import copy
import json
from datetime import date
from pathlib import Path

from trial_results_tracker.model import (
    DateType,
    OverallStatus,
    Precision,
    RegistryDate,
    UnpostedEvent,
    UnpostedEventType,
    Unrecognised,
)
from trial_results_tracker.parse import parse

FIXTURES = Path(__file__).parent / "fixtures"


def load(nct_id):
    # Recorded 2026-10-05 from /api/v2/studies/<id> with fetch.FIELDS.
    return json.loads((FIXTURES / f"{nct_id}.json").read_text())


# NCT01245270: results submitted 2013-08-23, QC passed 2014-08-13, posted 2014-08-15.
GAP = load("NCT01245270")
# NCT01916382: RELEASE, RESET, RELEASE, RESET; nothing posted.
RESET_TWICE = load("NCT01916382")


def with_status(record, **fields):
    record = copy.deepcopy(record)
    record["protocolSection"]["statusModule"].update(fields)
    return record


def test_full_date_keeps_day_precision():
    trial = parse(GAP)
    assert trial.results_first_submitted == RegistryDate(date(2013, 8, 23), Precision.DAY, None)
    assert trial.results_first_submit_qc == RegistryDate(date(2014, 8, 13), Precision.DAY, None)


def test_submit_post_gap_keeps_both_dates_and_post_type():
    trial = parse(GAP)
    assert trial.results_first_posted == RegistryDate(
        date(2014, 8, 15), Precision.DAY, DateType.ESTIMATED
    )
    assert trial.has_results


def test_month_partial_date_is_last_day_of_month():
    trial = parse(GAP)
    assert trial.primary_completion == RegistryDate(
        date(2013, 8, 31), Precision.MONTH, DateType.ACTUAL
    )
    assert trial.status_verified == RegistryDate(date(2021, 2, 28), Precision.MONTH, None)


def test_month_partial_date_respects_leap_years():
    trial = parse(with_status(GAP, statusVerifiedDate="2024-02"))
    assert trial.status_verified.value == date(2024, 2, 29)


def test_year_partial_date_is_last_day_of_year():
    record = with_status(GAP, primaryCompletionDateStruct={"date": "2013", "type": "ACTUAL"})
    assert parse(record).primary_completion == RegistryDate(
        date(2013, 12, 31), Precision.YEAR, DateType.ACTUAL
    )


def test_missing_pcd_is_none():
    record = copy.deepcopy(GAP)
    del record["protocolSection"]["statusModule"]["primaryCompletionDateStruct"]
    assert parse(record).primary_completion is None


def test_estimated_pcd_keeps_its_type():
    record = with_status(GAP, primaryCompletionDateStruct={"date": "2013-08", "type": "ESTIMATED"})
    assert parse(record).primary_completion.type is DateType.ESTIMATED


def test_unknown_status_enum_is_unrecognised_not_an_error():
    trial = parse(with_status(GAP, overallStatus="PAUSED_FOR_REVIEW"))
    assert trial.overall_status == Unrecognised("overallStatus", "PAUSED_FOR_REVIEW")
    assert trial.unrecognised == (Unrecognised("overallStatus", "PAUSED_FOR_REVIEW"),)


def test_known_enums_leave_nothing_unrecognised():
    trial = parse(GAP)
    assert trial.overall_status is OverallStatus.COMPLETED
    assert trial.unrecognised == ()


def test_unknown_unposted_event_type_is_unrecognised():
    record = copy.deepcopy(RESET_TWICE)
    events = record["annotationSection"]["annotationModule"]["unpostedAnnotation"]
    events["unpostedEvents"][0]["type"] = "WITHDRAW"
    assert parse(record).unrecognised == (Unrecognised("unpostedEvents.type", "WITHDRAW"),)


def test_latest_unposted_event_is_the_last_reset():
    trial = parse(RESET_TWICE)
    assert [e.type for e in trial.unposted_events] == [
        UnpostedEventType.RELEASE,
        UnpostedEventType.RESET,
        UnpostedEventType.RELEASE,
        UnpostedEventType.RESET,
    ]
    assert trial.latest_unposted_event == UnpostedEvent(UnpostedEventType.RESET, date(2025, 3, 11))
    assert trial.results_first_submitted is None
    assert trial.results_first_posted is None
    assert not trial.has_results


def test_latest_unposted_event_is_by_date_not_list_order():
    record = copy.deepcopy(RESET_TWICE)
    events = record["annotationSection"]["annotationModule"]["unpostedAnnotation"]
    events["unpostedEvents"].reverse()
    assert parse(record).latest_unposted_event.date == date(2025, 3, 11)


def test_no_unposted_events():
    assert parse(GAP).latest_unposted_event is None


def test_sponsor_is_kept_unchanged():
    trial = parse(GAP)
    assert trial.sponsor_raw == "University of Aberdeen"
    assert trial.sponsor_class == "OTHER"


def test_undated_unposted_event_is_kept_but_never_latest():
    # As in NCT00606515: UNRELEASE with dateUnknown between dated events.
    record = copy.deepcopy(RESET_TWICE)
    events = record["annotationSection"]["annotationModule"]["unpostedAnnotation"]
    events["unpostedEvents"].append({"type": "UNRELEASE", "dateUnknown": True})
    trial = parse(record)
    assert trial.unposted_events[-1] == UnpostedEvent(UnpostedEventType.UNRELEASE, None)
    assert trial.latest_unposted_event.type is UnpostedEventType.RESET


def test_submission_without_submit_date_is_the_earliest_unposted_event():
    # D1: the registry sets resultsFirstSubmitDate only once results post (PR #11).
    trial = parse(RESET_TWICE)
    assert trial.results_first_submitted is None
    assert trial.results_submitted == RegistryDate(date(2020, 2, 13), Precision.DAY, None)


def test_submit_date_wins_over_unposted_events():
    record = with_status(RESET_TWICE, resultsFirstSubmitDate="2019-06-01")
    assert parse(record).results_submitted.value == date(2019, 6, 1)


def test_no_submit_date_and_no_unposted_events_is_not_submitted():
    record = copy.deepcopy(GAP)
    del record["protocolSection"]["statusModule"]["resultsFirstSubmitDate"]
    assert parse(record).results_submitted is None

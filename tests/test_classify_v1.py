"""One test per v1.0 rule; each names the docs/plan.md decision it implements."""

import copy
import json
from collections import Counter
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from trial_results_tracker.classify import V1_0, Category, classify
from trial_results_tracker.crosswalk import crosswalk
from trial_results_tracker.model import (
    DateType,
    OverallStatus,
    Precision,
    RegistryDate,
    StudyType,
    Trial,
    UnpostedEvent,
    UnpostedEventType,
    Unrecognised,
)
from trial_results_tracker.parse import parse

AS_OF = date(2026, 10, 5)
FIXTURES = Path(__file__).parent / "fixtures"


def load(nct_id):
    return json.loads((FIXTURES / f"{nct_id}.json").read_text())


def ago(days, type=DateType.ACTUAL):
    return RegistryDate(AS_OF - timedelta(days=days), Precision.DAY, type)


def trial(status, pcd=None, submitted=None, **fields):
    t = Trial(
        nct_id="NCT00000000",
        study_type=StudyType.INTERVENTIONAL,
        overall_status=status,
        status_verified=None,
        why_stopped=None,
        enrollment_count=None,
        enrollment_type=None,
        primary_completion=pcd,
        completion=None,
        results_first_submitted=submitted,
        results_first_submit_qc=None,
        results_first_posted=None,
        disp_first_submitted=None,
        last_update_posted=None,
        has_results=submitted is not None,
        unposted_events=(),
        latest_unposted_event=None,
        sponsor_raw=None,
        sponsor_class=None,
        responsible_party=None,
        is_fda_regulated_drug=None,
        is_fda_regulated_device=None,
        fdaaa801_violation=None,
        unrecognised=(),
        results_submitted=submitted,
    )
    return replace(t, **fields)


def v1(t):
    return classify(t, AS_OF, V1_0)


LONG_AGO = ago(1000)


def test_d1_reported_date_is_submission_not_posting():
    # D1: submitted at PCD + 300 d counts as in time even though posting came at + 700 d.
    t = trial(
        OverallStatus.COMPLETED,
        LONG_AGO,
        submitted=ago(700),
        results_first_posted=ago(300),
    )
    assert v1(t) is Category.DUE_REPORTED_IN_TIME


def test_d1_no_submission_is_due_not_reported():
    assert v1(trial(OverallStatus.COMPLETED, LONG_AGO)) is Category.DUE_NOT_REPORTED


def test_d1_submission_reset_in_qc_with_nothing_posted_is_returned_in_qc():
    # D1: latest unposted event RESET and nothing posted is its own category.
    reset = UnpostedEvent(UnpostedEventType.RESET, AS_OF - timedelta(days=500))
    t = trial(
        OverallStatus.COMPLETED,
        LONG_AGO,
        submitted=ago(800),
        unposted_events=(UnpostedEvent(UnpostedEventType.RELEASE, None), reset),
        latest_unposted_event=reset,
    )
    assert v1(t) is Category.DUE_RETURNED_IN_QC


def test_d1_reset_but_later_posted_is_reported():
    reset = UnpostedEvent(UnpostedEventType.RESET, AS_OF - timedelta(days=800))
    t = trial(
        OverallStatus.COMPLETED,
        LONG_AGO,
        submitted=ago(900),
        results_first_posted=ago(700),
        latest_unposted_event=reset,
    )
    assert v1(t) is Category.DUE_REPORTED_IN_TIME


# Recorded 2026-10-05 from /api/v2/studies/<id> with fetch.FIELDS; neither has
# resultsFirstSubmitDate. NCT02582203: COMPLETED, PCD 2016-05, RELEASE then RESET.
# NCT01545440: COMPLETED, PCD 2013-03, RELEASE then an undated UNRELEASE.
RETURNED = load("NCT02582203")
UNRELEASED = load("NCT01545440")


def test_d1_reset_with_nothing_posted_is_returned_in_qc_on_a_real_record():
    assert v1(parse(RETURNED)) is Category.DUE_RETURNED_IN_QC


def test_d1_pending_release_counts_by_its_derived_submit_date():
    # NCT02582203 before its RESET: submitted 2025-03-24, over 395 d after PCD.
    record = copy.deepcopy(RETURNED)
    events = record["annotationSection"]["annotationModule"]["unpostedAnnotation"]
    events["unpostedEvents"].pop()
    assert v1(parse(record)) is Category.DUE_REPORTED_LATE


def test_d1_unreleased_submission_is_not_reported():
    assert v1(parse(UNRELEASED)) is Category.DUE_NOT_REPORTED


def test_d2_due_only_after_more_than_395_days():
    # D2: one number. Day 395 is still inside the window, day 396 is due.
    assert v1(trial(OverallStatus.COMPLETED, ago(395))) is Category.COMPLETED_NOT_DUE
    assert v1(trial(OverallStatus.COMPLETED, ago(396))) is Category.DUE_NOT_REPORTED


def test_d2_not_due_ignores_early_results():
    # D2: the due cohort is defined by time alone, so early reporters do not enter it early.
    t = trial(OverallStatus.COMPLETED, ago(100), submitted=ago(50))
    assert v1(t) is Category.COMPLETED_NOT_DUE


def test_d2_in_time_cut_is_the_same_395_days():
    # D2: submission at PCD + 395 d is in time, at PCD + 396 d it is late.
    in_time = trial(OverallStatus.COMPLETED, LONG_AGO, submitted=ago(1000 - 395))
    late = trial(OverallStatus.COMPLETED, LONG_AGO, submitted=ago(1000 - 396))
    assert v1(in_time) is Category.DUE_REPORTED_IN_TIME
    assert v1(late) is Category.DUE_REPORTED_LATE


def test_d2_partial_pcd_uses_the_last_day_of_its_period():
    # D2 with plan T2: a month-only PCD sits on the month's last day, favouring the sponsor.
    pcd = RegistryDate(AS_OF - timedelta(days=395), Precision.MONTH, DateType.ACTUAL)
    assert v1(trial(OverallStatus.COMPLETED, pcd)) is Category.COMPLETED_NOT_DUE


def test_d3_suspended_is_ongoing_not_exempt():
    # D3: suspension is a pause, not an exemption.
    assert v1(trial(OverallStatus.SUSPENDED, ago(100))) is Category.ONGOING


def test_d3_suspended_past_pcd_plus_395_is_status_overdue():
    # D3 with D5: a suspended trial is an open status, so it goes stale like one.
    assert v1(trial(OverallStatus.SUSPENDED, ago(396))) is Category.STATUS_OVERDUE


@pytest.mark.parametrize("status", [OverallStatus.COMPLETED, OverallStatus.TERMINATED])
@pytest.mark.parametrize(
    "pcd",
    [
        None,
        RegistryDate(LONG_AGO.value, Precision.DAY, DateType.ESTIMATED),
        RegistryDate(LONG_AGO.value, Precision.DAY, None),
        RegistryDate(LONG_AGO.value, Precision.DAY, Unrecognised("type", "X")),
    ],
    ids=["missing", "estimated", "untyped", "unrecognised"],
)
def test_d4_finished_without_actual_pcd_is_inconsistent(status, pcd):
    # D4 (a): no fallback to the completion date in v1.0.
    t = trial(status, pcd, completion=LONG_AGO)
    assert v1(t) is Category.INCONSISTENT


def test_d4_terminated_with_zero_actual_enrolment_has_no_requirement():
    t = trial(
        OverallStatus.TERMINATED,
        LONG_AGO,
        enrollment_count=0,
        enrollment_type=DateType.ACTUAL,
    )
    assert v1(t) is Category.NO_REPORTING_REQUIREMENT


def test_d4_zero_estimated_enrolment_is_still_due():
    t = trial(
        OverallStatus.TERMINATED,
        LONG_AGO,
        enrollment_count=0,
        enrollment_type=DateType.ESTIMATED,
    )
    assert v1(t) is Category.DUE_NOT_REPORTED


def test_withdrawn_has_no_requirement():
    # Kept from Keestra; plan "Categories (v1.0)".
    assert v1(trial(OverallStatus.WITHDRAWN, LONG_AGO)) is Category.NO_REPORTING_REQUIREMENT


@pytest.mark.parametrize(
    "status",
    [
        OverallStatus.NOT_YET_RECRUITING,
        OverallStatus.RECRUITING,
        OverallStatus.ENROLLING_BY_INVITATION,
        OverallStatus.ACTIVE_NOT_RECRUITING,
    ],
)
def test_d5_open_status_past_pcd_plus_395_is_status_overdue(status):
    # D5: the stale threshold is an open status with PCD more than 395 d ago.
    assert v1(trial(status, ago(396))) is Category.STATUS_OVERDUE
    assert v1(trial(status, ago(395))) is Category.ONGOING


def test_open_status_without_pcd_is_ongoing():
    # No PCD, so nothing can be past it; not inconsistent under methodology.md rec. 5.
    assert v1(trial(OverallStatus.RECRUITING)) is Category.ONGOING


@pytest.mark.parametrize(
    "status",
    [
        OverallStatus.UNKNOWN,
        OverallStatus.AVAILABLE,
        None,
        Unrecognised("overallStatus", "NEW"),
    ],
)
def test_unknown_and_unmatched_status_is_inconsistent(status):
    assert v1(trial(status, LONG_AGO)) is Category.INCONSISTENT


def test_crosswalk_cross_tabulates_keestra_against_v1():
    trials = [
        trial(OverallStatus.SUSPENDED, LONG_AGO),  # exempt -> status overdue
        trial(OverallStatus.COMPLETED),  # due, not reported -> inconsistent
        trial(OverallStatus.COMPLETED),
        trial(OverallStatus.COMPLETED, LONG_AGO, submitted=ago(700)),  # reported -> in time
    ]
    assert crosswalk(trials, AS_OF) == Counter(
        {
            (Category.NO_REPORTING_REQUIREMENT, Category.STATUS_OVERDUE): 1,
            (Category.DUE_NOT_REPORTED, Category.INCONSISTENT): 2,
            (Category.DUE_AND_REPORTED, Category.DUE_REPORTED_IN_TIME): 1,
        }
    )

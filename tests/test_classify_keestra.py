import json
import types
from datetime import date, timedelta
from pathlib import Path

import pytest

from trial_results_tracker import classify as classify_module
from trial_results_tracker.classify import KEESTRA_2021, Category, classify
from trial_results_tracker.model import (
    DateType,
    OverallStatus,
    Precision,
    RegistryDate,
    StudyType,
    Trial,
    Unrecognised,
)
from trial_results_tracker.parse import parse

AS_OF = date(2026, 10, 5)


def day(d, type=DateType.ACTUAL):
    return RegistryDate(d, Precision.DAY, type)


def trial(status, pcd=None, submitted=None):
    return Trial(
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
    )


def keestra(t):
    return classify(t, AS_OF, KEESTRA_2021)


LONG_AGO = day(AS_OF - timedelta(days=1000))


@pytest.mark.parametrize("status", [OverallStatus.WITHDRAWN, OverallStatus.SUSPENDED])
def test_withdrawn_and_suspended_have_no_reporting_requirement(status):
    assert keestra(trial(status, LONG_AGO)) is Category.NO_REPORTING_REQUIREMENT


def test_finished_with_results_past_threshold_is_due_and_reported():
    t = trial(OverallStatus.COMPLETED, LONG_AGO, submitted=day(AS_OF - timedelta(days=10)))
    assert keestra(t) is Category.DUE_AND_REPORTED


def test_terminated_without_results_past_threshold_is_due_not_reported():
    assert keestra(trial(OverallStatus.TERMINATED, LONG_AGO)) is Category.DUE_NOT_REPORTED


def test_submission_derived_from_unposted_events_leaves_keestra_unchanged():
    # Keestra read resultsFirstSubmitDate only; v1.0's derived submission (D1) is not it.
    record = json.loads((Path(__file__).parent / "fixtures" / "NCT02582203.json").read_text())
    t = parse(record)
    assert t.results_submitted is not None
    assert keestra(t) is Category.DUE_NOT_REPORTED


def test_finished_with_missing_pcd_is_due():
    # Keestra code, not paper: a missing PCD counts as past the threshold.
    assert keestra(trial(OverallStatus.COMPLETED)) is Category.DUE_NOT_REPORTED


def test_finished_within_threshold_is_completed_not_due():
    t = trial(OverallStatus.COMPLETED, day(AS_OF - timedelta(days=100)))
    assert keestra(t) is Category.COMPLETED_NOT_DUE


def test_open_status_with_pcd_recent_or_future_is_ongoing():
    assert keestra(trial(OverallStatus.RECRUITING, day(AS_OF))) is Category.ONGOING


@pytest.mark.parametrize(
    "t",
    [
        trial(OverallStatus.RECRUITING, LONG_AGO),  # open status, PCD long past
        trial(OverallStatus.ACTIVE_NOT_RECRUITING),  # open status, no PCD
        trial(OverallStatus.UNKNOWN, LONG_AGO),
        trial(None, LONG_AGO),
        trial(Unrecognised("overallStatus", "NEW"), LONG_AGO),
    ],
)
def test_everything_unmatched_is_inconsistent(t):
    assert keestra(t) is Category.INCONSISTENT


def test_boundary_394_days_is_not_due():
    t = trial(OverallStatus.COMPLETED, day(AS_OF - timedelta(days=394)))
    assert keestra(t) is Category.COMPLETED_NOT_DUE


def test_boundary_exactly_395_days_is_due():
    t = trial(OverallStatus.COMPLETED, day(AS_OF - timedelta(days=395)))
    assert keestra(t) is Category.DUE_NOT_REPORTED


def test_month_precision_pcd_sits_on_first_of_month():
    # Keestra parsed "%B %Y" to the 1st; the model stores the last day of the month.
    pcd = RegistryDate(date(2025, 9, 30), Precision.MONTH, DateType.ACTUAL)
    assert (AS_OF - date(2025, 9, 1)).days == 399
    assert keestra(trial(OverallStatus.COMPLETED, pcd)) is Category.DUE_NOT_REPORTED


def test_ongoing_window_is_30_days():
    assert keestra(trial(OverallStatus.RECRUITING, day(AS_OF - timedelta(days=29)))) is (
        Category.ONGOING
    )
    assert keestra(trial(OverallStatus.RECRUITING, day(AS_OF - timedelta(days=30)))) is (
        Category.INCONSISTENT
    )


def test_classify_imports_nothing_that_does_io():
    allowed = {"builtins", "dataclasses", "datetime", "enum", "collections.abc", "typing"}
    for name, value in vars(classify_module).items():
        if name.startswith("__"):
            continue
        module = (
            value.__name__
            if isinstance(value, types.ModuleType)
            else getattr(value, "__module__", "builtins")
        )
        assert (
            module in allowed
            or module.startswith("trial_results_tracker.model")
            or (module == "trial_results_tracker.classify")
        ), f"{name} comes from {module}"

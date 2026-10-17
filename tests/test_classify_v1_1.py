"""One test per v1.1 rule (D16, docs/plan.md); v1.1 is v1.0 everywhere else."""

from datetime import date

import pytest
from test_classify_v1 import LONG_AGO, ago, trial

from trial_results_tracker.classify import V1_0, V1_1, Category, classify
from trial_results_tracker.model import DateType, OverallStatus

AS_OF = date(2026, 10, 5)
OPEN = [
    OverallStatus.RECRUITING,
    OverallStatus.ENROLLING_BY_INVITATION,
    OverallStatus.ACTIVE_NOT_RECRUITING,
    OverallStatus.SUSPENDED,
    OverallStatus.NOT_YET_RECRUITING,
]


def v11(t):
    return classify(t, AS_OF, V1_1)


@pytest.mark.parametrize("status", OPEN)
def test_d16_open_status_with_results_is_scored_as_due(status):
    # v1.0 put these in status overdue, which the D5 upper bound counts as unreported.
    on_time = trial(status, LONG_AGO, submitted=ago(700))
    late = trial(status, LONG_AGO, submitted=ago(100))
    assert classify(on_time, AS_OF, V1_0) is Category.STATUS_OVERDUE
    assert v11(on_time) is Category.DUE_REPORTED_IN_TIME
    assert v11(late) is Category.DUE_REPORTED_LATE


def test_d16_active_not_recruiting_after_actual_pcd_is_due():
    assert v11(trial(OverallStatus.ACTIVE_NOT_RECRUITING, LONG_AGO)) is Category.DUE_NOT_REPORTED


def test_d16_active_not_recruiting_with_estimated_pcd_stays_status_overdue():
    t = trial(OverallStatus.ACTIVE_NOT_RECRUITING, ago(1000, DateType.ESTIMATED))
    assert v11(t) is Category.STATUS_OVERDUE


def test_d16_not_yet_recruiting_long_past_pcd_is_probably_never_started():
    t = trial(OverallStatus.NOT_YET_RECRUITING, ago(1000, DateType.ESTIMATED))
    assert v11(t) is Category.PROBABLY_NEVER_STARTED


@pytest.mark.parametrize(
    "status",
    [OverallStatus.RECRUITING, OverallStatus.ENROLLING_BY_INVITATION, OverallStatus.SUSPENDED],
)
def test_d16_other_open_statuses_without_results_stay_status_overdue(status):
    assert v11(trial(status, LONG_AGO)) is Category.STATUS_OVERDUE


def test_d16_open_status_inside_threshold_is_still_ongoing():
    t = trial(OverallStatus.ACTIVE_NOT_RECRUITING, ago(395), submitted=ago(10))
    assert v11(t) is Category.ONGOING

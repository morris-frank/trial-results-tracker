"""Sort a trial into a reporting category under a named rule set (docs/plan.md T3).

Pure: no I/O, the snapshot date comes in as `as_of`. AGENTS.md rule 5.

`KEESTRA_2021` transcribes the predecessor's code rather than its paper: LeeSean96/
GlobalHealthRanking at 4a3f726, `src/ClinicalTrialsTracker/model/clinical_trial.py`
(`create_category`, lines 100-116), `definitions.py` (thresholds, lines 15-17) and
`raw_data_to_clinical_trial_v1.py` (field extraction). The logic is reimplemented, not
copied; credit under its licence: Copyright 2020 Yi Nian Lee, MIT.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from trial_results_tracker.model import (
    DateType,
    OverallStatus,
    Precision,
    RegistryDate,
    Trial,
    UnpostedEventType,
)


class Category(StrEnum):
    """Keestra's six categories plus v1.0's (methodology.md rec. 5), so T6 only adds rules."""

    NO_REPORTING_REQUIREMENT = "no_reporting_requirement"
    DUE_AND_REPORTED = "due_and_reported"  # Keestra only; v1.0 splits it by timing
    DUE_NOT_REPORTED = "due_not_reported"
    DUE_REPORTED_IN_TIME = "due_reported_in_time"
    DUE_REPORTED_LATE = "due_reported_late"
    DUE_RETURNED_IN_QC = "due_returned_in_qc"
    COMPLETED_NOT_DUE = "completed_not_due"
    ONGOING = "ongoing"
    STATUS_OVERDUE = "status_overdue"
    INCONSISTENT = "inconsistent"


@dataclass(frozen=True)
class RuleSet:
    name: str
    rule: Callable[[Trial, date], Category]


def classify(trial: Trial, as_of: date, rules: RuleSet) -> Category:
    return rules.rule(trial, as_of)


_KEESTRA_UNCERTAINTY = 30  # days; definitions.py:15
_KEESTRA_REPORTING_THRESHOLD = 365 + _KEESTRA_UNCERTAINTY  # definitions.py:16
_KEESTRA_ONGOING = frozenset(
    {
        OverallStatus.NOT_YET_RECRUITING,
        OverallStatus.ACTIVE_NOT_RECRUITING,
        OverallStatus.RECRUITING,
        OverallStatus.ENROLLING_BY_INVITATION,
    }
)


def _keestra_pcd(pcd: RegistryDate | None) -> date | None:
    """Keestra parsed a month-only PCD with "%B %Y", landing on the 1st
    (raw_data_to_clinical_trial_v1.py:38); the model puts it on the month's last day.
    PCD type (ACTUAL/ESTIMATED) was never read, so it is ignored here too."""
    if pcd is None:
        return None
    return pcd.value.replace(day=1) if pcd.precision is Precision.MONTH else pcd.value


def _keestra_2021(trial: Trial, as_of: date) -> Category:
    """`create_category`, clinical_trial.py:100-116.

    Missing PCD on a finished trial counts as due: `has_exceeded_reporting_threshold`
    returns True when `completion_date is None` (clinical_trial.py:92-93), and
    `completion_date` is `primary_completion_date` (raw_data_to_clinical_trial_v1.py:37).
    This settles critique.md contradiction 3 in favour of methodology.md's reading.

    Reported means `results_first_submitted` is present (raw_data_to_clinical_trial_v1.py:
    54-55), not posted; its date never affects the category.
    """
    status = trial.overall_status
    pcd = _keestra_pcd(trial.primary_completion)
    days_since_pcd = None if pcd is None else (as_of - pcd).days

    if status in (OverallStatus.WITHDRAWN, OverallStatus.SUSPENDED):
        return Category.NO_REPORTING_REQUIREMENT
    if status in (OverallStatus.COMPLETED, OverallStatus.TERMINATED):
        if days_since_pcd is not None and days_since_pcd < _KEESTRA_REPORTING_THRESHOLD:
            return Category.COMPLETED_NOT_DUE
        if trial.results_first_submitted is not None:
            return Category.DUE_AND_REPORTED
        return Category.DUE_NOT_REPORTED
    # has_future_completion_date, clinical_trial.py:81-88: no PCD is not ongoing.
    if (
        status in _KEESTRA_ONGOING
        and days_since_pcd is not None
        and days_since_pcd < _KEESTRA_UNCERTAINTY
    ):
        return Category.ONGOING
    return Category.INCONSISTENT


KEESTRA_2021 = RuleSet("Keestra-2021 replication", _keestra_2021)


_V1_THRESHOLD = 395  # days; D2: one number for both the due and the in-time cut
_V1_OPEN = _KEESTRA_ONGOING | {OverallStatus.SUSPENDED}  # D3: suspension is a pause


def _v1_0(trial: Trial, as_of: date) -> Category:
    """Methodology v1.0, docs/methodology.md; decisions D1-D5 in docs/plan.md.

    Unlike Keestra, a trial is due only *after* 395 days, so a submission on day 395
    is in time and the trial is never overdue on that day. Partial dates keep the
    model's last-day-of-period reading.
    """
    status = trial.overall_status
    pcd = trial.primary_completion
    days_since_pcd = None if pcd is None else (as_of - pcd.value).days

    if status is OverallStatus.WITHDRAWN:
        return Category.NO_REPORTING_REQUIREMENT
    if status in _V1_OPEN:  # D3, D5
        if days_since_pcd is not None and days_since_pcd > _V1_THRESHOLD:
            return Category.STATUS_OVERDUE
        return Category.ONGOING
    if status not in (OverallStatus.COMPLETED, OverallStatus.TERMINATED):
        return Category.INCONSISTENT
    if (
        status is OverallStatus.TERMINATED
        and trial.enrollment_count == 0
        and trial.enrollment_type is DateType.ACTUAL
    ):  # D4
        return Category.NO_REPORTING_REQUIREMENT
    if pcd is None or pcd.type is not DateType.ACTUAL:  # D4 (a), no fallback
        return Category.INCONSISTENT
    if days_since_pcd <= _V1_THRESHOLD:  # D2
        return Category.COMPLETED_NOT_DUE
    submitted = trial.results_first_submitted  # D1
    if submitted is None:
        return Category.DUE_NOT_REPORTED
    latest = trial.latest_unposted_event
    if (
        trial.results_first_posted is None
        and latest is not None
        and latest.type is UnpostedEventType.RESET
    ):  # D1
        return Category.DUE_RETURNED_IN_QC
    if (submitted.value - pcd.value).days <= _V1_THRESHOLD:  # D2
        return Category.DUE_REPORTED_IN_TIME
    return Category.DUE_REPORTED_LATE


V1_0 = RuleSet("v1.0", _v1_0)

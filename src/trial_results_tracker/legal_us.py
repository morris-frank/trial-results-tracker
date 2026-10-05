"""The US legal-duty column: does FDAAA 801 appear to require results (docs/plan.md T13)?

Pure: no I/O. ClinicalTrials.gov does not publish whether a trial is an applicable clinical
trial (ACT), so this infers a *probable* ACT from the registry fields that 42 CFR 11.10 and
11.22(b) name, and returns "not determined" whenever one cannot be read. It never reads
or changes the WHO category (AGENTS.md rule 2). The re-check of the FDAAA TrialsTracker's
pACT rules against 11.10 is recorded in docs/research/legal.md section 4.
"""

from datetime import date, timedelta
from enum import StrEnum

from trial_results_tracker.model import (
    DateType,
    OverallStatus,
    Phase,
    PrimaryPurpose,
    StudyType,
    Trial,
    Unrecognised,
)

# 11.42: Part 11 results duties cover ACTs whose primary completion is on or after this date.
FINAL_RULE = date(2017, 1, 18)
# 11.44(a) gives one year; the 30 days for quality control match the WHO threshold.
DEADLINE = timedelta(days=365 + 30)
# 11.22(b): the United States "or one of its territories", as ClinicalTrials.gov spells them.
US = frozenset(
    {
        "United States",
        "American Samoa",
        "Guam",
        "Northern Mariana Islands",
        "Puerto Rico",
        "Virgin Islands",
        "Virgin Islands (U.S.)",
    }
)
PHASE_1 = frozenset({Phase.EARLY_PHASE1, Phase.PHASE1})  # 21 CFR 312.21(a)


class LegalDuty(StrEnum):
    NOT_DETERMINED = "not determined"
    NO_DUTY = "FDAAA: no duty identified"
    NOT_YET_DUE = "FDAAA probable ACT: not yet due"
    DELAYED = "FDAAA probable ACT: not yet due (delay certified or extension requested)"
    SUBMITTED = "FDAAA probable ACT: results submitted"
    APPEARS_OVERDUE = "appears overdue under FDAAA, absent an unpublished extension"


def _any(values: list[bool | None]) -> bool | None:
    """Three-valued or: True if one holds, False if all fail, None if unknown otherwise."""
    if True in values:
        return True
    return False if all(value is False for value in values) else None


def _drug(trial: Trial) -> bool | None:
    """11.10 applicable drug clinical trial: an FDA-regulated drug, other than phase 1."""
    if trial.is_fda_regulated_drug is not True:
        return trial.is_fda_regulated_drug
    if not trial.phases or any(isinstance(phase, Unrecognised) for phase in trial.phases):
        return None
    return not set(trial.phases) <= PHASE_1  # phase 1/2 is not phase 1


def _device(trial: Trial) -> bool | None:
    """11.10 applicable device clinical trial: an FDA-regulated device, not a feasibility study."""
    if trial.is_fda_regulated_device is not True:
        return trial.is_fda_regulated_device
    if trial.primary_purpose is None or isinstance(trial.primary_purpose, Unrecognised):
        return None
    return trial.primary_purpose is not PrimaryPurpose.DEVICE_FEASIBILITY


def probable_act(trial: Trial) -> bool | None:
    """True when every criterion the registry shows holds, False when one fails, None when
    one cannot be read. Controlled design (11.10) is assumed: every trial with arms and
    outcome measures counts as controlled."""
    if trial.study_type is not StudyType.INTERVENTIONAL:
        return False  # 11.10: expanded access is not an ACT; observational is not a trial
    if trial.overall_status is OverallStatus.WITHDRAWN:
        return False  # 11.22(a)(3): never initiated, as no subject enrolled
    product = _any([_drug(trial), _device(trial)])
    if not product:
        return product
    # 11.22(b)(1)(ii)(D), (b)(2)(iv): a US site, a US-made export, or an IND/IDE number.
    # IND and IDE numbers are not public, so a trial without the other two is unknown.
    if trial.is_us_export or US.intersection(trial.location_countries):
        return True
    return None


def _years_later(day: date, years: int) -> date:
    """The same calendar day `years` on; 29 Feb moves to 1 Mar, the later reading."""
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return date(day.year + years, 3, 1)


def status(trial: Trial, as_of: date) -> LegalDuty:
    act = probable_act(trial)
    if act is False:
        return LegalDuty.NO_DUTY
    pcd = trial.primary_completion
    if act is None or pcd is None or pcd.value < FINAL_RULE:
        return LegalDuty.NOT_DETERMINED  # before 11.42, only approved products, not shown
    if trial.results_first_submitted is not None:
        return LegalDuty.SUBMITTED  # 11.44 deadlines are about submission, not posting
    if as_of <= pcd.value + DEADLINE:
        return LegalDuty.NOT_YET_DUE
    if pcd.type is not DateType.ACTUAL:
        return LegalDuty.NOT_DETERMINED  # the clock runs from the actual date
    # 11.44(b)(2), (c)(2): a certified delay ends 2 years after certification at the latest.
    # dispFirstSubmitDate also marks extension requests (11.44(e)), whose length is not
    # published: hence "absent an unpublished extension".
    disp = trial.disp_first_submitted
    if disp is not None and as_of <= _years_later(disp.value, 2):
        return LegalDuty.DELAYED
    return LegalDuty.APPEARS_OVERDUE


def fda_flag(trial: Trial) -> str:
    """ClinicalTrials.gov's own flag, quoted and attributed: the only place the site may use
    the word violation (docs/research/legal.md section 3)."""
    if not trial.fdaaa801_violation:
        return ""
    return 'ClinicalTrials.gov shows "fdaaa801Violation: true", a flag set on information from FDA'

"""Typed trial rows, the only input classification sees (docs/plan.md T2).

Enum values are the ClinicalTrials.gov API v2 values from /studies/enums. A value the
API adds later parses to `Unrecognised` instead of raising, so it flags the row rather
than failing the build.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


@dataclass(frozen=True)
class Unrecognised:
    """An enum value this code does not know; `field` is the API piece it came from."""

    field: str
    raw: str


class Precision(StrEnum):
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"


class DateType(StrEnum):
    """ACTUAL/ESTIMATED; the registry uses the same pair for enrolment counts."""

    ACTUAL = "ACTUAL"
    ESTIMATED = "ESTIMATED"


class StudyType(StrEnum):
    INTERVENTIONAL = "INTERVENTIONAL"
    OBSERVATIONAL = "OBSERVATIONAL"
    EXPANDED_ACCESS = "EXPANDED_ACCESS"


class Phase(StrEnum):
    NA = "NA"
    EARLY_PHASE1 = "EARLY_PHASE1"
    PHASE1 = "PHASE1"
    PHASE2 = "PHASE2"
    PHASE3 = "PHASE3"
    PHASE4 = "PHASE4"


class PrimaryPurpose(StrEnum):
    TREATMENT = "TREATMENT"
    PREVENTION = "PREVENTION"
    DIAGNOSTIC = "DIAGNOSTIC"
    ECT = "ECT"
    SUPPORTIVE_CARE = "SUPPORTIVE_CARE"
    SCREENING = "SCREENING"
    HEALTH_SERVICES_RESEARCH = "HEALTH_SERVICES_RESEARCH"
    BASIC_SCIENCE = "BASIC_SCIENCE"
    DEVICE_FEASIBILITY = "DEVICE_FEASIBILITY"
    OTHER = "OTHER"


class OverallStatus(StrEnum):
    ACTIVE_NOT_RECRUITING = "ACTIVE_NOT_RECRUITING"
    COMPLETED = "COMPLETED"
    ENROLLING_BY_INVITATION = "ENROLLING_BY_INVITATION"
    NOT_YET_RECRUITING = "NOT_YET_RECRUITING"
    RECRUITING = "RECRUITING"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    WITHDRAWN = "WITHDRAWN"
    AVAILABLE = "AVAILABLE"
    NO_LONGER_AVAILABLE = "NO_LONGER_AVAILABLE"
    TEMPORARILY_NOT_AVAILABLE = "TEMPORARILY_NOT_AVAILABLE"
    APPROVED_FOR_MARKETING = "APPROVED_FOR_MARKETING"
    WITHHELD = "WITHHELD"
    UNKNOWN = "UNKNOWN"


class SponsorClass(StrEnum):
    NIH = "NIH"
    FED = "FED"
    OTHER_GOV = "OTHER_GOV"
    INDIV = "INDIV"
    INDUSTRY = "INDUSTRY"
    NETWORK = "NETWORK"
    AMBIG = "AMBIG"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ResponsiblePartyType(StrEnum):
    SPONSOR = "SPONSOR"
    PRINCIPAL_INVESTIGATOR = "PRINCIPAL_INVESTIGATOR"
    SPONSOR_INVESTIGATOR = "SPONSOR_INVESTIGATOR"


class UnpostedEventType(StrEnum):
    RESET = "RESET"
    RELEASE = "RELEASE"
    UNRELEASE = "UNRELEASE"


@dataclass(frozen=True)
class RegistryDate:
    """A registry date; partial dates sit on the last day of their month or year."""

    value: date
    precision: Precision
    type: DateType | Unrecognised | None  # None for dates the registry gives untyped


@dataclass(frozen=True)
class UnpostedEvent:
    type: UnpostedEventType | Unrecognised
    date: date | None  # None where the registry marks the date unknown


@dataclass(frozen=True)
class Trial:
    nct_id: str
    study_type: StudyType | Unrecognised | None
    overall_status: OverallStatus | Unrecognised | None
    status_verified: RegistryDate | None
    why_stopped: str | None
    enrollment_count: int | None
    enrollment_type: DateType | Unrecognised | None
    primary_completion: RegistryDate | None
    completion: RegistryDate | None
    results_first_submitted: RegistryDate | None
    results_first_submit_qc: RegistryDate | None
    results_first_posted: RegistryDate | None
    disp_first_submitted: RegistryDate | None
    last_update_posted: RegistryDate | None
    has_results: bool
    unposted_events: tuple[UnpostedEvent, ...]
    latest_unposted_event: UnpostedEvent | None
    sponsor_raw: str | None
    sponsor_class: SponsorClass | Unrecognised | None
    responsible_party: ResponsiblePartyType | Unrecognised | None
    is_fda_regulated_drug: bool | None
    is_fda_regulated_device: bool | None
    fdaaa801_violation: bool | None
    unrecognised: tuple[Unrecognised, ...]  # every Unrecognised field, for the build report
    # Read only by legal_us (T13), so the WHO rule tests need not set them.
    phases: tuple[Phase | Unrecognised, ...] = ()
    primary_purpose: PrimaryPurpose | Unrecognised | None = None
    location_countries: tuple[str, ...] = ()  # countries only; no facility or contact field
    is_us_export: bool | None = None
    # resultsFirstSubmitDate, else the earliest dated unposted event: the registry sets
    # the former only once results post (PR #11). Read by v1.0 (D1), not Keestra-2021.
    results_submitted: RegistryDate | None = None

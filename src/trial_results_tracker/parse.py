"""Turn one raw snapshot record into a `Trial`. Pure: no I/O."""

import calendar
from datetime import date

from trial_results_tracker.model import (
    DateType,
    OverallStatus,
    Precision,
    RegistryDate,
    ResponsiblePartyType,
    SponsorClass,
    StudyType,
    Trial,
    UnpostedEvent,
    UnpostedEventType,
    Unrecognised,
)


def parse_date(text: str) -> tuple[date, Precision]:
    """Read YYYY-MM-DD, YYYY-MM or YYYY; a partial date goes to the period's last day.

    The last day is the reading most favourable to the sponsor (docs/plan.md T2).
    """
    parts = [int(part) for part in text.split("-")]
    if len(parts) == 3:
        return date(*parts), Precision.DAY
    if len(parts) == 2:
        year, month = parts
        return date(year, month, calendar.monthrange(year, month)[1]), Precision.MONTH
    (year,) = parts
    return date(year, 12, 31), Precision.YEAR


def parse(record: dict) -> Trial:
    protocol = record["protocolSection"]
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    sponsors = protocol.get("sponsorCollaboratorsModule", {})
    oversight = protocol.get("oversightModule", {})
    annotation = record.get("annotationSection", {}).get("annotationModule", {})
    unrecognised: list[Unrecognised] = []

    def enum[E](kind: type[E], field: str, raw: str | None) -> E | Unrecognised | None:
        if raw is None:
            return None
        try:
            return kind(raw)
        except ValueError:
            unrecognised.append(Unrecognised(field, raw))
            return unrecognised[-1]

    def plain(field: str) -> RegistryDate | None:
        text = status.get(field)
        return None if text is None else RegistryDate(*parse_date(text), None)

    def struct(field: str) -> RegistryDate | None:
        value = status.get(field)
        if value is None:
            return None
        type_ = enum(DateType, f"{field}.type", value.get("type"))
        return RegistryDate(*parse_date(value["date"]), type_)

    events = tuple(
        UnpostedEvent(
            enum(UnpostedEventType, "unpostedEvents.type", event["type"]),
            parse_date(event["date"])[0] if "date" in event else None,  # else dateUnknown
        )
        for event in annotation.get("unpostedAnnotation", {}).get("unpostedEvents", [])
    )
    # By date, skipping undated events; on a tie the event listed later wins.
    dated = [(event.date, index, event) for index, event in enumerate(events) if event.date]
    latest = max(dated)[2] if dated else None
    enrollment = design.get("enrollmentInfo", {})
    lead = sponsors.get("leadSponsor", {})

    return Trial(
        nct_id=protocol["identificationModule"]["nctId"],
        study_type=enum(StudyType, "studyType", design.get("studyType")),
        overall_status=enum(OverallStatus, "overallStatus", status.get("overallStatus")),
        status_verified=plain("statusVerifiedDate"),
        why_stopped=status.get("whyStopped"),
        enrollment_count=enrollment.get("count"),
        enrollment_type=enum(DateType, "enrollmentInfo.type", enrollment.get("type")),
        primary_completion=struct("primaryCompletionDateStruct"),
        completion=struct("completionDateStruct"),
        results_first_submitted=plain("resultsFirstSubmitDate"),
        results_first_submit_qc=plain("resultsFirstSubmitQcDate"),
        results_first_posted=struct("resultsFirstPostDateStruct"),
        disp_first_submitted=plain("dispFirstSubmitDate"),
        last_update_posted=struct("lastUpdatePostDateStruct"),
        has_results=record.get("hasResults", False),
        unposted_events=events,
        latest_unposted_event=latest,
        sponsor_raw=lead.get("name"),
        sponsor_class=enum(SponsorClass, "leadSponsor.class", lead.get("class")),
        responsible_party=enum(
            ResponsiblePartyType,
            "responsibleParty.type",
            sponsors.get("responsibleParty", {}).get("type"),
        ),
        is_fda_regulated_drug=oversight.get("isFdaRegulatedDrug"),
        is_fda_regulated_device=oversight.get("isFdaRegulatedDevice"),
        fdaaa801_violation=oversight.get("fdaaa801Violation"),
        unrecognised=tuple(unrecognised),
    )

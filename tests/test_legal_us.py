"""One test per 42 CFR 11.10 / 11.22(b) criterion and per 11.44 deadline rule (docs/plan.md T13)."""

import copy
import csv
import gzip
import io
from dataclasses import replace
from datetime import date

import pytest
from test_build import STUDIES, pages, site  # noqa: F401 (site is a fixture)

from trial_results_tracker import legal_us
from trial_results_tracker.classify import KEESTRA_2021, V1_0, classify
from trial_results_tracker.export import export
from trial_results_tracker.legal_us import LegalDuty, fda_flag, probable_act, status
from trial_results_tracker.model import (
    DateType,
    OverallStatus,
    Phase,
    Precision,
    PrimaryPurpose,
    RegistryDate,
    StudyType,
)
from trial_results_tracker.parse import parse

AS_OF = date(2026, 10, 2)


def day(text, type_=DateType.ACTUAL):
    return RegistryDate(date.fromisoformat(text), Precision.DAY, type_)


# A phase 3 drug trial at a US site, finished 2023, no results: appears overdue.
ACT = replace(
    parse(STUDIES[0]),
    study_type=StudyType.INTERVENTIONAL,
    overall_status=OverallStatus.COMPLETED,
    phases=(Phase.PHASE3,),
    primary_purpose=PrimaryPurpose.TREATMENT,
    is_fda_regulated_drug=True,
    is_fda_regulated_device=False,
    location_countries=("Germany", "United States"),
    is_us_export=None,
    primary_completion=day("2023-06-30"),
    results_first_submitted=None,
    disp_first_submitted=None,
    fdaaa801_violation=None,
)
DEVICE = replace(ACT, is_fda_regulated_drug=False, is_fda_regulated_device=True, phases=(Phase.NA,))


def test_the_base_case_is_a_probable_act_that_appears_overdue():
    assert probable_act(ACT) is True
    assert status(ACT, AS_OF) is LegalDuty.APPEARS_OVERDUE
    assert LegalDuty.APPEARS_OVERDUE == (
        "appears overdue under FDAAA, absent an unpublished extension"
    )


# 11.10, 11.22(b)(1)(ii)(A), (b)(2)(i): interventional only; expanded access is not an ACT.
@pytest.mark.parametrize("study_type", [StudyType.EXPANDED_ACCESS, StudyType.OBSERVATIONAL])
def test_only_interventional_studies_are_acts(study_type):
    assert probable_act(replace(ACT, study_type=study_type)) is False


# 11.10 applicable drug clinical trial: a drug or biologic subject to FD&C 505 / PHS 351.
def test_drug_criterion_reads_the_fda_regulated_drug_flag():
    assert probable_act(replace(ACT, is_fda_regulated_drug=False)) is False
    assert probable_act(replace(ACT, is_fda_regulated_drug=None)) is None


# 11.10 "applicable device clinical trial": a device product subject to FD&C 510(k), 515 or 520(m).
def test_device_criterion_reads_the_fda_regulated_device_flag():
    assert probable_act(DEVICE) is True
    assert probable_act(replace(DEVICE, is_fda_regulated_device=False)) is False
    assert probable_act(replace(DEVICE, is_fda_regulated_device=None)) is None


def test_neither_flag_answered_is_not_determined():
    trial = replace(ACT, is_fda_regulated_drug=None, is_fda_regulated_device=None)
    assert status(trial, AS_OF) is LegalDuty.NOT_DETERMINED


# 11.10: "other than a phase 1 clinical investigation" (21 CFR 312.21), for drugs only.
@pytest.mark.parametrize(
    ("phases", "expected"),
    [
        ((Phase.PHASE1,), False),
        ((Phase.EARLY_PHASE1,), False),
        ((Phase.PHASE1, Phase.PHASE2), True),
        ((Phase.PHASE4,), True),
        ((Phase.NA,), True),
        ((), None),
    ],
)
def test_drug_trials_exclude_phase_1(phases, expected):
    assert probable_act(replace(ACT, phases=phases)) is expected


def test_phase_1_does_not_exclude_a_device_trial():
    assert probable_act(replace(DEVICE, phases=(Phase.PHASE1,))) is True


# 11.10 / 11.22(b)(1)(ii)(B): not a small feasibility study of a device.
def test_device_feasibility_studies_are_excluded():
    feasibility = replace(DEVICE, primary_purpose=PrimaryPurpose.DEVICE_FEASIBILITY)
    assert probable_act(feasibility) is False
    assert probable_act(replace(DEVICE, primary_purpose=None)) is None


# 11.22(b)(1)(ii)(D), (b)(2)(iv): a US facility, a US-made export, or an IND/IDE number.
@pytest.mark.parametrize("country", sorted(legal_us.US))
def test_a_us_or_territory_site_is_a_us_nexus(country):
    assert probable_act(replace(ACT, location_countries=(country,))) is True


def test_a_us_export_is_a_us_nexus():
    assert probable_act(replace(ACT, location_countries=("Canada",), is_us_export=True)) is True


def test_no_visible_us_nexus_is_not_determined_because_ind_numbers_are_not_public():
    trial = replace(ACT, location_countries=("Canada",), is_us_export=False)
    assert probable_act(trial) is None
    assert status(trial, AS_OF) is LegalDuty.NOT_DETERMINED


# 11.22(a)(3): initiated when the first subject enrols; a withdrawn trial never enrolled.
def test_withdrawn_trials_were_never_initiated():
    assert probable_act(replace(ACT, overall_status=OverallStatus.WITHDRAWN)) is False
    assert status(replace(ACT, is_fda_regulated_drug=False), AS_OF) is LegalDuty.NO_DUTY


# 11.42: Part 11 results are due for ACTs with a primary completion date on or after
# 18 Jan 2017; earlier ones only for approved products, which the registry does not show.
def test_primary_completion_before_the_final_rule_is_not_determined():
    assert status(replace(ACT, primary_completion=day("2017-01-17")), AS_OF) is (
        LegalDuty.NOT_DETERMINED
    )
    assert status(replace(ACT, primary_completion=day("2017-01-18")), AS_OF) is (
        LegalDuty.APPEARS_OVERDUE
    )
    assert status(replace(ACT, primary_completion=None), AS_OF) is LegalDuty.NOT_DETERMINED


# 11.44(a): due one year after primary completion; the site allows 30 more days for QC.
def test_due_one_year_plus_30_days_after_primary_completion():
    pcd = day("2025-09-02")  # 395 days before AS_OF
    assert status(replace(ACT, primary_completion=pcd), AS_OF) is LegalDuty.NOT_YET_DUE
    later = date(2026, 10, 3)
    assert status(replace(ACT, primary_completion=pcd), later) is LegalDuty.APPEARS_OVERDUE


def test_submitted_results_are_not_overdue():
    trial = replace(ACT, results_first_submitted=day("2026-01-01"))
    assert status(trial, AS_OF) is LegalDuty.SUBMITTED


def test_an_estimated_primary_completion_never_appears_overdue():
    trial = replace(ACT, primary_completion=day("2023-06-30", DateType.ESTIMATED))
    assert status(trial, AS_OF) is LegalDuty.NOT_DETERMINED


# 11.44(b)(2), (c)(2): a certified delay is not due until 2 years after certification.
def test_certified_delay_is_not_yet_due_up_to_the_two_year_backstop():
    certified = replace(ACT, disp_first_submitted=day("2024-10-02"))
    assert status(certified, AS_OF) is LegalDuty.DELAYED
    assert status(certified, date(2026, 10, 3)) is LegalDuty.APPEARS_OVERDUE


def test_violation_wording_only_quotes_the_registry_flag_and_attributes_it_to_fda():
    assert fda_flag(ACT) == ""
    quoted = fda_flag(replace(ACT, fdaaa801_violation=True))
    assert "fdaaa801Violation" in quoted
    assert "FDA" in quoted
    assert "violation" not in quoted.replace("fdaaa801Violation", "").lower()


def _legal_record(study):
    """The fixture study made a probable ACT: every legal field changes, nothing WHO reads."""
    study = copy.deepcopy(study)
    protocol = study["protocolSection"]
    protocol.setdefault("oversightModule", {}).update(
        isFdaRegulatedDrug=True, isUsExport=True, fdaaa801Violation=True
    )
    protocol["designModule"]["phases"] = ["PHASE3"]
    protocol["contactsLocationsModule"] = {"locations": [{"country": "United States"}]}
    return study


def test_who_categories_of_the_fixture_snapshot_are_unchanged(tmp_path):
    meta = {"dataTimestamp": "2026-10-02T09:00:04", "codeSha": "abc", "snapshot": "data-x"}
    by_id = {}
    for name, records in (("plain", STUDIES), ("act", [_legal_record(s) for s in STUDIES])):
        export(tmp_path / name, map(parse, records), AS_OF, meta, name_sponsors=False)
        with gzip.open(tmp_path / name / "trials.csv.gz", "rt", encoding="utf-8") as f:
            for row in csv.DictReader(io.StringIO(f.read())):
                who = (row["category_keestra_2021"], row["category_v1_0"])
                by_id.setdefault(row["nct_id"], []).append(who)
    expected = {
        s["protocolSection"]["identificationModule"]["nctId"]: (
            classify(parse(s), AS_OF, KEESTRA_2021),
            classify(parse(s), AS_OF, V1_0),
        )
        for s in STUDIES
    }
    assert by_id == {nct: [who, who] for nct, who in expected.items()}
    # The pinned categories as of this task, so a change in either rule set shows here too.
    assert expected == {
        "NCT01174160": ("due_and_reported", "due_reported_late"),
        "NCT01916382": ("inconsistent", "inconsistent"),
        "NCT01245270": ("due_and_reported", "due_reported_in_time"),
    }


def test_site_wording_never_says_breach_or_illegal(site):  # noqa: F811
    text = pages(site).lower()
    assert "breach" not in text
    assert "illegal" not in text
    assert LegalDuty.APPEARS_OVERDUE in pages(site)
    assert "28 apr 2026" in text
    assert "ctis" in text


def test_parse_reads_the_legal_fields():
    trial = parse(_legal_record(STUDIES[0]))
    assert trial.phases == (Phase.PHASE3,)
    assert trial.location_countries == ("United States",)
    assert trial.is_us_export is True
    assert fda_flag(trial)

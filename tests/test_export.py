import copy
import csv
import gzip
import io
import json
from datetime import date

import pytest
from test_build import STUDIES

from trial_results_tracker.export import INDIVIDUALS, export
from trial_results_tracker.parse import parse

AS_OF = date(2026, 10, 2)
META = {"dataTimestamp": "2026-10-02T09:00:04", "codeSha": "abc123", "snapshot": "data-2026-10-05"}


def with_sponsor(study, name, sponsor_class, responsible_party="SPONSOR"):
    study = copy.deepcopy(study)
    module = study["protocolSection"]["sponsorCollaboratorsModule"]
    module["leadSponsor"] = {"name": name, "class": sponsor_class}
    module["responsibleParty"] = {"type": responsible_party}
    return study


# Three named organisations, one INDIV sponsor and one sponsor-investigator: two people.
RECORDS = [
    *STUDIES,
    with_sponsor(STUDIES[0], "Jane Q. Doe", "INDIV"),
    with_sponsor(STUDIES[1], "John Roe, MD", "OTHER", "SPONSOR_INVESTIGATOR"),
]
ORGANISATIONS = {
    s["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"] for s in STUDIES
}
PEOPLE = {"Jane Q. Doe", "John Roe, MD"}


def build(tmp_path, name_sponsors):
    export(tmp_path, map(parse, RECORDS), AS_OF, META, name_sponsors=name_sponsors)
    with gzip.open(tmp_path / "trials.csv.gz", "rt", encoding="utf-8") as f:
        trials_text = f.read()
    sponsors_text = (tmp_path / "sponsors.csv").read_text()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    return trials_text, sponsors_text, manifest


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


@pytest.fixture(params=[False, True], ids=["names-off", "names-on"])
def files(request, tmp_path):
    return build(tmp_path, request.param)


def test_no_individual_sponsor_name_in_either_file(files):
    trials_text, sponsors_text, _ = files
    for name in PEOPLE:
        assert name not in trials_text
        assert name not in sponsors_text


def test_every_row_carries_evidence_basis_and_data_date(files):
    trials_text, sponsors_text, _ = files
    for text in (trials_text, sponsors_text):
        for row in rows(text):
            assert row["evidence_basis"] == "registry only"
            assert row["data_date"] == "2026-10-02"


def test_legal_duty_is_not_determined_and_separate_from_category(files):
    for row in rows(files[0]):
        assert row["legal_duty"] == "not determined"
        assert row["category_keestra_2021"] and row["category_v1_0"]


def test_one_trial_row_per_record(files):
    assert len(rows(files[0])) == len(RECORDS)


def test_flag_off_publishes_no_sponsor_name_at_all(tmp_path):
    trials_text, sponsors_text, manifest = build(tmp_path, name_sponsors=False)
    for name in ORGANISATIONS | PEOPLE:
        assert name not in trials_text
        assert name not in sponsors_text
    assert {row["sponsor_raw"] for row in rows(trials_text)} == {""}
    assert {row["sponsor"] for row in rows(sponsors_text)} == {"INDUSTRY", "OTHER", INDIVIDUALS}
    assert manifest["sponsorNames"] is False


def test_flag_on_names_organisations_and_pools_individuals(tmp_path):
    trials_text, sponsors_text, manifest = build(tmp_path, name_sponsors=True)
    by_sponsor = {row["sponsor"]: row for row in rows(sponsors_text)}
    assert set(by_sponsor) == ORGANISATIONS | {INDIVIDUALS}
    assert by_sponsor[INDIVIDUALS]["trials"] == "2"
    pooled = [row for row in rows(trials_text) if row["sponsor_raw"] == INDIVIDUALS]
    assert len(pooled) == 2
    assert manifest["sponsorNames"] is True


def test_manifest_records_method_data_timestamp_code_and_licence(files):
    manifest = files[2]
    assert manifest["methods"] == ["Keestra-2021 replication", "v1.0"]
    assert manifest["dataTimestamp"] == "2026-10-02T09:00:04"
    assert manifest["codeSha"] == "abc123"
    assert manifest["licence"] == "CC BY 4.0"
    assert manifest["evidenceBasis"] == "registry only"
    assert manifest["legalDuty"] == "not determined"

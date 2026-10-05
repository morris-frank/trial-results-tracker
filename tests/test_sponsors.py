import csv
import gzip
import io
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from test_build import STUDIES
from test_export import META

from trial_results_tracker import sponsors
from trial_results_tracker.export import export
from trial_results_tracker.model import SponsorClass
from trial_results_tracker.parse import parse
from trial_results_tracker.sponsors import COLUMNS, Method

AS_OF = date(2026, 10, 2)
ALIASES = Path(__file__).resolve().parents[1] / "sponsors" / "aliases.csv"
REVIEWED = ("claude-opus-5-5 (agent review)", "2026-10-05")


def table(*rows: tuple[str, ...]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return out.getvalue()


def test_reviewed_row_maps_raw_string_to_sponsor_id():
    text = table(("Uppsala University", "uppsala-university", "048a87296", "ror-chosen", *REVIEWED))
    assert sponsors.lookup(text) == {"Uppsala University": "uppsala-university"}


def test_unreviewed_row_is_ignored():
    text = table(
        ("Uppsala University", "uppsala-university", "048a87296", "ror-chosen", "", ""),
        ("Uppsala Universitet", "uppsala-university", "048a87296", "ror-manual", "", "2026-10-05"),
    )
    assert sponsors.lookup(text) == {}


def test_aliases_share_one_sponsor_id_without_roll_up():
    text = table(
        ("Uppsala University", "uppsala-university", "048a87296", "ror-chosen", *REVIEWED),
        ("Uppsala Universitet", "uppsala-university", "048a87296", "ror-manual", *REVIEWED),
        ("Uppsala University Hospital", "uppsala-university-hospital", "01apvbh93", "ror-chosen",
         *REVIEWED),
    )  # fmt: skip
    ids = sponsors.lookup(text)
    assert ids["Uppsala University"] == ids["Uppsala Universitet"]
    assert ids["Uppsala University Hospital"] != ids["Uppsala University"]


@pytest.mark.parametrize("method", ["", "fuzzy"])
def test_row_without_a_known_match_method_is_rejected(method):
    with pytest.raises(ValueError, match="match_method"):
        sponsors.lookup(table(("Acme", "acme", "", method, *REVIEWED)))


def test_duplicate_raw_string_is_rejected():
    row = ("Acme", "acme", "", "none", *REVIEWED)
    with pytest.raises(ValueError, match="Acme"):
        sponsors.lookup(table(row, row))


def ror_item(chosen: bool, ror: str, name: str, score: float = 1.0) -> dict:
    return {
        "chosen": chosen,
        "score": score,
        "organization": {
            "id": f"https://ror.org/{ror}",
            "names": [{"value": name, "types": ["ror_display", "label"]}],
        },
    }


def test_proposal_takes_only_the_chosen_ror_record_and_lands_unreviewed():
    items = [ror_item(False, "01apvbh93", "Uppsala University Hospital"),
             ror_item(True, "048a87296", "Uppsala University", 0.9)]  # fmt: skip
    row = sponsors.propose("Uppsala Universitet", items)
    assert row == ("Uppsala Universitet", "uppsala-university", "048a87296", "ror-chosen", "", "")


def test_proposal_ignores_a_high_score_that_ror_did_not_choose():
    row = sponsors.propose("Mayo Clinic", [ror_item(False, "02qp3tb03", "Mayo Clinic", 1.0)])
    assert row == ("Mayo Clinic", "mayo-clinic", "", "none", "", "")


def test_candidates_count_due_trials_per_raw_string_and_skip_individuals():
    due = parse(STUDIES[0])  # due, reported late
    not_due = parse(STUDIES[1])  # inconsistent: not a due trial
    trials = [
        *[replace(due, sponsor_raw="Big") for _ in range(3)],
        *[replace(due, sponsor_raw="Small") for _ in range(2)],
        *[replace(not_due, sponsor_raw="Small") for _ in range(5)],
        *[replace(due, sponsor_raw="Jane Doe", sponsor_class=SponsorClass.INDIV)
          for _ in range(3)],
    ]  # fmt: skip
    assert sponsors.candidates(trials, AS_OF, threshold=3) == ["Big"]


def test_export_writes_reviewed_sponsor_id_only_when_names_are_on(tmp_path):
    ids = {"University of Aberdeen": "university-of-aberdeen"}

    def column(name_sponsors: bool) -> dict[str, str]:
        export(tmp_path, map(parse, STUDIES), AS_OF, META, name_sponsors, ids)
        with gzip.open(tmp_path / "trials.csv.gz", "rt", encoding="utf-8") as f:
            return {row["nct_id"]: row["sponsor_id"] for row in csv.DictReader(f)}

    assert column(True) == {
        "NCT01174160": "",
        "NCT01916382": "",
        "NCT01245270": "university-of-aberdeen",
    }
    assert set(column(False).values()) == {""}


def test_committed_table_has_a_method_on_every_row_and_reviews_every_row():
    rows = list(csv.DictReader(io.StringIO(ALIASES.read_text())))
    assert rows
    assert {row["match_method"] for row in rows} <= {m.value for m in Method}
    assert all(row["reviewed_by"] and row["reviewed_on"] for row in rows)
    assert len(sponsors.lookup(ALIASES.read_text())) == len(rows)

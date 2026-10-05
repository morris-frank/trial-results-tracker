import copy
import csv
import gzip
import re
from datetime import date
from pathlib import Path

import pytest
from test_build import STUDIES, pages, write_snapshot
from test_sponsors import REVIEWED, table

from trial_results_tracker import __main__ as cli
from trial_results_tracker import sponsors
from trial_results_tracker.parse import parse
from trial_results_tracker.stats import wilson

AS_OF = date(2026, 10, 2)
ROOT = Path(__file__).resolve().parents[1]


def nct(n: int) -> str:
    return f"NCT{n:08d}"


def study(n, sponsor, *, reported=True, stale=False, sponsor_class="OTHER", party="SPONSOR"):
    """A copy of a fixture study: due and reported in time (Aberdeen), due with no results,
    or inconsistent (Liverpool's record, with no actual primary completion read)."""
    record = copy.deepcopy(STUDIES[1] if stale else STUDIES[2])
    protocol = record["protocolSection"]
    protocol["identificationModule"]["nctId"] = nct(n)
    protocol["sponsorCollaboratorsModule"]["leadSponsor"] = {
        "name": sponsor,
        "class": sponsor_class,
    }
    protocol["sponsorCollaboratorsModule"]["responsibleParty"] = {"type": party}
    if not reported and not stale:
        for key in ("resultsFirstSubmitDate", "resultsFirstSubmitQcDate"):
            protocol["statusModule"].pop(key)
        protocol["statusModule"].pop("resultsFirstPostDateStruct")
        record["hasResults"] = False
    return record


def batch(sponsor, due, unreported, start, **kwargs):
    """`due` due trials for `sponsor` numbered from `start`, the first `unreported` unreported."""
    return [study(start + i, sponsor, reported=i >= unreported, **kwargs) for i in range(due)]


def rank(*records, ids):
    return sponsors.rank([parse(r) for r in records], AS_OF, ids)


def test_only_reviewed_sponsors_with_at_least_20_due_trials_rank():
    ranked = rank(
        *batch("Alpha University", 20, 5, 0),
        *batch("Beta Hospital", 19, 19, 100),
        *batch("Gamma Inc", 25, 25, 200),  # no reviewed alias row
        ids={"Alpha University": "alpha-university", "Beta Hospital": "beta-hospital"},
    )
    assert [r.sponsor_id for r in ranked] == ["alpha-university"]


def test_ranked_by_point_estimate_with_its_wilson_ci():
    ranked = rank(
        *batch("Alpha", 20, 10, 0), *batch("Beta", 20, 15, 100), ids={"Alpha": "a", "Beta": "b"}
    )
    assert [(r.sponsor_id, r.rank, r.tied) for r in ranked] == [("b", 1, False), ("a", 2, False)]
    assert (ranked[0].low, ranked[0].high) == wilson(15, 20)


def test_ties_break_alphabetically_and_are_marked():
    ranked = rank(
        *batch("Zeta", 20, 10, 0),
        *batch("Alpha", 40, 20, 100),
        *batch("Mid", 20, 5, 200),
        ids={"Zeta": "z", "Alpha": "a", "Mid": "m"},
    )
    assert [(r.name, r.rank, r.tied) for r in ranked] == [
        ("Alpha", 1, True),
        ("Zeta", 1, True),
        ("Mid", 3, False),
    ]


def test_individual_and_sponsor_investigator_trials_never_rank():
    ranked = rank(
        *batch("Jane Q. Doe", 20, 20, 0, sponsor_class="INDIV"),
        *batch("John Roe, MD", 20, 20, 100, party="SPONSOR_INVESTIGATOR"),
        ids={"Jane Q. Doe": "jane-q-doe", "John Roe, MD": "john-roe-md"},
    )
    assert ranked == []


def test_aliases_pool_under_one_sponsor_id_named_by_the_commonest_string():
    ranked = rank(
        *batch("Uppsala University", 11, 2, 0),
        *batch("Uppsala Universitet", 9, 2, 100),
        ids={"Uppsala University": "uppsala", "Uppsala Universitet": "uppsala"},
    )
    assert [(r.name, r.due, len(r.unreported)) for r in ranked] == [("Uppsala University", 20, 4)]
    assert ranked[0].aliases == ("Uppsala Universitet", "Uppsala University")


def test_stale_and_inconsistent_trials_go_to_the_check_list_not_the_count():
    ranked = rank(*batch("Alpha", 20, 5, 0), study(50, "Alpha", stale=True), ids={"Alpha": "alpha"})
    assert (ranked[0].due, len(ranked[0].unreported)) == (20, 5)
    assert [nct_id for nct_id, _ in ranked[0].check] == [nct(50)]


SPONSOR, PERSON, SMALL = "Alpha University", "Jane Q. Doe", "Beta Hospital"


@pytest.fixture
def snap(tmp_path, monkeypatch):
    aliases = tmp_path / "aliases.csv"
    aliases.write_text(
        table(
            (SPONSOR, "alpha-university", "", "none", *REVIEWED),
            (PERSON, "jane-q-doe", "", "none", *REVIEWED),
            (SMALL, "beta-hospital", "", "none", *REVIEWED),
        )
    )
    disputes = tmp_path / "disputes.csv"
    with disputes.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("nct_id", "opened_on", "issue", "note"))
        writer.writerow((nct(0), "2026-10-04", "https://example.org/1", "Results are in review."))
    monkeypatch.setattr(cli, "ALIASES", aliases)
    monkeypatch.setattr(cli, "DISPUTES", disputes)
    records = [
        *batch(SPONSOR, 20, 6, 0),
        study(50, SPONSOR, stale=True),
        *batch(PERSON, 20, 20, 100, sponsor_class="INDIV"),
        *batch(SMALL, 19, 19, 200),
    ]
    return write_snapshot(tmp_path / "snap", studies=records)


def build(tmp_path, snap, monkeypatch, name_sponsors):
    monkeypatch.setenv("NAME_SPONSORS", "1" if name_sponsors else "0")
    out = tmp_path / ("named" if name_sponsors else "unnamed")
    cli.main(["build", "--out", str(out), "--snapshot-dir", str(snap)])
    return out


def everything(out: Path) -> str:
    return "\n".join(
        gzip.decompress(f.read_bytes()).decode() if f.suffix == ".gz" else f.read_text()
        for f in sorted(out.rglob("*"))
        if f.is_file() and f.suffix != ".png"
    )


def test_flag_off_renders_no_sponsor_name_anywhere_in_the_site(tmp_path, snap, monkeypatch):
    out = build(tmp_path, snap, monkeypatch, name_sponsors=False)
    text = everything(out)
    for name in (SPONSOR, PERSON, SMALL, "alpha-university", "jane-q-doe", "beta-hospital"):
        assert name not in text
    assert not list(out.glob("sponsor-*.html"))


def test_flag_on_no_individual_sponsor_ranks(tmp_path, snap, monkeypatch):
    out = build(tmp_path, snap, monkeypatch, name_sponsors=True)
    assert PERSON not in pages(out)
    assert not (out / "sponsor-jane-q-doe.html").exists()


def test_flag_on_league_table_shows_ranked_sponsor_with_ci_and_method(tmp_path, snap, monkeypatch):
    out = build(tmp_path, snap, monkeypatch, name_sponsors=True)
    index = (out / "index.html").read_text()
    low, high = wilson(6, 20)
    assert f'<a href="sponsor-alpha-university.html">{SPONSOR}</a>' in index
    assert f"{low:.1%} to {high:.1%}" in index
    # Below the threshold: neither ranked nor given a page.
    assert SMALL not in pages(out)
    assert sorted(p.name for p in out.glob("sponsor-*.html")) == ["sponsor-alpha-university.html"]
    for cell in re.findall(r'<td class="n">(.*?)</td>', pages(out)):
        assert '<span class="method">' in cell and "v1.0" in cell, cell


def test_sponsor_page_links_unreported_trials_and_lists_stale_ones_apart(
    tmp_path, snap, monkeypatch
):
    out = build(tmp_path, snap, monkeypatch, name_sponsors=True)
    unreported, check = (out / "sponsor-alpha-university.html").read_text().split('id="check"')
    links = re.findall(r'href="https://clinicaltrials.gov/study/(NCT\d+)"', unreported)
    assert links == [nct(i) for i in range(6)]
    assert nct(50) in check and nct(50) not in unreported


def test_dispute_note_is_shown_and_never_removes_the_trial(tmp_path, snap, monkeypatch):
    out = build(tmp_path, snap, monkeypatch, name_sponsors=True)
    unreported = (out / "sponsor-alpha-university.html").read_text().split('id="check"')[0]
    assert f"https://clinicaltrials.gov/study/{nct(0)}" in unreported
    assert "Disputed on 2026-10-04: Results are in review." in unreported


def test_methodology_points_legal_readers_to_the_bennett_trackers(tmp_path, snap, monkeypatch):
    methodology = (build(tmp_path, snap, monkeypatch, False) / "methodology.html").read_text()
    assert "https://fdaaa.trialstracker.net/" in methodology
    assert "https://eu.trialstracker.net/" in methodology


def test_every_page_links_the_correction_form_and_public_log(tmp_path, snap, monkeypatch):
    out = build(tmp_path, snap, monkeypatch, name_sponsors=True)
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "correction.yml").exists()
    assert (ROOT / "CORRECTIONS.md").exists()
    for page in out.glob("*.html"):
        text = page.read_text()
        assert "issues/new?template=correction.yml" in text
        assert "CORRECTIONS.md" in text

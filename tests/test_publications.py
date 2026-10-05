import copy
import csv
import gzip
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from test_build import STUDIES, write_snapshot

from trial_results_tracker import publications, snapshot
from trial_results_tracker.__main__ import main
from trial_results_tracker.publications import EVIDENCE_BASIS, METHOD, link, mentions, read

# Recorded 2026-10-05: Europe PMC core search for the three fixture NCT IDs at pageSize=2,
# trimmed to the fields used. Opaque cursors are replaced by "page-2" and "page-3".
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "europepmc-three-ids.json").read_text())
IDS = ["NCT01174160", "NCT01916382", "NCT01245270"]
TODAY = date(2026, 10, 5)


def fake_europepmc():
    requests = []

    def get(url):
        requests.append(url)
        cursor = parse_qs(urlsplit(url).query)["cursorMark"][0]
        return FIXTURE["pages"][{"*": 0, "page-2": 1, "page-3": 2}[cursor]]

    return get, requests


def linked(tmp_path, ids=IDS):
    get, requests = fake_europepmc()
    path = link(tmp_path, ids, get=get, sleep=lambda _: None, today=TODAY)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return list(csv.DictReader(f)), requests


def test_query_is_an_exact_title_abstract_phrase_per_id(tmp_path):
    _, requests = linked(tmp_path)
    query = parse_qs(urlsplit(requests[0]).query)["query"][0]
    assert query == FIXTURE["query"]


def test_follows_the_cursor_until_an_empty_page(tmp_path):
    _, requests = linked(tmp_path)
    assert len(requests) == 3


def test_links_only_the_id_each_record_mentions(tmp_path):
    rows, _ = linked(tmp_path)
    found = [row for row in rows if row["id"]]
    assert {row["nct_id"] for row in found} == {"NCT01916382"}
    assert {row["pmid"] for row in found} == {"37446173", "36270742", "32822600"}


def test_every_searched_trial_has_a_row_even_without_a_hit(tmp_path):
    rows, _ = linked(tmp_path)
    assert {row["nct_id"] for row in rows} == set(IDS)
    empty = [row for row in rows if not row["id"]]
    assert {row["nct_id"] for row in empty} == {"NCT01174160", "NCT01245270"}


def test_every_row_carries_method_query_date_and_evidence_basis(tmp_path):
    rows, _ = linked(tmp_path)
    for row in rows:
        assert row["method"] == METHOD
        assert row["query_date"] == "2026-10-05"
        assert row["evidence_basis"] == EVIDENCE_BASIS == "registry plus NCT-ID publication search"


def test_mentions_requires_the_whole_id_not_a_prefix_or_neighbour():
    record = {"title": "Trial NCT019163820 and nct01174160", "abstractText": "see NCT01245270."}
    assert mentions(record, {"NCT01916382", "NCT01174160", "NCT01245270"}) == {
        "NCT01174160",
        "NCT01245270",
    }


def test_read_groups_found_and_searched(tmp_path):
    linked(tmp_path)
    result = read(tmp_path / "publications.csv.gz")
    assert result.searched == set(IDS)
    assert result.found == {"NCT01916382"}
    assert result.query_date == "2026-10-05"


# --- build wiring -------------------------------------------------------------------------


def unreported_snapshot(directory: Path, with_publications: bool) -> Path:
    """The fixture snapshot with NCT01916382 marked completed, so it is due and unreported."""
    write_snapshot(directory)
    studies = copy.deepcopy(STUDIES)
    studies[1]["protocolSection"]["statusModule"]["overallStatus"] = "COMPLETED"
    with gzip.open(directory / "ctgov-2026-10-05.jsonl.gz", "wt", encoding="utf-8") as lines:
        for study in studies:
            lines.write(json.dumps(study) + "\n")
    if with_publications:
        get, _ = fake_europepmc()
        link(directory, ["NCT01916382"], get=get, sleep=lambda _: None, today=TODAY)
        manifest = snapshot.manifest(directory)
        manifest["publications"] = "publications.csv.gz"
        (directory / "manifest.json").write_text(json.dumps(manifest))
    return directory


def built(tmp_path, with_publications):
    snap = unreported_snapshot(tmp_path / "snap", with_publications)
    out = tmp_path / "dist"
    main(["build", "--out", str(out), "--snapshot-dir", str(snap)])
    return out


def registry_figures(index: str) -> str:
    """Everything from the page heading to the end of the category table: the headline,
    the upper bound and every registry count."""
    return index[index.index("<h1>") : index.index("</table>")]


def test_headline_numbers_are_byte_identical_with_and_without_publications(tmp_path):
    without = (built(tmp_path / "a", False) / "index.html").read_text()
    with_ = (built(tmp_path / "b", True) / "index.html").read_text()
    assert "possible publication found" in with_
    assert registry_figures(without).encode() == registry_figures(with_).encode()


def test_site_shows_the_share_with_its_evidence_basis_and_query_date(tmp_path):
    index = (built(tmp_path, True) / "index.html").read_text()
    section = index[index.index("Possible publications") :]
    assert '<span class="n">1</span> of <span class="n">1</span>' in section
    assert "registry plus NCT-ID publication search" in section
    assert "2026-10-05" in section
    assert 'href="publications.csv.gz"' in section


def test_site_without_publications_has_no_secondary_measure(tmp_path):
    index = (built(tmp_path, False) / "index.html").read_text()
    assert "possible publication found" not in index
    assert "publications.csv.gz" not in index


def test_trial_download_marks_possible_publication_with_its_basis(tmp_path):
    out = built(tmp_path, True)
    with gzip.open(out / "trials.csv.gz", "rt", encoding="utf-8") as f:
        by_id = {row["nct_id"]: row for row in csv.DictReader(f)}
    row = by_id["NCT01916382"]
    assert row["possible_publication"] == "found"
    assert row["possible_publication_basis"] == "registry plus NCT-ID publication search"
    assert row["possible_publication_query_date"] == "2026-10-05"
    assert row["evidence_basis"] == "registry only"  # the registry category is unchanged
    assert by_id["NCT01174160"]["possible_publication"] == ""  # not searched
    manifest = json.loads((out / "manifest.json").read_text())
    assert "publications.csv.gz" in manifest["files"]
    assert manifest["possiblePublication"]["evidenceBasis"] == EVIDENCE_BASIS
    assert (out / "publications.csv.gz").exists()


def test_download_fetches_the_publications_file_the_manifest_names(tmp_path):
    unreported_snapshot(tmp_path / "releases" / "data-2026-10-05", with_publications=True)
    base = (tmp_path / "releases").as_uri()
    out = snapshot.download("data-2026-10-05", tmp_path / "got", base=base)
    assert (out / "publications.csv.gz").exists()


def test_fetch_searches_only_due_not_reported_trials(tmp_path, monkeypatch):
    snap = unreported_snapshot(tmp_path, with_publications=False)
    searched = []

    def fake_link(out, ids, **_):
        searched.extend(ids)
        return out / "publications.csv.gz"

    monkeypatch.setattr(publications, "link", fake_link)
    publications.link_snapshot(snap, today=TODAY)
    assert searched == ["NCT01916382"]
    assert snapshot.manifest(snap)["publications"] == "publications.csv.gz"

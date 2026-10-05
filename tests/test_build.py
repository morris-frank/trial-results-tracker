import gzip
import json
from pathlib import Path

import pytest

from trial_results_tracker import snapshot
from trial_results_tracker.__main__ import main
from trial_results_tracker.fetch import code_sha

FIXTURES = Path(__file__).parent / "fixtures"
# The three studies of the recorded two-page pull: one due and reported, two due and not.
STUDIES = [
    study
    for page in json.loads((FIXTURES / "ctgov-two-pages.json").read_text())["pages"]
    for study in page["studies"]
]


def write_snapshot(
    directory: Path, rows_written: int | None = None, studies: list[dict] = STUDIES
) -> Path:
    rows_written = len(studies) if rows_written is None else rows_written
    directory.mkdir(parents=True, exist_ok=True)
    with gzip.open(directory / "ctgov-2026-10-05.jsonl.gz", "wt", encoding="utf-8") as lines:
        for study in studies:
            lines.write(json.dumps(study) + "\n")
    manifest = {
        "apiVersion": "2.0.5",
        "dataTimestamp": "2026-10-02T09:00:04",
        "totalCount": rows_written,
        "rowsWritten": rows_written,
        "file": "ctgov-2026-10-05.jsonl.gz",
        "codeSha": "663e4c7758104e300f6a6b0f1fda862261e38c65",
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return directory


@pytest.fixture
def site(tmp_path):
    out = tmp_path / "dist"
    main(["build", "--out", str(out), "--snapshot-dir", str(write_snapshot(tmp_path / "snap"))])
    return out


def pages(out: Path) -> str:
    return "\n".join(page.read_text() for page in sorted(out.glob("*.html")))


def test_overview_shows_counts_method_label_data_date_and_code_sha(site):
    index = (site / "index.html").read_text()
    assert "v1.0" in index
    assert "2026-10-02" in index
    assert code_sha()[:12] in index
    assert "3 trials" in index
    assert '<td class="n">1 <span class="method">v1.0</span></td>' in index
    assert '<td class="n">33.3% <span class="method">v1.0</span></td>' in index


def test_methodology_states_rules_and_modifications(site):
    methodology = (site / "methodology.html").read_text()
    assert "395 days" in methodology
    assert "Modifications" in methodology


def test_footer_names_publisher_credits_registry_and_disclaims_soilytix(site):
    for page in site.glob("*.html"):
        text = page.read_text()
        assert "Maurice Frank" in text
        assert "ClinicalTrials.gov" in text
        assert "not affiliated with Soilytix" in text


def test_overview_links_downloads_manifest_and_licence(site):
    index = (site / "index.html").read_text()
    for name in ("trials.csv.gz", "sponsors.csv", "manifest.json"):
        assert f'href="{name}"' in index
        assert (site / name).exists()
    assert "CC BY 4.0" in index


def test_output_has_no_script(site):
    assert "<script" not in pages(site).lower()


def test_row_count_mismatch_fails_the_build(tmp_path):
    snap = write_snapshot(tmp_path / "snap", rows_written=len(STUDIES) + 1)
    with pytest.raises(snapshot.RowMismatch):
        main(["build", "--out", str(tmp_path / "dist"), "--snapshot-dir", str(snap)])
    assert not (tmp_path / "dist" / "index.html").exists()


def test_download_fetches_manifest_and_snapshot(tmp_path):
    release = write_snapshot(tmp_path / "releases" / "data-2026-10-05")
    base = (tmp_path / "releases").as_uri()
    out = snapshot.download("data-2026-10-05", tmp_path / "got", base=base)
    assert snapshot.manifest(out)["file"] == "ctgov-2026-10-05.jsonl.gz"
    assert (out / "ctgov-2026-10-05.jsonl.gz").read_bytes() == (
        release / "ctgov-2026-10-05.jsonl.gz"
    ).read_bytes()


def test_download_failure_raises(tmp_path):
    with pytest.raises(OSError):
        snapshot.download("data-2026-10-05", tmp_path / "got", base=(tmp_path / "none").as_uri())


def test_overview_headline_is_v1_with_ci_denominator_upper_bound_and_data_date(site):
    index = (site / "index.html").read_text()
    # Under v1.0 the fixture's three trials are two due and reported, one inconsistent.
    assert '<span class="n">0.0%</span> of <span class="n">2</span> due trials' in index
    assert '95% CI <span class="n">0.0%</span> to <span class="n">65.8%</span>' in index
    assert "within 12 months of primary completion, as of 2026-10-02. Method v1.0." in index
    assert 'Upper bound: <span class="n">33.3%</span> of <span class="n">3</span> trials' in index
    for word in ("failed", "hid "):
        assert word not in index.lower()


def test_headline_with_nothing_due_says_so_instead_of_dividing_by_zero():
    from collections import Counter

    from trial_results_tracker.classify import Category
    from trial_results_tracker.render import headline

    html = headline(Counter({Category.ONGOING: 4}), "v1.0", "2026-10-02")
    assert html == "    <p>No trials are due under method v1.0 as of 2026-10-02.</p>"

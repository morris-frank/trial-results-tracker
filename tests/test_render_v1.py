import re
from datetime import date

import pytest
from test_build import STUDIES, pages, write_snapshot

from trial_results_tracker.__main__ import main
from trial_results_tracker.crosswalk import crosswalk
from trial_results_tracker.parse import parse
from trial_results_tracker.render import LABELS

AS_OF = date(2026, 10, 2)  # the fixture manifest's dataTimestamp


@pytest.fixture
def site(tmp_path):
    out = tmp_path / "dist"
    main(["build", "--out", str(out), "--snapshot-dir", str(write_snapshot(tmp_path / "snap"))])
    return out


def test_overview_defaults_to_v1_0(site):
    index = (site / "index.html").read_text()
    assert "v1.0" in index
    # The fixture's three trials under v1.0: one in time, one late, one inconsistent.
    for label in ("Due, results submitted in time", "Due, results submitted late"):
        assert re.search(rf"<td>{label}</td><td class=\"n\">1 ", index)
    assert "<td>Due, results submitted</td>" not in index  # Keestra's unsplit category


def test_methodology_renders_the_crosswalk_for_the_snapshot(site):
    methodology = (site / "methodology.html").read_text()
    table = methodology.split('<table id="crosswalk">')[1].split("</table>")[0]
    cells = re.findall(r"<td>(.*?)</td><td>(.*?)</td><td class=\"n\">([\d,]+) ", table)
    expected = crosswalk([parse(study) for study in STUDIES], AS_OF)
    assert {(k, v, int(n)) for k, v, n in cells} == {
        (LABELS[keestra], LABELS[v1], n) for (keestra, v1), n in expected.items()
    }


def test_every_rendered_number_carries_the_v1_0_label(site):
    text = pages(site)
    cells = re.findall(r'<td class="n">(.*?)</td>', text)
    assert cells
    for cell in cells:
        assert '<span class="method">' in cell and "v1.0" in cell, cell
    assert "3 trials, v1.0" in text


def test_output_contains_no_sponsor_name(site):
    names = {
        study["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"]
        for study in STUDIES
    }
    assert len(names) == 3
    text = pages(site)
    for name in names:
        assert name not in text

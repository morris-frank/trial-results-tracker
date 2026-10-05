import csv
from pathlib import Path

import pytest
from test_build import write_snapshot

from trial_results_tracker.__main__ import main
from trial_results_tracker.classify import Category
from trial_results_tracker.validate import (
    allocate,
    cohen_kappa,
    draw,
    read_coding,
    score,
    wilson,
)

C = Category


def population() -> dict[str, Category]:
    cats = [C.DUE_NOT_REPORTED] * 50 + [C.ONGOING] * 30 + [C.STATUS_OVERDUE] * 3
    return {f"NCT{i:08d}": cat for i, cat in enumerate(cats)}


def test_allocate_is_equal_and_gives_a_small_category_all_its_trials():
    sizes = {C.DUE_NOT_REPORTED: 50, C.ONGOING: 30, C.STATUS_OVERDUE: 3}
    assert allocate(sizes, 30) == {C.DUE_NOT_REPORTED: 14, C.ONGOING: 13, C.STATUS_OVERDUE: 3}
    assert allocate(sizes, 1000) == sizes


def test_same_seed_and_snapshot_give_the_same_sample():
    assert draw(population(), 30, seed=7) == draw(population(), 30, seed=7)
    assert draw(population(), 30, seed=7) != draw(population(), 30, seed=8)


def test_sample_is_stratified_and_ignores_input_order():
    shuffled = dict(reversed(population().items()))
    sample = draw(population(), 30, seed=7)
    assert draw(shuffled, 30, seed=7) == sample
    assert [cat for _, cat in sample].count(C.STATUS_OVERDUE) == 3
    assert len({nct for nct, _ in sample}) == 30


def test_wilson_matches_the_textbook_value():
    low, high = wilson(8, 10)
    assert low == pytest.approx(0.4902, abs=1e-4)
    assert high == pytest.approx(0.9433, abs=1e-4)
    assert wilson(0, 0) == (0.0, 1.0)


def test_cohen_kappa_on_a_toy_table():
    a = ["x", "x", "y", "y"]
    assert cohen_kappa(a, a) == 1.0
    assert cohen_kappa(a, ["x", "y", "x", "y"]) == 0.0


def test_score_on_a_toy_table():
    key = {"NCT1": C.ONGOING, "NCT2": C.ONGOING, "NCT3": C.DUE_NOT_REPORTED}
    coder_a = {"NCT1": C.ONGOING, "NCT2": C.ONGOING, "NCT3": C.DUE_NOT_REPORTED}
    coder_b = {"NCT1": C.ONGOING, "NCT2": C.STATUS_OVERDUE, "NCT3": C.DUE_NOT_REPORTED}
    result = score(key, coder_a, coder_b)
    assert result.per_category[C.ONGOING] == (2, 2, 1)  # n, coder A agrees, coder B agrees
    assert result.per_category[C.DUE_NOT_REPORTED] == (1, 1, 1)
    assert result.coder_agreement == 2
    assert result.n == 3


def test_score_refuses_a_coding_that_misses_a_sampled_trial():
    key = {"NCT1": C.ONGOING, "NCT2": C.ONGOING}
    with pytest.raises(ValueError, match="NCT2"):
        score(key, {"NCT1": C.ONGOING}, key)


def test_read_coding_refuses_an_unknown_category(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("nct_id,url,category,note\nNCT1,u,maybe,\n")
    with pytest.raises(ValueError, match="maybe"):
        read_coding(path)


def test_cli_draws_a_blind_coding_csv_then_scores_it(tmp_path):
    out = tmp_path / "validation"
    snap = write_snapshot(tmp_path / "snap")
    main(["validate", "sample", "--out", str(out), "--snapshot-dir", str(snap), "--seed", "1"])
    stem = out / "v1.0-data-2026-10-05"
    coding = list(csv.DictReader(Path(f"{stem}-coding.csv").read_text().splitlines()))
    assert {row["category"] for row in coding} == {""}  # blind: coders never see the key
    assert all(row["url"] == f"https://clinicaltrials.gov/study/{row['nct_id']}" for row in coding)
    key = list(csv.DictReader(Path(f"{stem}-sample.csv").read_text().splitlines()))
    assert len(key) == len(coding) == 3
    assert "coding pending" in Path(f"{stem}.md").read_text()

    for coder in ("a", "b"):
        with (tmp_path / f"{coder}.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, ["nct_id", "url", "category", "note"])
            writer.writeheader()
            writer.writerows({**row, "category": row["category"], "note": ""} for row in key)
    main(
        ["validate", "score", str(stem) + "-sample.csv"]
        + [str(tmp_path / "a.csv"), str(tmp_path / "b.csv")]
    )
    report = Path(f"{stem}.md").read_text()
    assert "coding pending" not in report
    assert "3 of 3" in report

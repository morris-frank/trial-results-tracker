from collections import Counter

from trial_results_tracker.classify import Category
from trial_results_tracker.notify import Summary, message

RUN = "https://github.com/morris-frank/trial-results-tracker/actions/runs/1"
PREVIOUS = Summary(
    "data-2026-10-05",
    "2026-10-02",
    1000,
    Counter({Category.DUE_NOT_REPORTED: 300, Category.DUE_AND_REPORTED: 700}),
)
CURRENT = Summary(
    "data-2026-10-12",
    "2026-10-09",
    1010,
    Counter({Category.DUE_NOT_REPORTED: 290, Category.DUE_AND_REPORTED: 715, Category.ONGOING: 5}),
)


def test_success_names_release_rows_and_run():
    text = message("success", RUN, "Keestra-2021 replication", CURRENT, PREVIOUS)
    assert text.splitlines()[0] == "Refresh success"
    assert "https://github.com/morris-frank/trial-results-tracker/releases/tag/data-2026-10-12" in (
        text
    )
    assert "Data date 2026-10-09: 1,010 rows (+10 vs data-2026-10-05)" in text
    assert RUN in text


def test_success_lists_every_category_with_its_delta():
    text = message("success", RUN, "Keestra-2021 replication", CURRENT, PREVIOUS)
    assert "Keestra-2021 replication, versus data-2026-10-05:" in text
    assert "Due, no results submitted: 290 (-10)" in text
    assert "Due, results submitted: 715 (+15)" in text
    assert "Ongoing: 5 (+5)" in text
    assert "Inconsistent or stale record: 0 (+0)" in text


def test_success_without_previous_says_there_is_no_comparison():
    text = message("success", RUN, "Keestra-2021 replication", CURRENT, None)
    assert "Data date 2026-10-09: 1,010 rows" in text
    assert "no comparison with the previous snapshot" in text
    assert "Due, no results submitted: 290\n" in text + "\n"


def test_failure_is_flagged_and_claims_no_release():
    text = message("failure", RUN, "Keestra-2021 replication", None, None)
    assert text.splitlines()[0] == "Refresh FAILURE"
    assert "releases/tag" not in text
    assert RUN in text


def test_failure_after_fetch_reports_rows_but_no_release_or_categories():
    fetched = Summary("data-2026-10-12", "2026-10-09", 1010, None)
    text = message("failure", RUN, "Keestra-2021 replication", fetched, PREVIOUS)
    assert "1,010 rows" in text
    assert "releases/tag" not in text
    assert "Due, no results submitted" not in text

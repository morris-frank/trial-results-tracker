from collections import Counter

from trial_results_tracker.classify import V1_0, Category
from trial_results_tracker.notify import Summary, message

RUN = "https://github.com/morris-frank/trial-results-tracker/actions/runs/1"
PREVIOUS = Summary(
    "data-2026-10-05",
    "2026-10-02",
    1000,
    Counter(
        {
            Category.DUE_NOT_REPORTED: 300,
            Category.DUE_REPORTED_IN_TIME: 500,
            Category.DUE_REPORTED_LATE: 196,
            Category.DUE_RETURNED_IN_QC: 4,
        }
    ),
)
CURRENT = Summary(
    "data-2026-10-12",
    "2026-10-09",
    1010,
    Counter(
        {
            Category.DUE_NOT_REPORTED: 290,
            Category.DUE_REPORTED_IN_TIME: 515,
            Category.DUE_REPORTED_LATE: 196,
            Category.DUE_RETURNED_IN_QC: 4,
            Category.STATUS_OVERDUE: 5,
        }
    ),
)


def test_success_names_release_rows_and_run():
    text = message("success", RUN, V1_0.name, CURRENT, PREVIOUS)
    assert text.splitlines()[0] == "Refresh success"
    assert "https://github.com/morris-frank/trial-results-tracker/releases/tag/data-2026-10-12" in (
        text
    )
    assert "Data date 2026-10-09: 1,010 rows (+10 vs data-2026-10-05)" in text
    assert RUN in text


def test_success_lists_v1_categories_with_their_deltas():
    text = message("success", RUN, V1_0.name, CURRENT, PREVIOUS)
    assert "v1.0, versus data-2026-10-05:" in text
    assert "Due, no results submitted: 290 (-10)" in text
    assert "Due, results submitted in time: 515 (+15)" in text
    assert "Due, results submitted late: 196 (+0)" in text
    assert "Due, submitted but returned in quality control: 4 (+0)" in text
    assert "Status overdue (still open long after primary completion): 5 (+5)" in text
    # Keestra's undivided category, which v1.0 never produces, is not reported as a zero.
    assert "Due, results submitted:" not in text


def test_success_without_previous_says_there_is_no_comparison():
    text = message("success", RUN, V1_0.name, CURRENT, None)
    assert "Data date 2026-10-09: 1,010 rows" in text
    assert "no comparison with the previous snapshot" in text
    assert "Due, no results submitted: 290\n" in text + "\n"


def test_failure_is_flagged_and_claims_no_release():
    text = message("failure", RUN, V1_0.name, None, None)
    assert text.splitlines()[0] == "Refresh FAILURE"
    assert "releases/tag" not in text
    assert RUN in text


def test_failure_after_fetch_reports_rows_but_no_release_or_categories():
    fetched = Summary("data-2026-10-12", "2026-10-09", 1010, None)
    text = message("failure", RUN, V1_0.name, fetched, PREVIOUS)
    assert "1,010 rows" in text
    assert "releases/tag" not in text
    assert "Due, no results submitted" not in text

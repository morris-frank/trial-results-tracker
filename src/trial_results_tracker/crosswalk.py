"""Cross-tabulate the Keestra-2021 and v1.0 rule sets (docs/plan.md T6). Pure."""

from collections import Counter
from collections.abc import Iterable
from datetime import date

from trial_results_tracker.classify import KEESTRA_2021, V1_0, Category, classify
from trial_results_tracker.model import Trial


def crosswalk(trials: Iterable[Trial], as_of: date) -> Counter[tuple[Category, Category]]:
    """Trial counts keyed by (Keestra-2021 category, v1.0 category)."""
    return Counter((classify(t, as_of, KEESTRA_2021), classify(t, as_of, V1_0)) for t in trials)

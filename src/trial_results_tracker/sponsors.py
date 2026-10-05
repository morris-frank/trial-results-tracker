"""The sponsor alias table, sponsors/aliases.csv: raw lead-sponsor strings to sponsor IDs
(docs/plan.md T10). Pure: callers pass text and parsed ROR responses in.

Only reviewed rows are used. Aliases only, no parent/child roll-up (D6): a hospital and
its university keep separate IDs. Seed proposals take ROR's `chosen: true` record and
nothing else, since ROR advises against trusting its scores
(https://ror.readme.io/docs/matching).
"""

import csv
import io
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from datetime import date
from enum import StrEnum

from trial_results_tracker.classify import V1_0, classify
from trial_results_tracker.export import is_individual
from trial_results_tracker.model import Trial
from trial_results_tracker.render import DUE

COLUMNS = ("sponsor_raw", "sponsor_id", "ror_id", "match_method", "reviewed_by", "reviewed_on")
THRESHOLD = 20  # due trials, D6's ranking threshold


class Method(StrEnum):
    ROR_CHOSEN = "ror-chosen"  # ROR's affiliation match marked the record chosen
    ROR_MANUAL = "ror-manual"  # a reviewer picked the ROR record ROR did not choose
    NONE = "none"  # no ROR record; the ID is the raw string's own


# Letters NFKD leaves without an ASCII base, so "Sağlık" keeps its dotless i.
_UNDECOMPOSED = str.maketrans({"ı": "i", "ø": "o", "Ø": "O", "æ": "ae", "ß": "ss", "ł": "l"})


def slug(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.translate(_UNDECOMPOSED))
    ascii_name = decomposed.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def lookup(text: str) -> dict[str, str]:
    """Reviewed `sponsor_raw -> sponsor_id` from the table's CSV text.

    A row needs both `reviewed_by` and `reviewed_on` to count. Every row, reviewed or not,
    must carry a known `match_method` and a raw string no other row has."""
    ids: dict[str, str] = {}
    seen: set[str] = set()
    for row in csv.DictReader(io.StringIO(text)):
        raw = row["sponsor_raw"]
        if row["match_method"] not in Method:
            raise ValueError(f"{raw!r}: unknown match_method {row['match_method']!r}")
        if raw in seen:
            raise ValueError(f"{raw!r} appears twice in the alias table")
        seen.add(raw)
        if row["reviewed_by"] and row["reviewed_on"]:
            ids[raw] = row["sponsor_id"]
    return ids


def _display_name(organization: dict) -> str:
    return next(n["value"] for n in organization["names"] if "ror_display" in n["types"])


def propose(raw: str, items: list[dict]) -> tuple[str, ...]:
    """An unreviewed row for `raw` from ROR affiliation-match `items`."""
    chosen = next((item["organization"] for item in items if item["chosen"]), None)
    if chosen is None:
        return (raw, slug(raw), "", Method.NONE.value, "", "")
    ror_id = chosen["id"].removeprefix("https://ror.org/")
    return (raw, slug(_display_name(chosen)), ror_id, Method.ROR_CHOSEN.value, "", "")


def candidates(trials: Iterable[Trial], as_of: date, threshold: int = THRESHOLD) -> list[str]:
    """Raw lead-sponsor strings with at least `threshold` v1.0 due trials, individuals
    excluded (D8), most due first."""
    due = Counter(
        trial.sponsor_raw
        for trial in trials
        if trial.sponsor_raw and not is_individual(trial) and classify(trial, as_of, V1_0) in DUE
    )
    return [raw for raw, n in due.most_common() if n >= threshold]

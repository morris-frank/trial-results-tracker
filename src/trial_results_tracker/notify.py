"""Report a refresh run to the owner's Telegram bot (docs/plan.md T8).

`message` is pure; `send` is the one network call, Telegram's sendMessage in plain text.
A failed run never claims a release or category counts, only what it fetched.
"""

import json
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import urlopen

from trial_results_tracker.classify import Category
from trial_results_tracker.render import LABELS

RELEASE_PAGE = "https://github.com/morris-frank/trial-results-tracker/releases/tag"


@dataclass(frozen=True)
class Summary:
    tag: str
    data_date: str
    rows: int
    counts: Counter[Category] | None  # None when the snapshot was not classified


def message(
    status: str, run_url: str, method: str, current: Summary | None, previous: Summary | None
) -> str:
    ok = status == "success"
    lines = [f"Refresh {status if ok else status.upper()}"]
    if current:
        rows = f"Data date {current.data_date}: {current.rows:,} rows"
        if previous:
            rows += f" ({current.rows - previous.rows:+,} vs {previous.tag})"
        lines.append(rows)
        if ok:
            lines.append(f"Release: {RELEASE_PAGE}/{current.tag}")
    if ok and current and current.counts is not None:
        before = previous.counts if previous else None
        lines.append(
            f"{method}, versus {previous.tag}:"
            if before is not None
            else f"{method}, no comparison with the previous snapshot:"
        )
        for category, label in LABELS.items():
            line = f"  {label}: {current.counts[category]:,}"
            if before is not None:
                line += f" ({current.counts[category] - before[category]:+,})"
            lines.append(line)
    lines.append(f"Run: {run_url}")
    return "\n".join(lines)


def send(token: str, chat_id: str, text: str) -> None:
    """POST `text` to the chat; Telegram's HTTP errors propagate and fail the step."""
    data = urlencode({"chat_id": chat_id, "text": text}).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with urlopen(url, data=data, timeout=30) as response:  # noqa: S310 (fixed https URL)
        if not json.load(response)["ok"]:
            raise RuntimeError("Telegram rejected the message")

"""Render category counts into the static site: plain HTML and CSS, no scripts (docs/plan.md T5).

Only aggregates reach this module, so no sponsor name can be rendered (naming gate, D7).
"""

import shutil
from collections import Counter
from html import escape
from pathlib import Path
from string import Template

from trial_results_tracker.classify import Category

SITE = Path(__file__).resolve().parents[2] / "site"
TEMPLATES = SITE / "templates"

# Keestra's six categories in reading order; registry observations, never accusations.
LABELS = {
    Category.DUE_NOT_REPORTED: "Due, no results submitted",
    Category.DUE_AND_REPORTED: "Due, results submitted",
    Category.COMPLETED_NOT_DUE: "Completed, not yet due",
    Category.ONGOING: "Ongoing",
    Category.NO_REPORTING_REQUIREMENT: "No reporting requirement (withdrawn or suspended)",
    Category.INCONSISTENT: "Inconsistent or stale record",
}


def render(out: Path, counts: Counter[Category], method: str, context: dict[str, str]) -> None:
    """Write index.html and methodology.html; `context` fills the templates' other fields."""
    unlabelled = set(counts) - set(LABELS)
    if unlabelled:
        raise ValueError(f"no label for categories {sorted(unlabelled)}")
    total = counts.total()
    rows = "\n".join(
        f'        <tr><td>{label}</td><td class="n">{counts[category]:,}</td>'
        f'<td class="n">{counts[category] / total:.1%}</td></tr>'
        for category, label in LABELS.items()
    )
    fields = {key: escape(value) for key, value in {**context, "method": method}.items()}
    fields |= {"total": f"{total:,}", "rows": rows}
    out.mkdir(parents=True, exist_ok=True)
    for asset in ("favicon.png", "style.css"):
        shutil.copy(SITE / asset, out / asset)
    layout = Template((TEMPLATES / "layout.html").read_text())
    for page, title in (("index", "Overview"), ("methodology", "Methodology")):
        main = Template((TEMPLATES / f"{page}.html").read_text()).substitute(fields)
        (out / f"{page}.html").write_text(
            layout.substitute(fields, title=title, main=main.rstrip("\n"))
        )

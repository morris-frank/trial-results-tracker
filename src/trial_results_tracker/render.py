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

# Registry observations, never accusations, in reading order. Keestra's unsplit "reported"
# shows only in the crosswalk.
LABELS = {
    Category.DUE_NOT_REPORTED: "Due, no results submitted",
    Category.DUE_AND_REPORTED: "Due, results submitted",
    Category.DUE_REPORTED_IN_TIME: "Due, results submitted in time",
    Category.DUE_REPORTED_LATE: "Due, results submitted late",
    Category.DUE_RETURNED_IN_QC: "Due, submitted but returned in quality control",
    Category.COMPLETED_NOT_DUE: "Completed, not yet due",
    Category.ONGOING: "Ongoing",
    Category.STATUS_OVERDUE: "Status overdue (still open long after primary completion)",
    Category.NO_REPORTING_REQUIREMENT: "No reporting requirement",
    Category.INCONSISTENT: "Inconsistent record",
}


def _number(value: str, method: str) -> str:
    """A table cell whose number names the rule set it was counted under (AGENTS.md rule 1)."""
    return f'<td class="n">{value} <span class="method">{escape(method)}</span></td>'


def render(
    out: Path,
    counts: Counter[Category],
    cross: Counter[tuple[Category, Category]],
    method: str,
    comparison: str,
    context: dict[str, str],
) -> None:
    """Write index.html and methodology.html. `counts` are under `method`; `cross` is keyed by
    (`comparison` category, `method` category); `context` fills the templates' other fields."""
    unlabelled = (set(counts) | {c for pair in cross for c in pair}) - set(LABELS)
    if unlabelled:
        raise ValueError(f"no label for categories {sorted(unlabelled)}")
    total = counts.total()
    rows = "\n".join(
        f"        <tr><td>{label}</td>{_number(f'{counts[category]:,}', method)}"
        f"{_number(f'{counts[category] / total:.1%}', method)}</tr>"
        for category, label in LABELS.items()
        if category is not Category.DUE_AND_REPORTED
    )
    order = list(LABELS)
    pair_method = f"{comparison} → {method}"
    crosswalk_rows = "\n".join(
        f"        <tr><td>{LABELS[old]}</td><td>{LABELS[new]}</td>"
        f"{_number(f'{n:,}', pair_method)}</tr>"
        for (old, new), n in sorted(cross.items(), key=lambda item: [*map(order.index, item[0])])
    )
    named = {**context, "method": method, "comparison": comparison}
    fields = {key: escape(value) for key, value in named.items()}
    fields |= {
        "total": f"{total:,}",
        "rows": rows,
        "total_cell": _number(f"{total:,}", method),
        "share_cell": _number("100.0%", method),
        "crosswalk_rows": crosswalk_rows,
        "crosswalk_total": _number(f"{cross.total():,}", pair_method),
    }
    out.mkdir(parents=True, exist_ok=True)
    for asset in ("favicon.png", "style.css"):
        shutil.copy(SITE / asset, out / asset)
    layout = Template((TEMPLATES / "layout.html").read_text())
    for page, title in (("index", "Overview"), ("methodology", "Methodology")):
        main = Template((TEMPLATES / f"{page}.html").read_text()).substitute(fields)
        (out / f"{page}.html").write_text(
            layout.substitute(fields, title=title, main=main.rstrip("\n"))
        )

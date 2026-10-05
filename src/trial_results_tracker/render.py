"""Render category counts into the static site: plain HTML and CSS, no scripts (docs/plan.md T5).

Sponsor names arrive only as `Ranked` rows (T12), which the build passes in only with
NAME_SPONSORS on (naming gate, D7); otherwise only aggregates reach this module.
"""

import shutil
from collections import Counter
from collections.abc import Sequence
from html import escape
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from trial_results_tracker.classify import Category
from trial_results_tracker.legal_us import LegalDuty
from trial_results_tracker.publications import EVIDENCE_BASIS as PUBLICATION_BASIS
from trial_results_tracker.publications import Links
from trial_results_tracker.stats import wilson

if TYPE_CHECKING:
    from trial_results_tracker.sponsors import Ranked

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

# docs/methodology.md "Categories": returned in QC is due but not unreported; status-overdue
# and inconsistent trials enter only the upper bound (D5).
DUE = (
    Category.DUE_NOT_REPORTED,
    Category.DUE_REPORTED_IN_TIME,
    Category.DUE_REPORTED_LATE,
    Category.DUE_RETURNED_IN_QC,
)
STALE = (Category.STATUS_OVERDUE, Category.INCONSISTENT)

REGISTRY = "https://clinicaltrials.gov/study/"


def _number(value: str, method: str) -> str:
    """A table cell whose number names the rule set it was counted under (AGENTS.md rule 1)."""
    return f'<td class="n">{value} <span class="method">{escape(method)}</span></td>'


def headline(counts: Counter[Category], method: str, data_date: str) -> str:
    """The overview's headline block: due-not-reported over due with a Wilson 95% CI, and
    the D5 upper bound. `counts` must come from the rule set named by `method`."""
    method, data_date = escape(method), escape(data_date)
    unreported, due = counts[Category.DUE_NOT_REPORTED], sum(counts[c] for c in DUE)
    overdue, inconsistent = counts[Category.STATUS_OVERDUE], counts[Category.INCONSISTENT]
    stale = overdue + inconsistent
    if due == 0:
        figure = f"    <p>No trials are due under method {method} as of {data_date}.</p>"
    else:
        low, high = wilson(unreported, due)
        figure = (
            f'    <p class="headline"><span class="n">{unreported / due:.1%}</span> of '
            f'<span class="n">{due:,}</span> due trials (95% CI <span class="n">{low:.1%}</span> '
            f'to <span class="n">{high:.1%}</span>) have no summary results on ClinicalTrials.gov '
            f"within 12 months of primary completion, as of {data_date}. Method {method}.</p>"
        )
    if due + stale == 0:
        bound = ""
    else:
        share = (unreported + stale) / (due + stale)
        bound = (
            f'\n    <p>Upper bound: <span class="n">{share:.1%}</span> of '
            f'<span class="n">{due + stale:,}</span> trials if the '
            f'<span class="n">{overdue:,}</span> status-overdue and '
            f'<span class="n">{inconsistent:,}</span> inconsistent records, whose registry '
            "status is stale or unreadable, are also counted as unreported.</p>"
        )
    return figure + bound


def legal(counts: Counter[LegalDuty], flagged: int) -> str:
    """The US legal-duty table, a separate axis from the WHO categories (AGENTS.md rule 2)."""
    method = "v1.0, FDAAA probable ACT"  # the legal axis is part of methodology v1.0
    rows = "\n".join(
        f"        <tr><td>{escape(duty)}</td>{_number(f'{counts[duty]:,}', method)}</tr>"
        for duty in LegalDuty
    )
    return (
        "    <table>\n"
        '      <thead><tr><th>Legal duty, United States</th><th class="n">Trials</th>'
        "</tr></thead>\n"
        f"      <tbody>\n{rows}\n      </tbody>\n    </table>\n"
        f'    <p><span class="n">{flagged:,}</span> trials carry ClinicalTrials.gov\'s '
        '"fdaaa801Violation" flag, set on information from FDA; it is quoted in the downloads '
        "and is not our finding.</p>"
    )


def publication_share(links: Links, unreported: set[str], data_date: str) -> str:
    """T14's secondary measure, kept apart from the registry figures it never changes:
    due-not-reported trials (`unreported`) with a possible publication in `links`."""
    searched, found = links.searched & unreported, links.found & unreported
    basis, query_date = escape(PUBLICATION_BASIS), escape(links.query_date)
    if searched:
        low, high = wilson(len(found), len(searched))
        figure = (
            f'<span class="n">{len(found):,}</span> of <span class="n">{len(searched):,}</span> due'
            f' trials with no results submitted (<span class="n">{len(found) / len(searched):.1%}'
            f'</span>, 95% CI <span class="n">{low:.1%}</span> to'
            f' <span class="n">{high:.1%}</span>) have a possible publication found'
        )
    else:
        figure = (
            "No due trial with no results submitted was searched, so no possible publication found"
        )
    missed = len(unreported - searched)
    gap = f" {missed:,} due trials with no results submitted were not searched." if missed else ""
    return (
        "    <h2>Possible publications</h2>\n"
        f"    <p>Evidence basis: <strong>{basis}</strong>. {figure}: a Europe PMC record, which"
        " includes PubMed, whose title or abstract names the trial's NCT ID, searched on"
        f" {query_date} for registry data of {escape(data_date)}.{gap} A possible publication is"
        " a candidate match, not checked to hold the trial's results, and it changes neither the"
        " headline nor any registry count above: the WHO standard is results on the registry."
        ' Every link, with its method and query date: <a href="publications.csv.gz">'
        "publications.csv.gz</a>.</p>\n"
    )


def league(ranked: Sequence["Ranked"], method: str, data_date: str, threshold: int) -> str:
    """The T12 league table of reviewed lead sponsors, each linked to its page."""
    method, data_date = escape(method), escape(data_date)
    rows = "\n".join(
        f"        <tr>{_number(f'{r.rank}=' if r.tied else str(r.rank), method)}"
        f'<td><a href="sponsor-{escape(r.sponsor_id)}.html">{escape(r.name)}</a></td>'
        f"{_number(f'{r.due:,}', method)}"
        f"{_number(f'{len(r.unreported) / r.due:.1%}', method)}"
        f"{_number(f'{r.low:.1%} to {r.high:.1%}', method)}</tr>"
        for r in ranked
    )
    return (
        f'    <h2 id="league">Lead sponsors with at least {threshold} due trials</h2>\n'
        f"    <p>Reviewed lead sponsors with at least {threshold} due trials under method {method},"
        " ranked by the share of their due trials with no summary results on ClinicalTrials.gov"
        f" as of {data_date}, highest first, with its Wilson 95% CI. Read the interval, not only"
        ' the rank. Equal shares share a rank, marked "=", and are listed alphabetically.'
        " Evidence basis: <strong>registry only</strong>. A lead-sponsor string counts only"
        " through a reviewed row of the alias table; aliases are pooled, but no organisation"
        " rolls up another, and individual sponsors are never ranked. This is the WHO standard,"
        " not a legal finding: for legal compliance see the"
        ' <a href="https://fdaaa.trialstracker.net/">FDAAA TrialsTracker</a> and the'
        ' <a href="https://eu.trialstracker.net/">EU TrialsTracker</a>.</p>\n'
        "    <table>\n"
        '      <thead><tr><th class="n">Rank</th><th>Lead sponsor</th><th class="n">Due trials'
        '</th><th class="n">No results submitted</th><th class="n">95% CI</th></tr></thead>\n'
        f"      <tbody>\n{rows}\n      </tbody>\n    </table>\n"
    )


def _trial(nct_id: str, disputes: dict[str, dict[str, str]], label: str = "") -> str:
    """A registry-linked list item, with its dispute note if one is open; a dispute never
    removes the trial."""
    item = f'<a href="{REGISTRY}{escape(nct_id)}">{escape(nct_id)}</a>{label}'
    if dispute := disputes.get(nct_id):
        item += (
            f' <span class="dispute">Disputed on {escape(dispute["opened_on"])}:'
            f' {escape(dispute["note"])} (<a href="{escape(dispute["issue"])}">correction'
            " request</a>). The trial stays listed as the registry shows it while the dispute is"
            " open.</span>"
        )
    return f"        <li>{item}</li>"


def _sponsor_fields(
    r: "Ranked", ranked: int, disputes: dict[str, dict[str, str]], method: str, data_date: str
) -> dict[str, str]:
    method, data_date = escape(method), escape(data_date)
    share = len(r.unreported) / r.due
    summary = (
        f'    <p class="headline"><span class="n">{len(r.unreported):,}</span> of'
        f' <span class="n">{r.due:,}</span> due trials (<span class="n">{share:.1%}</span>, 95% CI'
        f' <span class="n">{r.low:.1%}</span> to <span class="n">{r.high:.1%}</span>) have no'
        " summary results on ClinicalTrials.gov within 12 months of primary completion, as of"
        f' {data_date}. Method {method}; rank <span class="n">{r.rank}{"=" if r.tied else ""}'
        f'</span> of <span class="n">{ranked:,}</span> on the'
        ' <a href="index.html#league">league table</a>.</p>'
    )
    none = "        <li>None.</li>"
    return {
        "name": escape(r.name),
        "summary": summary,
        "aliases": ", ".join(escape(raw) for raw in r.aliases),
        "unreported": "\n".join(_trial(n, disputes) for n in r.unreported) or none,
        "check": "\n".join(_trial(n, disputes, f": {LABELS[c]}") for n, c in r.check) or none,
    }


def render(
    out: Path,
    counts: Counter[Category],
    cross: Counter[tuple[Category, Category]],
    method: str,
    comparison: str,
    context: dict[str, str],
    headline_html: str = "",
    legal_html: str = "",
    publications_html: str = "",
    league_html: str = "",
    ranked: Sequence["Ranked"] = (),
    disputes: dict[str, dict[str, str]] | None = None,
) -> None:
    """Write index.html, methodology.html and one sponsor-<id>.html per `ranked` row. `counts`
    are under `method`; `cross` is keyed by (`comparison` category, `method` category);
    `context` fills the templates' other fields; `disputes` holds open disputes by NCT ID."""
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
        "headline": headline_html,
        "legal": legal_html,
        "publications": publications_html,
        "league": league_html,
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
    sponsor = Template((TEMPLATES / "sponsor.html").read_text())
    for r in ranked:
        page = _sponsor_fields(r, len(ranked), disputes or {}, method, context["data_date"])
        main = sponsor.substitute(fields, **page)
        (out / f"sponsor-{r.sponsor_id}.html").write_text(
            layout.substitute(fields, title=page["name"], main=main.rstrip("\n"))
        )

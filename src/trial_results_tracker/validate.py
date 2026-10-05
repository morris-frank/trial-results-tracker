"""Draw and score a manual validation sample of the classifier (docs/plan.md T11, D14).

`draw` takes a seeded random sample stratified by category; coders then classify each
sampled trial by hand from its registry page, blind to the code's category, and `score`
measures their agreement with the code (Wilson 95% CIs) and with each other (Cohen's kappa).
The strata are sampled equally, not in proportion, so per-category agreement is reported
and no pooled accuracy is: a pooled figure would need weighting back to the population.
"""

import csv
import hashlib
import math
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from trial_results_tracker.classify import Category

SIZE = 200  # D14: 200 trials, two coders
COLUMNS = ["nct_id", "url", "category", "note"]


def registry_url(nct_id: str) -> str:
    return f"https://clinicaltrials.gov/study/{nct_id}"


def default_seed(method: str, tag: str) -> int:
    """A seed fixed by the method and snapshot, so nobody chooses it after seeing a draw."""
    return int.from_bytes(hashlib.sha256(f"{method} {tag}".encode()).digest()[:4])


def allocate(sizes: Mapping[Category, int], total: int) -> dict[Category, int]:
    """Equal allocation: one trial per category in turn, skipping categories that run out."""
    alloc = dict.fromkeys(sizes, 0)
    while total > 0 and any(alloc[c] < sizes[c] for c in sizes):
        for category in Category:
            if total > 0 and category in sizes and alloc[category] < sizes[category]:
                alloc[category] += 1
                total -= 1
    return alloc


def draw(categories: Mapping[str, Category], size: int, seed: int) -> list[tuple[str, Category]]:
    """A stratified sample of (nct_id, category), in category then NCT order."""
    strata: dict[Category, list[str]] = {}
    for nct_id, category in sorted(categories.items()):
        strata.setdefault(category, []).append(nct_id)
    alloc = allocate({c: len(ids) for c, ids in strata.items()}, size)
    rng = random.Random(seed)  # noqa: S311 - a reproducible draw, not a secret
    return [
        (nct_id, category)
        for category in Category
        if category in strata
        for nct_id in sorted(rng.sample(strata[category], alloc[category]))
    ]


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z / (1 + z * z / n) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    count_a, count_b = Counter(a), Counter(b)
    expected = sum(count_a[c] * count_b[c] for c in count_a) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


@dataclass(frozen=True)
class Score:
    n: int
    per_category: dict[Category, tuple[int, int, int]]  # n, coder A agrees, coder B agrees
    coder_agreement: int  # trials where the two coders chose the same category
    kappa: float


def score(
    key: Mapping[str, Category], coder_a: Mapping[str, Category], coder_b: Mapping[str, Category]
) -> Score:
    for name, coding in (("coder A", coder_a), ("coder B", coder_b)):
        if set(coding) != set(key):
            raise ValueError(f"{name} differs from the sample: {sorted(set(key) ^ set(coding))}")
    per_category: dict[Category, tuple[int, int, int]] = {}
    for category in Category:
        ids = [nct for nct, c in key.items() if c is category]
        if ids:
            per_category[category] = (
                len(ids),
                sum(coder_a[i] is category for i in ids),
                sum(coder_b[i] is category for i in ids),
            )
    ids = sorted(key)
    return Score(
        n=len(ids),
        per_category=per_category,
        coder_agreement=sum(coder_a[i] is coder_b[i] for i in ids),
        kappa=cohen_kappa([coder_a[i] for i in ids], [coder_b[i] for i in ids]),
    )


def write_sample(stem: Path, sample: list[tuple[str, Category]], seed: int) -> None:
    """`<stem>-sample.csv` is the key; `<stem>-coding.csv` is the blank, shuffled coding sheet."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    with Path(f"{stem}-sample.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(COLUMNS[:3])
        writer.writerows((nct, registry_url(nct), category) for nct, category in sample)
    shuffled = [nct for nct, _ in sample]
    random.Random(seed).shuffle(shuffled)  # noqa: S311
    with Path(f"{stem}-coding.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows((nct, registry_url(nct), "", "") for nct in shuffled)


def read_coding(path: Path) -> dict[str, Category]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    known = {c.value for c in Category}
    unknown = sorted({r["category"] for r in rows} - known)
    if unknown:
        raise ValueError(f"{path}: unknown categories {unknown}")
    return {r["nct_id"]: Category(r["category"]) for r in rows}


RESULTS = "## Results\n"


def report(meta: Mapping[str, str], key: Mapping[str, Category]) -> str:
    """The Markdown page for docs/validation/<method>-<snapshot>.md, results pending."""
    strata = Counter(key.values())
    lines = [
        f"# Validation: {meta['method']} on {meta['tag']}",
        "",
        f"Method {meta['method']}, snapshot [{meta['tag']}]({meta['release_url']}) "
        f"(data timestamp {meta['data_date']}), sample drawn by code `{meta['code_sha'][:12]}` "
        f"with seed {meta['seed']}. Evidence basis: registry only.",
        "",
        "## Sample",
        "",
        f"{len(key)} trials, a random sample stratified by v1.0 category with equal allocation "
        "(a category with fewer trials than its share is taken whole); D14 in `docs/plan.md`. "
        f"Reproduce with `python -m trial_results_tracker validate sample --seed {meta['seed']}` "
        f"against `SNAPSHOT` = `{meta['tag']}`.",
        "",
        "| Category | Sampled |",
        "|---|---:|",
        *(f"| `{c}` | {strata[c]} |" for c in Category if c in strata),
        "",
        "## Coding protocol",
        "",
        "Two coders each copy the coding sheet (`-coding.csv`) and, working independently and "
        "without seeing the key (`-sample.csv`), enter the v1.0 category (`docs/methodology.md`) "
        f"each trial should have as of {meta['data_date']}. The link is the live registry page, "
        "which may have changed since; code from its record history as of that date. Allowed "
        "values: " + ", ".join(f"`{c}`" for c in Category if c is not Category.DUE_AND_REPORTED),
        "",
        RESULTS,
        "Not scored: coding pending. The coding round is the owner's to run.",
    ]
    return "\n".join(lines) + "\n"


def scored(page: str, result: Score) -> str:
    """`page` from `report` with its Results section replaced by `result`."""
    lines = [
        page.split(RESULTS)[0] + RESULTS,
        "Agreement of each coder with the code's category, with Wilson 95% CIs. Strata are "
        "sampled equally, so these are per-category figures, not a pooled accuracy.",
        "",
        "| Category | n | Coder A agrees | 95% CI | Coder B agrees | 95% CI |",
        "|---|---:|---:|---|---:|---|",
    ]
    for category, (n, a, b) in result.per_category.items():
        (a_lo, a_hi), (b_lo, b_hi) = wilson(a, n), wilson(b, n)
        lines.append(
            f"| `{category}` | {n} | {a} | {a_lo:.0%}–{a_hi:.0%} | {b} | {b_lo:.0%}–{b_hi:.0%} |"
        )
    lo, hi = wilson(result.coder_agreement, result.n)
    lines += [
        "",
        f"Inter-coder agreement: {result.coder_agreement} of {result.n} "
        f"({lo:.0%}–{hi:.0%}, Wilson 95%), Cohen's kappa {result.kappa:.2f}.",
    ]
    return "\n".join(lines) + "\n"

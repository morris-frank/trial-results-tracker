"""Write the per-trial and per-sponsor downloads with their manifest (docs/plan.md T9).

Individual sponsors are pooled into one unnamed bucket (D8). A named download counts as
naming, so with `name_sponsors` off (the default until D7's gate) no sponsor name is
written at all: `sponsor_raw` is empty and sponsors.csv counts per sponsor class.
"""

import csv
import gzip
import json
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from trial_results_tracker.classify import KEESTRA_2021, V1_0, Category, classify
from trial_results_tracker.model import RegistryDate, ResponsiblePartyType, SponsorClass, Trial

INDIVIDUALS = "Individual sponsors (pooled)"
EVIDENCE_BASIS = "registry only"
LEGAL_DUTY = "not determined"  # D15 (a); never derived from the WHO category
LICENCE = "CC BY 4.0"  # D12, CT.gov-derived data only
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"

V1_CATEGORIES = [c for c in Category if c is not Category.DUE_AND_REPORTED]  # Keestra only

TRIAL_COLUMNS = (
    "nct_id",
    "sponsor_raw",
    "sponsor_id",
    "sponsor_class",
    "category_keestra_2021",
    "category_v1_0",
    "primary_completion",
    "primary_completion_type",
    "results_first_submitted",
    "results_first_posted",
    "stale_status",
    "evidence_basis",
    "data_date",
    "legal_duty",
)


def is_individual(trial: Trial) -> bool:
    """INDIV, or a sponsor-investigator: the registry's own mark that the investigator is
    the lead sponsor. Investigator names are never fetched (T1), so the type stands in for
    comparing names (critique.md gap 8); it pools some institutions too, erring private."""
    return (
        trial.sponsor_class is SponsorClass.INDIV
        or trial.responsible_party is ResponsiblePartyType.SPONSOR_INVESTIGATOR
    )


def _text(value) -> str:
    if value is None:
        return ""
    return getattr(value, "raw", value)  # an Unrecognised enum keeps the registry's string


def _date(registry_date: RegistryDate | None) -> str:
    return registry_date.value.isoformat() if registry_date else ""


def export(
    out: Path,
    trials: Iterable[Trial],
    as_of: date,
    meta: dict[str, str],
    name_sponsors: bool,
    sponsor_ids: dict[str, str] | None = None,
) -> None:
    """Write trials.csv.gz, sponsors.csv and manifest.json into `out`.

    `meta` holds `dataTimestamp`, `codeSha` and `snapshot` (the release tag);
    `sponsor_ids` maps raw strings to reviewed alias-table IDs (sponsors.lookup)."""
    data_date = meta["dataTimestamp"][:10]
    sponsors: dict[str, Counter[Category]] = {}
    out.mkdir(parents=True, exist_ok=True)
    with gzip.open(out / "trials.csv.gz", "wt", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(TRIAL_COLUMNS)
        for trial in trials:
            v1 = classify(trial, as_of, V1_0)
            if is_individual(trial):
                sponsor = INDIVIDUALS
            elif name_sponsors:
                sponsor = trial.sponsor_raw or ""
            else:
                sponsor = _text(trial.sponsor_class) or "UNKNOWN"
            sponsors.setdefault(sponsor, Counter())[v1] += 1
            pcd = trial.primary_completion
            writer.writerow(
                (
                    trial.nct_id,
                    sponsor if name_sponsors else "",
                    (sponsor_ids or {}).get(sponsor, "") if name_sponsors else "",
                    _text(trial.sponsor_class),
                    classify(trial, as_of, KEESTRA_2021),
                    v1,
                    _date(pcd),
                    _text(pcd and pcd.type),
                    _date(trial.results_first_submitted),
                    _date(trial.results_first_posted),
                    v1 is Category.STATUS_OVERDUE,  # D5: open status, PCD over 395 days ago
                    EVIDENCE_BASIS,
                    data_date,
                    LEGAL_DUTY,
                )
            )
    with (out / "sponsors.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            (
                "sponsor",
                "trials",
                *(f"v1_0_{c}" for c in V1_CATEGORIES),
                "evidence_basis",
                "data_date",
            )
        )
        for sponsor, counts in sorted(sponsors.items()):
            writer.writerow(
                (
                    sponsor,
                    counts.total(),
                    *(counts[c] for c in V1_CATEGORIES),
                    EVIDENCE_BASIS,
                    data_date,
                )
            )
    manifest = {
        "methods": [KEESTRA_2021.name, V1_0.name],
        "dataTimestamp": meta["dataTimestamp"],
        "dataDate": data_date,
        "snapshot": meta["snapshot"],
        "codeSha": meta["codeSha"],
        "licence": LICENCE,
        "licenceUrl": LICENCE_URL,
        "attribution": "Derived from ClinicalTrials.gov (US National Library of Medicine)",
        "evidenceBasis": EVIDENCE_BASIS,
        "legalDuty": LEGAL_DUTY,
        "sponsorNames": name_sponsors,
        "files": ["trials.csv.gz", "sponsors.csv"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

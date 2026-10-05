"""Link due-not-reported trials to candidate publications (docs/plan.md T14, D13 (c)).

A trial is linked to a Europe PMC record, which covers PubMed, only when the record's
title or abstract contains its exact NCT ID. That is a candidate, never verified results,
so it is shown as "possible publication found" beside the registry figures and never
changes them. Every row carries its method, query date and evidence basis.
"""

import csv
import gzip
import json
import re
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from trial_results_tracker import snapshot
from trial_results_tracker.classify import V1_0, Category, classify
from trial_results_tracker.fetch import Get, get_json
from trial_results_tracker.parse import parse

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FILE = "publications.csv.gz"
METHOD = "exact NCT-ID mention in Europe PMC title or abstract (includes PubMed)"
EVIDENCE_BASIS = "registry plus NCT-ID publication search"
BATCH = 50  # NCT IDs per query, OR-ed
PAUSE = 0.5  # seconds between requests
COLUMNS = (
    "nct_id",
    "source",
    "id",
    "pmid",
    "doi",
    "title",
    "first_publication_date",
    "method",
    "query_date",
    "evidence_basis",
)
_NCT = re.compile(r"(?<![A-Z0-9])NCT\d{8}(?!\d)")


def mentions(record: dict, nct_ids: set[str]) -> set[str]:
    """The requested NCT IDs written out whole in the record's title or abstract."""
    text = f"{record.get('title', '')} {record.get('abstractText', '')}".upper()
    return set(_NCT.findall(text)) & nct_ids


def _search(
    nct_ids: list[str], get: Get, sleep: Callable[[float], None]
) -> Iterator[tuple[str, dict]]:
    query = " OR ".join(f'TITLE_ABS:"{nct_id}"' for nct_id in nct_ids)
    cursor = "*"
    while True:
        params = {"query": query, "format": "json", "resultType": "core", "pageSize": 1000}
        page = get(f"{API}?{urlencode({**params, 'cursorMark': cursor})}")
        records = page["resultList"]["result"]
        for record in records:
            for nct_id in sorted(mentions(record, set(nct_ids))):
                yield nct_id, record
        sleep(PAUSE)
        if not records or page.get("nextCursorMark") in (None, cursor):
            return
        cursor = page["nextCursorMark"]


def link(
    out: Path,
    nct_ids: Iterable[str],
    get: Get = get_json,
    sleep: Callable[[float], None] = time.sleep,
    today: date | None = None,
) -> Path:
    """Search every NCT ID and write publications.csv.gz: a row per link, and an empty-link
    row for a searched trial with none, so "searched, none found" differs from unsearched."""
    query_date = (today or date.today()).isoformat()
    ids = list(nct_ids)
    path = out / FILE
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for start in range(0, len(ids), BATCH):
            batch = ids[start : start + BATCH]
            found = set()
            for nct_id, record in _search(batch, get, sleep):
                found.add(nct_id)
                writer.writerow(
                    (
                        nct_id,
                        record.get("source", ""),
                        record.get("id", ""),
                        record.get("pmid", ""),
                        record.get("doi", ""),
                        record.get("title", ""),
                        record.get("firstPublicationDate", ""),
                        METHOD,
                        query_date,
                        EVIDENCE_BASIS,
                    )
                )
            for nct_id in batch:
                if nct_id not in found:
                    writer.writerow((nct_id, *[""] * 6, METHOD, query_date, EVIDENCE_BASIS))
    return path


def link_snapshot(directory: Path, today: date | None = None) -> Path:
    """Search the snapshot's v1.0 due-not-reported trials and name the file in its manifest,
    so the snapshot task releases it and the build downloads it."""
    manifest = snapshot.manifest(directory)
    as_of = date.fromisoformat(manifest["dataTimestamp"][:10])
    ids = [
        trial.nct_id
        for trial in map(parse, snapshot.records(directory))
        if classify(trial, as_of, V1_0) is Category.DUE_NOT_REPORTED
    ]
    path = link(directory, ids, today=today)
    manifest["publications"] = FILE
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return path


@dataclass(frozen=True)
class Links:
    searched: set[str]
    found: set[str]
    query_date: str


def read(path: Path) -> Links:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return Links(
        searched={row["nct_id"] for row in rows},
        found={row["nct_id"] for row in rows if row["id"]},
        query_date=max((row["query_date"] for row in rows), default=""),
    )

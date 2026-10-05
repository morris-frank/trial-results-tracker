"""Pull a dated snapshot of interventional studies from the ClinicalTrials.gov API v2.

Only the classification fields of docs/research/data-sources.md section 1 are requested;
no person-level field (investigator, official, contact, point of contact) is ever fetched
(docs/research/legal.md section 2). A pull whose row count differs from the API's
`totalCount` raises and leaves no manifest, so a partial snapshot cannot be published.
"""

import gzip
import json
import subprocess
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

API = "https://clinicaltrials.gov/api/v2"
QUERY = {
    "format": "json",
    "filter.advanced": "AREA[StudyType]INTERVENTIONAL",
    "pageSize": 1000,
}

_STATUS = "protocolSection.statusModule."
_SPONSORS = "protocolSection.sponsorCollaboratorsModule."
_OVERSIGHT = "protocolSection.oversightModule."
FIELDS = (
    "protocolSection.identificationModule.nctId",
    "protocolSection.designModule.studyType",
    "protocolSection.designModule.enrollmentInfo",
    _STATUS + "overallStatus",
    _STATUS + "statusVerifiedDate",
    _STATUS + "whyStopped",
    _STATUS + "startDateStruct",
    _STATUS + "primaryCompletionDateStruct",
    _STATUS + "completionDateStruct",
    _STATUS + "resultsFirstSubmitDate",
    _STATUS + "resultsFirstSubmitQcDate",
    _STATUS + "resultsFirstPostDateStruct",
    _STATUS + "dispFirstSubmitDate",
    _STATUS + "lastUpdatePostDateStruct",
    _SPONSORS + "leadSponsor",
    _SPONSORS + "responsibleParty.type",
    _SPONSORS + "collaborators",
    _OVERSIGHT + "isFdaRegulatedDrug",
    _OVERSIGHT + "isFdaRegulatedDevice",
    _OVERSIGHT + "fdaaa801Violation",
    "annotationSection.annotationModule.unpostedAnnotation.unpostedEvents",
    "hasResults",
)

PAUSE = 2.0  # seconds between pages; the ~50 req/min limit is unverified
RETRIES = 5

Get = Callable[[str], dict]


class ShortPull(RuntimeError):
    """The rows written differ from the API's totalCount."""


def get_json(url: str, sleep: Callable[[float], None] = time.sleep) -> dict:
    """GET a JSON document, retrying 429, 5xx and network errors with exponential backoff."""
    for attempt in range(RETRIES + 1):
        try:
            with urlopen(url, timeout=120) as response:  # noqa: S310 (fixed https URL)
                return json.load(response)
        except HTTPError as error:
            if error.code != 429 and error.code < 500 or attempt == RETRIES:
                raise
        except URLError:
            if attempt == RETRIES:
                raise
        sleep(PAUSE * 2**attempt)
    raise AssertionError("unreachable")


def code_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).parent,
    )
    return result.stdout.strip()


def fetch(
    out: Path,
    get: Get = get_json,
    sleep: Callable[[float], None] = time.sleep,
    today: date | None = None,
) -> Path:
    """Write ctgov-<date>.jsonl.gz and manifest.json into `out`; return the manifest path."""
    out.mkdir(parents=True, exist_ok=True)
    version = get(f"{API}/version")
    snapshot = out / f"ctgov-{(today or date.today()).isoformat()}.jsonl.gz"
    manifest = out / "manifest.json"
    manifest.unlink(missing_ok=True)
    query = {**QUERY, "fields": ",".join(FIELDS)}
    total = None
    rows = 0
    token = None
    with gzip.open(snapshot, "wt", encoding="utf-8") as lines:
        while True:
            params = (
                {**query, "countTotal": "true"} if token is None else {**query, "pageToken": token}
            )
            page = get(f"{API}/studies?{urlencode(params)}")
            if total is None:
                total = page["totalCount"]
            for study in page.get("studies", []):
                lines.write(json.dumps(study, separators=(",", ":")) + "\n")
                rows += 1
            token = page.get("nextPageToken")
            if not token:
                break
            sleep(PAUSE)
    if rows != total:
        snapshot.unlink()
        raise ShortPull(f"wrote {rows} rows but the API reported totalCount {total}")
    manifest.write_text(
        json.dumps(
            {
                "apiVersion": version["apiVersion"],
                "dataTimestamp": version["dataTimestamp"],
                "totalCount": total,
                "rowsWritten": rows,
                "file": snapshot.name,
                "query": QUERY,
                "fields": list(FIELDS),
                "codeSha": code_sha(),
            },
            indent=2,
        )
        + "\n"
    )
    return manifest

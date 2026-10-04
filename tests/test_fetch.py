import gzip
import io
import json
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from trial_results_tracker import fetch as fetch_module
from trial_results_tracker.fetch import FIELDS, ShortPull, fetch, get_json

# Recorded 2026-10-05: three interventional studies by NCT ID at pageSize=2, so two pages.
# The opaque page token is replaced by "page-2" (gitleaks reads it as an API key).
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "ctgov-two-pages.json").read_text())
TODAY = date(2026, 10, 5)


def fake_api(pages):
    requests = []

    def get(url):
        requests.append(url)
        if url.endswith("/version"):
            return FIXTURE["version"]
        token = parse_qs(urlsplit(url).query).get("pageToken")
        return pages[0] if token is None else pages[1]

    return get, requests


def test_fetch_writes_every_row_and_a_manifest(tmp_path):
    get, requests = fake_api(FIXTURE["pages"])
    manifest = json.loads(fetch(tmp_path, get=get, sleep=lambda _: None, today=TODAY).read_text())

    with gzip.open(tmp_path / "ctgov-2026-10-05.jsonl.gz", "rt") as lines:
        rows = [json.loads(line) for line in lines]
    assert len(rows) == manifest["totalCount"] == manifest["rowsWritten"] == 3
    assert manifest["apiVersion"] == "2.0.5"
    assert manifest["dataTimestamp"] == "2026-10-02T09:00:04"
    assert manifest["fields"] == list(FIELDS)
    assert len(manifest["codeSha"]) == 40

    first, second = (parse_qs(urlsplit(url).query) for url in requests[1:])
    assert first.pop("countTotal") == ["true"]
    assert second.pop("pageToken") == [FIXTURE["pages"][0]["nextPageToken"]]
    assert first == second


def test_short_pull_raises_and_writes_no_manifest(tmp_path):
    first, second = FIXTURE["pages"]
    get, _ = fake_api([first, {**second, "studies": []}])
    with pytest.raises(ShortPull):
        fetch(tmp_path, get=get, sleep=lambda _: None, today=TODAY)
    assert not (tmp_path / "manifest.json").exists()
    assert not (tmp_path / "ctgov-2026-10-05.jsonl.gz").exists()


@pytest.mark.parametrize(
    "person_field",
    ["investigator", "official", "contact", "pointofcontact", "affiliation", "fullname"],
)
def test_no_person_level_field_is_requested(person_field):
    assert not [field for field in FIELDS if person_field in field.lower()]


def test_get_json_retries_429_and_5xx_then_succeeds(monkeypatch):
    responses = [429, 503, b'{"ok": true}']

    def urlopen(url, timeout):
        response = responses.pop(0)
        if isinstance(response, int):
            raise HTTPError(url, response, "busy", {}, None)
        return io.BytesIO(response)

    monkeypatch.setattr(fetch_module, "urlopen", urlopen)
    waits = []
    assert get_json("https://example.test", sleep=waits.append) == {"ok": True}
    assert waits == [2.0, 4.0]


def test_get_json_does_not_retry_a_client_error(monkeypatch):
    def urlopen(url, timeout):
        raise HTTPError(url, 400, "bad request", {}, None)

    monkeypatch.setattr(fetch_module, "urlopen", urlopen)
    with pytest.raises(HTTPError):
        get_json("https://example.test", sleep=lambda _: pytest.fail("retried a 400"))

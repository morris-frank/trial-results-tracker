"""Download a published snapshot release and read it back, row-count checked (docs/plan.md T5).

Releases are public, so no token is needed and Vercel's Git build can run this. Any
download error propagates: the build fails rather than publishing a placeholder.
"""

import gzip
import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from urllib.request import urlopen

RELEASES = "https://github.com/morris-frank/trial-results-tracker/releases/download"


class RowMismatch(RuntimeError):
    """The snapshot file holds a different number of rows than its manifest records."""


def manifest(directory: Path) -> dict:
    return json.loads((directory / "manifest.json").read_text())


def download(tag: str, out: Path, base: str = RELEASES) -> Path:
    """Fetch `manifest.json` and the snapshot and publications files it names from release
    `tag` into `out`."""
    out.mkdir(parents=True, exist_ok=True)

    def get(name: str) -> None:
        # base is the fixed https URL, or a file:// URI in tests.
        url = f"{base}/{tag}/{name}"
        with urlopen(url, timeout=300) as response, (out / name).open("wb") as target:  # noqa: S310
            shutil.copyfileobj(response, target)

    get("manifest.json")
    get(manifest(out)["file"])
    if "publications" in manifest(out):  # T14; older releases have none
        get(manifest(out)["publications"])
    return out


def records(directory: Path) -> Iterator[dict]:
    """Yield every raw record; raise `RowMismatch` at the end if the count is off."""
    expected = manifest(directory)["rowsWritten"]
    rows = 0
    with gzip.open(directory / manifest(directory)["file"], "rt", encoding="utf-8") as lines:
        for line in lines:
            rows += 1
            yield json.loads(line)
    if rows != expected:
        raise RowMismatch(f"snapshot has {rows} rows but its manifest records {expected}")

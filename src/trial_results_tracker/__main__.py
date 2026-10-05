"""Command line entrypoint. `fetch` pulls a dated registry snapshot; `build` writes the site."""

import argparse
import os
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

from trial_results_tracker import snapshot
from trial_results_tracker.classify import KEESTRA_2021, classify
from trial_results_tracker.fetch import code_sha, fetch
from trial_results_tracker.parse import parse
from trial_results_tracker.render import render

SNAPSHOT = Path(__file__).resolve().parents[2] / "SNAPSHOT"


def build(out: Path, snapshot_dir: Path | None = None) -> None:
    """Classify the pinned snapshot (or a local one) and render the site into `out`."""
    with tempfile.TemporaryDirectory() as scratch:
        directory = snapshot_dir or snapshot.download(SNAPSHOT.read_text().strip(), Path(scratch))
        manifest = snapshot.manifest(directory)
        # The release tag the snapshot task gave this file, so a local override is labelled too.
        tag = "data-" + manifest["file"].removeprefix("ctgov-").removesuffix(".jsonl.gz")
        data_date = manifest["dataTimestamp"][:10]
        as_of = date.fromisoformat(data_date)
        counts = Counter(
            classify(parse(record), as_of, KEESTRA_2021) for record in snapshot.records(directory)
        )
    # Vercel's Git build has no .git directory but exposes the commit.
    sha = os.environ.get("VERCEL_GIT_COMMIT_SHA") or code_sha()
    render(
        out,
        counts,
        KEESTRA_2021.name,
        {
            "data_date": data_date,
            "api_version": manifest["apiVersion"],
            "rows_written": f"{manifest['rowsWritten']:,}",
            "fetch_sha_short": manifest["codeSha"][:12],
            "tag": tag,
            "release_url": f"https://github.com/morris-frank/trial-results-tracker/releases/tag/{tag}",
            "code_sha": sha,
            "code_sha_short": sha[:12],
        },
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="trial-results-tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="build the static site")
    build_cmd.add_argument("--out", type=Path, default=Path("dist"))
    build_cmd.add_argument(
        "--snapshot-dir", type=Path, help="use this local snapshot instead of downloading SNAPSHOT"
    )
    fetch_cmd = sub.add_parser("fetch", help="pull a dated ClinicalTrials.gov snapshot")
    fetch_cmd.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)
    if args.command == "build":
        build(args.out, args.snapshot_dir)
    elif args.command == "fetch":
        print(fetch(args.out))


if __name__ == "__main__":
    main()

"""Command line entrypoint: `fetch` a registry snapshot, `build` the site, `notify` Telegram."""

import argparse
import os
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

from trial_results_tracker import notify, snapshot
from trial_results_tracker.classify import KEESTRA_2021, classify
from trial_results_tracker.fetch import code_sha, fetch
from trial_results_tracker.parse import parse
from trial_results_tracker.render import render

SNAPSHOT = Path(__file__).resolve().parents[2] / "SNAPSHOT"


def summarise(directory: Path, categorise: bool = True) -> notify.Summary:
    """Tag, data date, rows and (optionally) Keestra-2021 counts of a snapshot directory."""
    manifest = snapshot.manifest(directory)
    # The release tag the snapshot task gave this file, so a local override is labelled too.
    tag = "data-" + manifest["file"].removeprefix("ctgov-").removesuffix(".jsonl.gz")
    data_date = manifest["dataTimestamp"][:10]
    counts = None
    if categorise:
        as_of = date.fromisoformat(data_date)
        counts = Counter(
            classify(parse(record), as_of, KEESTRA_2021) for record in snapshot.records(directory)
        )
    return notify.Summary(tag, data_date, manifest["rowsWritten"], counts)


def build(out: Path, snapshot_dir: Path | None = None) -> None:
    """Classify the pinned snapshot (or a local one) and render the site into `out`."""
    with tempfile.TemporaryDirectory() as scratch:
        directory = snapshot_dir or snapshot.download(SNAPSHOT.read_text().strip(), Path(scratch))
        manifest = snapshot.manifest(directory)
        summary = summarise(directory)
        tag, data_date, counts = summary.tag, summary.data_date, summary.counts
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


def report(status: str, run_url: str, previous_tag: str, snapshot_dir: Path) -> None:
    """Send the run's Telegram message; deltas only for a successful run with a fresh snapshot."""
    ok = status == "success"
    current = previous = None
    # fetch writes the manifest last, so it exists only after a complete pull.
    if (snapshot_dir / "manifest.json").exists():
        current = summarise(snapshot_dir, categorise=ok)
    if ok and current:
        with tempfile.TemporaryDirectory() as scratch:
            try:
                previous = summarise(snapshot.download(previous_tag, Path(scratch)))
            except OSError as error:  # the report still goes out, saying there is no comparison
                print(f"previous snapshot {previous_tag} unavailable: {error}", file=sys.stderr)
    text = notify.message(status, run_url, KEESTRA_2021.name, current, previous)
    print(text)
    notify.send(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"], text)


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
    notify_cmd = sub.add_parser("notify", help="report a refresh run to Telegram")
    notify_cmd.add_argument("--status", required=True, help="the job status, e.g. success")
    notify_cmd.add_argument("--run-url", default="(local run)")
    notify_cmd.add_argument("--previous", required=True, help="the tag pinned before this run")
    notify_cmd.add_argument("--snapshot-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)
    if args.command == "build":
        build(args.out, args.snapshot_dir)
    elif args.command == "fetch":
        print(fetch(args.out))
    elif args.command == "notify":
        report(args.status, args.run_url, args.previous, args.snapshot_dir)


if __name__ == "__main__":
    main()

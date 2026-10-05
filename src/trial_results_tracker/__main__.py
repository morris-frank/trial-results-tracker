"""Command line entrypoint. `fetch` pulls a dated registry snapshot; `build` writes the site."""

import argparse
import csv
import json
import os
import shutil
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from trial_results_tracker import legal_us, publications, snapshot, sponsors, validate
from trial_results_tracker.classify import KEESTRA_2021, V1_0, Category, classify
from trial_results_tracker.crosswalk import crosswalk
from trial_results_tracker.export import LICENCE, LICENCE_URL, export
from trial_results_tracker.fetch import code_sha, fetch
from trial_results_tracker.parse import parse
from trial_results_tracker.render import headline, legal, publication_share, render

SNAPSHOT = Path(__file__).resolve().parents[2] / "SNAPSHOT"
ALIASES = Path(__file__).resolve().parents[2] / "sponsors" / "aliases.csv"
ROR_AFFILIATION = "https://api.ror.org/v2/organizations?affiliation="
NAMED = "Organisations are named in the downloads; individual sponsors are pooled unnamed."
UNNAMED = (
    "Sponsor names are withheld until the naming gate is passed: sponsors are counted by"
    " sponsor class, with individual sponsors pooled."
)


def build(out: Path, snapshot_dir: Path | None = None, name_sponsors: bool = False) -> None:
    """Classify the pinned snapshot (or a local one) and render the site into `out`."""
    with tempfile.TemporaryDirectory() as scratch:
        directory = snapshot_dir or snapshot.download(SNAPSHOT.read_text().strip(), Path(scratch))
        manifest = snapshot.manifest(directory)
        # The release tag the snapshot task gave this file, so a local override is labelled too.
        tag = "data-" + manifest["file"].removeprefix("ctgov-").removesuffix(".jsonl.gz")
        data_date = manifest["dataTimestamp"][:10]
        as_of = date.fromisoformat(data_date)
        trials = [parse(record) for record in snapshot.records(directory)]
        links = None
        if "publications" in manifest:  # T14; published beside the downloads
            links = publications.read(directory / manifest["publications"])
            out.mkdir(parents=True, exist_ok=True)
            shutil.copy(directory / manifest["publications"], out / publications.FILE)
    counts = Counter(classify(trial, as_of, V1_0) for trial in trials)
    unreported = {t.nct_id for t in trials if classify(t, as_of, V1_0) is Category.DUE_NOT_REPORTED}
    # Vercel's Git build has no .git directory but exposes the commit.
    sha = os.environ.get("VERCEL_GIT_COMMIT_SHA") or code_sha()
    meta = {"dataTimestamp": manifest["dataTimestamp"], "codeSha": sha, "snapshot": tag}
    export(out, trials, as_of, meta, name_sponsors, sponsors.lookup(ALIASES.read_text()), links)
    render(
        out,
        counts,
        crosswalk(trials, as_of),
        V1_0.name,
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
            "licence": LICENCE,
            "licence_url": LICENCE_URL,
            "sponsor_note": NAMED if name_sponsors else UNNAMED,
        },
        headline(counts, V1_0.name, data_date),
        legal(
            Counter(legal_us.status(trial, as_of) for trial in trials),
            sum(bool(trial.fdaaa801_violation) for trial in trials),
        ),
        publication_share(links, unreported, data_date) if links else "",
    )


def validate_sample(out: Path, snapshot_dir: Path | None, seed: int | None, size: int) -> None:
    """Draw the v1.0 validation sample from the pinned snapshot into `out`."""
    with tempfile.TemporaryDirectory() as scratch:
        directory = snapshot_dir or snapshot.download(SNAPSHOT.read_text().strip(), Path(scratch))
        manifest = snapshot.manifest(directory)
        tag = "data-" + manifest["file"].removeprefix("ctgov-").removesuffix(".jsonl.gz")
        data_date = manifest["dataTimestamp"][:10]
        as_of = date.fromisoformat(data_date)
        categories = {}
        for record in snapshot.records(directory):
            trial = parse(record)
            categories[trial.nct_id] = classify(trial, as_of, V1_0)
    seed = validate.default_seed(V1_0.name, tag) if seed is None else seed
    sample = validate.draw(categories, size, seed)
    stem = out / f"{V1_0.name}-{tag}"
    validate.write_sample(stem, sample, seed)
    meta = {
        "method": V1_0.name,
        "tag": tag,
        "release_url": f"https://github.com/morris-frank/trial-results-tracker/releases/tag/{tag}",
        "data_date": data_date,
        "code_sha": code_sha(),
        "seed": str(seed),
    }
    Path(f"{stem}.md").write_text(validate.report(meta, dict(sample)))


def validate_score(sample: Path, coder_a: Path, coder_b: Path) -> None:
    """Score two coders' sheets against the sample key into the sample's report page."""
    key = validate.read_coding(sample)
    result = validate.score(key, validate.read_coding(coder_a), validate.read_coding(coder_b))
    page = Path(str(sample).removesuffix("-sample.csv") + ".md")
    page.write_text(validate.scored(page.read_text(), result))


def sponsors_seed(table: Path, snapshot_dir: Path | None) -> int:
    """Append unreviewed ROR proposals to `table` for every raw string above D6's threshold
    that has no row yet; existing rows, reviewed or not, are kept as they are."""
    with tempfile.TemporaryDirectory() as scratch:
        directory = snapshot_dir or snapshot.download(SNAPSHOT.read_text().strip(), Path(scratch))
        as_of = date.fromisoformat(snapshot.manifest(directory)["dataTimestamp"][:10])
        wanted = sponsors.candidates(map(parse, snapshot.records(directory)), as_of)
    rows = list(csv.reader(table.open(encoding="utf-8")))[1:] if table.exists() else []
    known = {row[0] for row in rows}
    for raw in wanted:
        if raw not in known:
            with urlopen(ROR_AFFILIATION + quote(raw), timeout=60) as response:  # noqa: S310
                rows.append(sponsors.propose(raw, json.load(response)["items"]))
    table.parent.mkdir(parents=True, exist_ok=True)
    with table.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")  # LF, as git stores the table
        writer.writerow(sponsors.COLUMNS)
        writer.writerows(sorted(rows))
    return len(rows) - len(known)


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
    validate_cmd = sub.add_parser("validate", help="draw or score a validation sample")
    validate_sub = validate_cmd.add_subparsers(dest="step", required=True)
    sample_cmd = validate_sub.add_parser("sample", help="draw the v1.0 sample and coding sheet")
    sample_cmd.add_argument("--out", type=Path, default=Path("docs/validation"))
    sample_cmd.add_argument("--snapshot-dir", type=Path)
    sample_cmd.add_argument("--seed", type=int, help="default: derived from method and snapshot")
    sample_cmd.add_argument("--size", type=int, default=validate.SIZE)
    score_cmd = validate_sub.add_parser("score", help="score two coders against the sample")
    score_cmd.add_argument("sample", type=Path, help="the <method>-<snapshot>-sample.csv key")
    score_cmd.add_argument("coder_a", type=Path)
    score_cmd.add_argument("coder_b", type=Path)
    seed_cmd = sub.add_parser("sponsors-seed", help="propose ROR matches into the alias table")
    seed_cmd.add_argument("--table", type=Path, default=ALIASES)
    seed_cmd.add_argument("--snapshot-dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "build":
        # NAME_SPONSORS=1 publishes organisation names in the downloads; off until D7's gate.
        build(args.out, args.snapshot_dir, os.environ.get("NAME_SPONSORS") == "1")
    elif args.command == "fetch":
        print(fetch(args.out))
        print(publications.link_snapshot(args.out))
    elif args.command == "sponsors-seed":
        print(f"{sponsors_seed(args.table, args.snapshot_dir)} unreviewed proposals added")
    elif args.step == "sample":
        validate_sample(args.out, args.snapshot_dir, args.seed, args.size)
    else:
        validate_score(args.sample, args.coder_a, args.coder_b)


if __name__ == "__main__":
    main()

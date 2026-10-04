"""Command line entrypoint. `build` writes the static site; the pipeline lands in later tasks."""

import argparse
import shutil
from pathlib import Path

SITE = Path(__file__).resolve().parents[2] / "site"


def build(out: Path) -> None:
    # Until the pipeline exists the build is the placeholder page, so the deploy
    # path (Vercel runs `mise run build`) is exercised from the first commit.
    shutil.copytree(SITE, out, dirs_exist_ok=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="trial-results-tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="build the static site")
    build_cmd.add_argument("--out", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    if args.command == "build":
        build(args.out)


if __name__ == "__main__":
    main()

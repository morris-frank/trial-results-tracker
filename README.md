<img src="icons/icon.png" align="left" width="160" hspace="16" alt="trial-results-tracker logo">

<h3>trial-results-tracker</h3>

<p>
  <sub>CLINICAL TRIAL TRANSPARENCY · WHO STANDARD, NOT JUST THE LAW</sub>
  <br>
  <strong>Shows which sponsors post clinical trial results on the registry within 12 months of completion.</strong>
  <br>
  <br>
  <a href="https://github.com/morris-frank/trial-results-tracker/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/morris-frank/trial-results-tracker/ci.yml?style=flat-square&amp;label=CI&amp;labelColor=16211B&amp;color=1AB172" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/status-pre--release-8EDE3D?style=flat-square&amp;labelColor=16211B" alt="Pre-release">
  <a href=".python-version">
    <img src="https://img.shields.io/badge/python-3.13-1AB172?style=flat-square&amp;labelColor=16211B" alt="Python 3.13">
  </a>
  <img src="https://img.shields.io/badge/output-static%20site-8EDE3D?style=flat-square&amp;labelColor=16211B" alt="Output: a static site">
</p>

<br clear="left">

- [What it does](#what-it-does)
- [Background](#background)
- [Install](#install)
- [Configuration](#configuration)
- [Development](#development)

## What it does

A public tracker for clinical trial results reporting. It measures every sponsor on a
registry against the WHO best-practice standard: summary results posted on the registry
within 12 months of completion, whether or not a law requires it. Legal-compliance
trackers already exist for the US (FDAAA TrialsTracker) and the old EU register; nobody
maintains one at the WHO standard for all sponsors.

It is pre-release. Today the build publishes unnamed aggregate counts from the snapshot
pinned in `SNAPSHOT`, under the Keestra-2021 replication rules; the rest arrives through
the tasks in [`docs/`](docs/).

It never states that a trial is unreported without saying how it looked: registry
results only, or registry results plus a search for journal publications.

## Background

- Keestra et al. 2021, *Trials* 22:385 ([doi](https://doi.org/10.1186/s13063-021-05330-5))
  built the first such tracker for ClinicalTrials.gov. Its site, clinical-trials-tracker.com,
  has served a frozen 2022-08-01 snapshot since.
- Later work showed what a successor must do differently: count cancelled and
  never-started trials separately, look for journal publications as well as registry
  results (e.g. TrialScout, 2026), and let institutions check the figures before
  publication.

## Install

Needs [mise](https://mise.jdx.dev). Everything else comes from `mise.toml`.

```sh
git clone git@github.com:morris-frank/trial-results-tracker.git
cd trial-results-tracker
mise run setup
mise run build   # static site into dist/
```

## Configuration

`.env.example` lists every variable. The build needs none; `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID` (a dedicated bot, not mario's) are only for the refresh report, set
as repository secrets for CI and in `.env` for `mise run notify`, which sends a test
report built from `data/raw/` if present.

Snapshots: raw registry data is never committed. The `Refresh` workflow
(`.github/workflows/refresh.yml`, weekly on Mondays at 04:00 UTC, or by manual
dispatch) runs `mise run fetch`, then
`mise run snapshot`, which publishes `data/raw/` as GitHub Release `data-<YYYY-MM-DD>`
with the `.jsonl.gz` and `manifest.json` as assets, and commits the tag to the one-line
`SNAPSHOT` file on `main`. A release is never overwritten: if that day's release exists,
`mise run snapshot` exits non-zero without changing anything. Running it locally needs
`gh` authenticated with write access to the repository. Every run, pass or fail, ends
with a Telegram message: rows, v1.0 category deltas (the headline's method) against the previously
pinned release, the release URL and the job status.

GitHub disables a scheduled workflow after 60 days without repository activity
([docs](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/disabling-and-enabling-a-workflow)).
The weekly pin commit is meant to count as that activity, but whether a commit made
with `GITHUB_TOKEN` counts is **[unverified]**; if the weekly report stops arriving,
re-enable the workflow in the Actions tab.

Deployment: Vercel builds `vercel.json`'s command on every push to `main` and serves
`dist/`, so the refresh's pin commit is what deploys new data. The build downloads the pinned release over public HTTPS (no token) and fails if
the download fails or the row count differs from the manifest; `build --snapshot-dir DIR`
uses a local snapshot instead.

## Development

`mise run check` is the definition of done: lint, format check and tests, the same as CI.

| task | does |
|---|---|
| `mise run lint` / `fmt` / `test` | the individual gates |
| `mise run hooks` | every hook over the whole repo |
| `mise run audit` | dependency vulnerabilities against `uv.lock` |
| `mise run secrets` | secret scan of the working tree |

`AGENTS.md` is the working agreement for changing this repository.

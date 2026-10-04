---
date: 2026-10-04
area: Engineering and hosting
---

## Question

What is the simplest robust architecture for a nightly-refreshed public tracker, built in Python with uv and published as a static site? It should classify every interventional ClinicalTrials.gov trial by lead sponsor against the WHO 12-month standard, Keestra et al. 2021 style. The options compared below cover data pull, snapshot storage, processing, how data reaches the browser, hosting, deploy triggering and Telegram notification.

## Findings

### Data source: CT.gov API v2 vs AACT

**CT.gov API v2, measured today (2026-10-04).**

- The registry holds 605,599 studies, with an average record size of 17,301 bytes (`/api/v2/stats/size`, https://clinicaltrials.gov/api/v2/stats/size). Pulling full records would mean roughly 10 GB of JSON.
- The data timestamp was `2026-10-02T09:00:04` and the API version was 2.0.5 (https://clinicaltrials.gov/api/v2/version). The registry refreshes daily, but this timestamp lagged about 2 days at fetch time.
- `pageSize` is coerced down to 1,000 at most, and the default is 10. Source: the OpenAPI spec (https://clinicaltrials.gov/api/oas/v2).
- The `fields=` parameter limits each record to the columns the classification needs. With it set, `query.term=AREA[StudyType]INTERVENTIONAL` returned `totalCount` 462,154. Each record came back with NCT ID, overall status, primary completion date and type, completion date, results-first-submit and results-first-post dates, last-update date, lead sponsor name and class, and `hasResults`. Source: https://clinicaltrials.gov/api/v2/studies.
- A full pull from a laptop took **463 pages and 1,022 s (about 17 min)** sequentially, with a 1.2 s pause between pages. It transferred **210 MB raw JSON, or 17 MB gzipped as JSONL**. Without the pause, one page took about 1.1 s. This is my own measurement with a script in the session scratchpad. It is not committed.
- Rate limit: secondary sources say "about 50 requests per minute per IP" (https://glama.ai/mcp/servers/@genomoncology/biomcp/blob/c7db7e1ea47c1df8f8f9bfc98a5bf2da5c962e3a/docs/backend-services-reference/04-clinicaltrials-gov.md). I found no official statement, and the response headers carry no rate-limit header. **[unverified]** Pacing at about 1 request per 2 s stayed well under any plausible limit and still finished in under 20 min.
- A bulk endpoint, `https://clinicaltrials.gov/api/int/studies/download?format=json.zip`, returns `ctg-studies.json.zip` (HTTP HEAD, 2026-10-04). It sits under `/api/int/` (internal), the response has no Content-Length, and its size and stability are **[unverified]**. Do not depend on it.

**AACT (CTTI).**

- AACT is a daily-refreshed relational copy of the whole registry. "Download full snapshots" requires creating an account (https://aact.ctti-clinicaltrials.org/).
- Older documentation describes pipe-delimited flat files, one per table: 30 rolling daily snapshots plus permanent monthly archives (https://aact.ctti-clinicaltrials.org/downloads/flatfiles_instructions, https://aact.ctti-clinicaltrials.org/pipe_files). Both of those URLs now return 404 after a site redesign (checked 2026-10-04). The current download URLs and file sizes are **[unverified]**.
- AACT adds a login secret, a multi-GB download **[unverified]**, and one more party between us and the source. In return it gives a relational schema that this classification does not need. The API pull with `fields=` is about 17 MB compressed.
- The monthly AACT archives remain useful later, to reconstruct historical states for back-testing (see Open decision 6).

**GitHub Actions fits easily.**

- Actions is free for public repositories on standard GitHub-hosted runners (https://docs.github.com/en/billing/concepts/product-billing/github-actions).
- A job can run up to 6 h (https://docs.github.com/en/actions/reference/limits).
- The standard Linux runner has 4 CPU, 16 GB RAM and 14 GB SSD (https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
- **Caveat:** "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days" (https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/disabling-and-enabling-a-workflow). If the nightly job does not commit, the cron will die silently. Whether a bot commit made with `GITHUB_TOKEN` counts as "activity" is **[unverified]**.

### Snapshot storage

| Option | Limits | Fit |
|---|---|---|
| GitHub Releases | Each file under 2 GiB, up to 1,000 assets per release, no limit on total size or bandwidth (https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) | One release per day (tag `data-YYYY-MM-DD`) with the raw `.jsonl.gz` (about 17 MB) and the classified Parquet (about 5 MB). No new account. `GITHUB_TOKEN` can write it. |
| Cloudflare R2 | Free tier: 10 GB-month storage, 1M Class A and 10M Class B operations per month, free egress (https://developers.cloudflare.com/r2/pricing/) | At about 22 MB/day, 10 GB fills in about 450 days. Needs a Cloudflare account and an API token. |
| Hugging Face datasets | Public storage is "best-effort" for free users. Recommendations: under 100k files per repo, under 10k per folder. Huge commit counts degrade the repo (https://huggingface.co/docs/hub/storage-limits) | Good second channel for reuse (Parquet viewer, citation). A git commit per night will degrade it over years. |

### Processing

- DuckDB read the 462,154-record JSONL and wrote a zstd Parquet file of the 6 classification columns. Output: **5.1 MB, in 0.6 s on a laptop**. This is my own measurement with `duckdb` via `uv run`.
- At this scale Polars is equally viable. DuckDB has the advantage that the same SQL can later run in the browser via DuckDB-WASM. The deciding factor should be which one is easier to test as a pure function of (snapshot, as-of date) to category. I have no external source for that and it is a judgement call.
- Measured data shape: **44,409 distinct raw lead-sponsor strings**, of which only **2,082 have 30 or more interventional trials**. Sponsor names are free text and unnormalised, so the real entity count is lower. Normalisation is a separate data question.

### Data to the browser

- **Pre-aggregated JSON.** One summary row per sponsor (name, total, with-results) was 1.59 MB raw and **0.55 MB gzipped** (own measurement). One JSON file *per sponsor* would mean about 44k files. That exceeds Cloudflare Pages' 20,000-file limit (https://developers.cloudflare.com/pages/platform/limits/). Vercel's CLI limit of 15,000 *source* files also applies to a CLI deployment (https://vercel.com/docs/limits). Whether that limit counts files in a `--prebuilt` output upload is **[unverified]**.
- **DuckDB-WASM over Parquet.** DuckDB-WASM runs entirely client-side. Its JavaScript httpfs fetches only the byte ranges a query needs, but "reading through the built-in httpfs extension may currently download the whole file". It is single-threaded by default with a 4 GB memory ceiling (https://duckdb.org/docs/current/clients/wasm/overview.html). A 5 MB Parquet file is small enough to fetch whole, so range requests are not needed. The WASM runtime is the heavier part of the page (bundle size **[unverified]**).
- Practical split: a static summary JSON (about 0.5 MB gz) drives the league table. Static HTML pages go only to sponsors above a threshold (for example 30 or more trials, about 2,082 pages), which stays under every file limit. The long tail plus per-trial drill-down are served as one Parquet file, loaded with DuckDB-WASM only on the "explore" page.

### Hosting

| | Vercel Hobby (current) | Cloudflare Pages / Workers static assets | GitHub Pages |
|---|---|---|---|
| Commercial use | "Hobby teams are restricted to non-commercial personal use only". Commercial means financial gain of **anyone** involved in production, including a paid employee or consultant writing the code. Donations are allowed (https://vercel.com/docs/limits/fair-use-guidelines) | No non-commercial clause found in what I read. The Self-Serve Subscription Agreement itself was not reviewed (https://www.cloudflare.com/website-terms/) **[unverified]** | Not to be used "primarily directed at either facilitating commercial transactions or providing commercial software as a service" (https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) |
| Deploy frequency | 100 deployments/day, 45 min build, deploy hooks 60/hour (https://vercel.com/docs/limits) | 500 builds/month, 20 min build timeout, 1 concurrent build (https://developers.cloudflare.com/pages/platform/limits/). Direct upload from CI via `cloudflare/wrangler-action` (https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/) | 10 builds/hour soft, which does not apply when deploying from an Actions workflow. 10 min deploy timeout |
| Size and files | CLI upload 100 MB (Hobby), 15,000 source files via CLI | 20,000 files per site, 25 MiB per file. Workers static asset requests are "free and unlimited" (https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/) | Site up to 1 GB |
| Bandwidth | 100 GB Fast Data Transfer/month included (https://vercel.com/docs/limits/fair-use-guidelines) | No bandwidth limit stated on the Pages limits page | 100 GB/month soft |
| Other | Hobby cannot connect to repos owned by a GitHub *organisation* (https://vercel.com/docs/limits). `morris-frank/trial-results-tracker` is a personal repo, so this is fine. | | |

At our size (a site of about 10 to 20 MB, about 2k pages, 1 deploy per night) **all three fit** on technical limits. The decider is the commercial clause and whether the project stays personal. It also matters that every deploy comes from a GitHub Actions run that already has the data.

### Triggering the deploy after a refresh

- **Vercel deploy hook.** A POST to a secret URL "re-run[s] the Build Step" for a linked Git repo and branch. The build therefore runs on Vercel *from the Git source* and would have to fetch the data again itself (https://vercel.com/docs/deploy-hooks). The hook is a bearer secret, and hooks are ignored when `github.enabled = false`.
- **Vercel CLI with a token.** Run `vercel pull`, then `vercel build --prod`, then `vercel deploy --prebuilt --prod`, with secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` (https://vercel.com/kb/guide/how-can-i-use-github-actions-with-vercel). The site is built in the same Actions job that holds the fresh data and uploads only the output. **This one fits better:** there is no second fetch, and the deploy is atomic with the data it shows.
- Current `vercel.json` builds on Vercel with `uv run ... build --out dist` on every push. A nightly data job would also need that path to work. Simplest is to switch Git-triggered builds off, or keep them for code-only previews, and let Actions be the only production deployer.

### Telegram notification

- `POST https://api.telegram.org/bot<token>/sendMessage` with `chat_id` and `text` (1 to 4,096 characters), and optional `parse_mode` (https://core.telegram.org/bots/api#sendmessage). Rate guidance: in a single chat, avoid more than one message per second (https://core.telegram.org/bots/faq).
- One `curl` step at the end of the job, with `if: always()` so failures are reported too, is enough. It needs secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Use a dedicated bot next to the mario bot; do not reuse mario's token.

## Recommendation

Use **one GitHub Actions workflow** (`refresh.yml`, `schedule: cron "17 6 * * *"` plus `workflow_dispatch`) on `ubuntu-latest`, free for this public repo:

1. **Pull.** Page through CT.gov API v2: `fields=` with about 12 columns, `pageSize=1000`, interventional only. Use one request about every 2 s, with retry and backoff on 429/5xx. Expect **about 463 requests, about 17 min, 210 MB in transit, 17 MB gz on disk**. Record `dataTimestamp` from `/api/v2/version` as the snapshot's provenance.
2. **Classify.** Use DuckDB (SQL), or Polars if preferred, as a pure function of (snapshot, as-of date), with unit tests on the Keestra category boundaries (395 days, etc.). Output `trials.parquet` (about 5 MB) and `sponsors.json` (about 0.5 MB gz).
3. **Snapshot.** Create a GitHub Release `data-YYYY-MM-DD` with `ctgov-raw.jsonl.gz`, `trials.parquet` and a `manifest.json` (API version, data timestamp, row count, code SHA). Releases are free, unlimited in total size, and versioned next to the code. Mirror to Hugging Face later if reuse becomes a goal.
4. **Build.** Render the static site in the same job: a league table from `sponsors.json`, static pages only for sponsors with 30 or more trials (about 2k), and an explore page using DuckDB-WASM over `trials.parquet`. That is well under 20k files and 100 MB.
5. **Deploy.** Run `vercel build --prod` and `vercel deploy --prebuilt --prod` with a token. This is one deploy a night, against a limit of 100/day. Keep the provider swappable: the same `dist/` deploys to Cloudflare with `wrangler pages deploy dist`.
6. **Keep alive and notify.** Commit `data/latest.json` (the manifest) to `main` each night, which also gives a public audit trail and should count as activity against the 60-day cron disable **[unverified]**. Then send one Telegram `sendMessage`: rows, category deltas versus yesterday, deploy URL, and a failure flag.

Total cost: €0. Moving parts: one workflow, five secrets (Vercel ×3, Telegram ×2), no database, no server.

## Open decisions

1. **Host.** (a) Stay on Vercel Hobby. (b) Cloudflare Pages / Workers static assets. (c) GitHub Pages. *Recommend (a) while the project is strictly personal and unpaid*, because it is already wired up. Switch to (b) the moment anyone could be paid for it or it is tied to an employer: Vercel's clause covers "a paid employee or consultant writing the code". The swap costs one CI step.
2. **Is this personal or Soilytix work?** Owner, licence and hosting all follow from the answer, and it has to be made by a human. Options: personal side project, or Soilytix-affiliated. *Recommend personal, explicitly not via Soilytix*, as the request says. Keep accounts, tokens and domain out of Soilytix infrastructure.
3. **Snapshot store.** (a) GitHub Releases only. (b) Releases plus a Hugging Face dataset mirror. (c) Cloudflare R2. *Recommend (a) now, (b) once the method is published.*
4. **Deploy trigger.** (a) `vercel deploy --prebuilt` from Actions with a token. (b) A deploy hook that rebuilds on Vercel and fetches data again. *Recommend (a).* It also means turning off or limiting Vercel's own Git-push production builds, which is a project setting someone must change.
5. **Browser data layer.** (a) Pre-aggregated JSON plus static pages only. (b) Add DuckDB-WASM explore over Parquet. *Recommend (a) for v1 and (b) as v2*, after a page-weight check, because the WASM bundle size is unverified.
6. **History.** (a) Start the time series from the first nightly snapshot. (b) Backfill from AACT monthly archives, which needs an account and has unverified availability and size. *Recommend (a) now. Decide on (b) once the AACT download path is confirmed.*
7. **Sponsor page threshold.** Choose the number of trials needed for a static sponsor page: 30 (about 2,082 pages, raw strings), 10, or all trials served via Parquet. *Recommend 30 until sponsor-name normalisation exists.*
8. **Refresh cadence.** Nightly or weekly. *Recommend nightly*, because it is cheap. Note that the CT.gov data timestamp was 2 days old when checked, so "nightly" means "latest available", not "yesterday's".

## Sources

- ClinicalTrials.gov API v2: https://clinicaltrials.gov/api/v2/version · https://clinicaltrials.gov/api/v2/stats/size · https://clinicaltrials.gov/api/v2/studies · https://clinicaltrials.gov/api/oas/v2
- Rate limit (secondary): https://glama.ai/mcp/servers/@genomoncology/biomcp/blob/c7db7e1ea47c1df8f8f9bfc98a5bf2da5c962e3a/docs/backend-services-reference/04-clinicaltrials-gov.md
- AACT: https://aact.ctti-clinicaltrials.org/ · https://aact.ctti-clinicaltrials.org/downloads/flatfiles_instructions · https://aact.ctti-clinicaltrials.org/pipe_files
- GitHub Actions: https://docs.github.com/en/billing/concepts/product-billing/github-actions · https://docs.github.com/en/actions/reference/limits · https://docs.github.com/en/actions/reference/runners/github-hosted-runners · https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/disabling-and-enabling-a-workflow
- GitHub Releases: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- Cloudflare R2: https://developers.cloudflare.com/r2/pricing/
- Hugging Face Hub: https://huggingface.co/docs/hub/storage-limits
- DuckDB-WASM: https://duckdb.org/docs/current/clients/wasm/overview.html
- Vercel: https://vercel.com/docs/limits · https://vercel.com/docs/limits/fair-use-guidelines · https://vercel.com/docs/deploy-hooks · https://vercel.com/kb/guide/how-can-i-use-github-actions-with-vercel
- Cloudflare Pages / Workers: https://developers.cloudflare.com/pages/platform/limits/ · https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/ · https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/ · https://www.cloudflare.com/website-terms/
- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Telegram: https://core.telegram.org/bots/api#sendmessage · https://core.telegram.org/bots/faq
- Own measurements (2026-10-04, laptop): full fields-restricted API pull and DuckDB classification. The scripts are in the session scratchpad and are not committed.

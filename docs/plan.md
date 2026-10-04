---
date: 2026-10-04
area: v1 plan
---

Built from the six notes in `docs/research/` (data-sources, methodology, landscape, legal, engineering, critique), all dated 2026-10-04. Factual claims carry the URL the research note cited; anything the notes could not confirm stays marked **[unverified]**. Where the notes contradict each other (critique.md, "Contradictions"), the conflict is resolved here as a decision, not silently.

## Proposal

**What v1 is.** A dated, reproducible audit of every interventional ClinicalTrials.gov trial against the WHO standard: summary results on the registry within 12 months of primary completion ([WHO 2017 joint statement](https://www.who.int/news/item/18-05-2017-joint-statement-on-registration)). It follows the Keestra et al. 2021 method ([Trials 22:385](https://doi.org/10.1186/s13063-021-05330-5)) with explicit, versioned corrections. It describes the registry; it does not allege legal breaches (AGENTS.md rule 2).

**Source.** ClinicalTrials.gov API v2 only, called directly: paged `/studies` with `pageSize=1000`, `filter.advanced=AREA[StudyType]INTERVENTIONAL` and a `fields=` list of about 20 columns ([OpenAPI spec](https://clinicaltrials.gov/api/oas/v2)). A measured full pull was 463 pages, about 17 min, 17 MB gzipped (engineering.md, own measurement 2026-10-04). Provenance is the `dataTimestamp` from [`/api/v2/version`](https://clinicaltrials.gov/api/v2/version). Rejected for v1: AACT (account plus unread terms, [aact](https://aact.ctti-clinicaltrials.org/)); the undocumented bulk zip (not in the OpenAPI spec); ICTRP (non-commercial clause, [WHO terms](https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set/downloading-records-from-the-ictrp-database)); CTIS, EUCTR, ISRCTN (different "reported" semantics and undocumented endpoints; v2 at the earliest). No person-level fields are ever fetched (legal.md §2).

**Methodology.** Two rule sets in one pure module (AGENTS.md rule 5):
- `keestra-2021`: a faithful replication of the predecessor's code ([GlobalHealthRanking](https://github.com/LeeSean96/GlobalHealthRanking), MIT), used as the first published baseline and for a crosswalk.
- `v1.0`: the corrected rules, once decisions D1 to D5 are made. Every published number carries the rule-set version, the CT.gov `dataTimestamp` and the code commit.

**Categories (v1.0, pending D1 to D5).** No reporting requirement · due, not reported · due, reported in time · due, reported late · due, submitted but returned in QC · completed, not yet due · ongoing · status overdue (open status, PCD long past) · inconsistent data. Status overdue and inconsistent are never counted as unreported (AGENTS.md rule 3); the headline shows them as an upper bound beside the point estimate (methodology.md rec. 6). A separate legal-duty column defaults to "not determined".

**Outputs.**
1. Overview page: headline share of due trials not reported on the registry, with Wilson 95% CIs and the denominator, and counts per category, each stamped with method version and data date.
2. Methodology page with the modifications statement ClinicalTrials.gov's terms ask for (legal.md §1; the current terms text is **[unverified]**).
3. Downloads: per-trial classified CSV and per-sponsor CSV, each with a manifest.
4. Later (after the naming gate, D7): named sponsor league table, sponsor pages listing trials to fix, and a corrections log.

**Architecture.** Python 3.13, stdlib-first, no database, no server:
`fetch` (API to `data/raw/ctgov-<date>.jsonl.gz` + `manifest.json`) → GitHub Release `data-<date>` (raw snapshot is never committed, rule 4) → `build` (downloads the pinned snapshot, parses, classifies, aggregates, renders static HTML/CSV into `dist/`). Classification runs at build time, so a rule change redeploys without re-fetching. The only committed data artefact is `SNAPSHOT`, a one-line pin naming the release tag. DuckDB/Polars and a DuckDB-WASM explore page are deferred: 462k rows classify in pure Python in seconds, and a per-trial pure function is the easiest thing to test.

**Publishing.** Personal project, not via Soilytix (engineering.md D2). A scheduled GitHub Actions workflow fetches, releases the snapshot, and commits the bumped `SNAPSHOT` pin to `main`. That commit triggers the existing Vercel Hobby Git build, so there is no Vercel token in CI. The same commit counts as repository activity against GitHub's 60-day scheduled-workflow disable ([docs](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/disabling-and-enabling-a-workflow); whether a `GITHUB_TOKEN` commit counts is **[unverified]**). A dedicated Telegram bot, not mario's, reports each run ([sendMessage](https://core.telegram.org/bots/api#sendmessage)). `dist/` is host-agnostic, so it can move to Cloudflare with `wrangler pages deploy dist` ([docs](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/)) if Vercel's non-commercial clause ever bites ([fair use](https://vercel.com/docs/limits/fair-use-guidelines)).

**Launch sequence.** Unnamed aggregates first. Named institutions only after D7's gate: the lawyer consult, a validation sample, and a corrections process (legal.md rec. "Before launch"; [TranspariMED](https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results)).

## Decisions needed from the owner

1. **Which date counts as "reported"?** (a) `resultsFirstSubmitDate`, as Keestra's code and the FDAAA tracker do ([FDAAA about](https://fdaaa.trialstracker.net/about/)); (b) `resultsFirstPostDateStruct`, the strict "publicly posted" reading; (c) both as two headlines. Do not use `hasResults`: it is `Present(ResultsFirstSubmitDate)` ([metadata](https://clinicaltrials.gov/api/v2/studies/metadata)). **Recommend (a) as headline, posting date shown per trial, and a submission whose latest unposted event is RESET with nothing posted as its own "submitted, returned in QC" category.** Shapes T6.
2. **The "due" threshold and the in-time cut.** The notes disagree (critique.md contradiction 1). (a) Keestra code: due when `as_of − PCD > 395 d`, in time when `results − PCD ≤ 365 d`; (b) due at 365 d, in time at ≤ 395 d; (c) one number, 395 d, for both. **Recommend (c):** one rule a reader can check, and it never calls a trial overdue while it is still inside the 30-day QC grace. Shapes T6.
3. **Suspended trials.** (a) no reporting requirement (Keestra); (b) ongoing; (c) due once PCD + 395 d has passed. **Recommend (b).** Suspension is a pause, not an exemption. Shapes T6.
4. **Finished trials (COMPLETED/TERMINATED) with a missing or ESTIMATED PCD.** (a) inconsistent; (b) fall back to completion date and tag `pcd_fallback`; (c) treat an estimated PCD as binding, as FDAAA does. 300 such ESTIMATED records existed on 2026-10-04 ([API query](https://clinicaltrials.gov/api/v2/studies?filter.overallStatus=COMPLETED,TERMINATED&query.term=AREA%5BStudyType%5DINTERVENTIONAL%20AND%20AREA%5BPrimaryCompletionDateType%5DESTIMATED&countTotal=true)). **Recommend (a), with no fallback in v1.0**, which resolves the internal contradiction in methodology.md (critique.md contradiction 3). Also: TERMINATED with actual enrolment 0 counts as no reporting requirement (yes/no). **Recommend yes.** Shapes T6.
5. **Stale statuses in the headline.** (a) excluded from the denominator and shown separately; (b) counted as unreported; (c) a range, with (a) as the point estimate and an upper bound that counts them. **Recommend (c)**, with the stale threshold at "open status and PCD more than 395 d ago". Shapes T7.
6. **Attribution, grouping and ranking threshold.** Unit: (a) lead sponsor; (b) responsible party; (c) IntoValue-style institution. Grouping: aliases only, or also parent/child roll-ups. Rank threshold: 10, 20 or 50 due trials. **Recommend lead sponsor, aliases only (no roll-ups), rank at ≥ 20 due trials; everyone else searchable, not ranked.** This settles critique.md contradiction 7: the unit is *due* trials. Shapes T10, T12.
7. **Naming gate.** (a) aggregates only until a Dutch media/privacy lawyer consult, the first validation sample and the corrections process exist, then name; (b) name at launch. **Recommend (a).** Blocks T12.
8. **Person-level data and individual sponsors.** (a) drop all person fields and pool `INDIV` and person-named sponsors into one unnamed "individual sponsors" bucket; (b) show individual sponsors by name; (c) mirror the registry. **Recommend (a)** (legal.md §2). Shapes T9.
9. **Refresh cadence and snapshot store.** Cadence: nightly or weekly (the notes disagree, critique.md contradiction 6). Store: GitHub Releases only, or also a Hugging Face mirror. **Recommend weekly snapshots as GitHub Releases**: about 52 releases a year instead of 365, still far fresher than the 2022 freeze, and CT.gov's own timestamp lagged 2 days anyway. Move to nightly if users ask. Shapes T8.
10. **Deploy trigger and host.** (a) the refresh workflow commits the `SNAPSHOT` pin and Vercel's Git build deploys it (no token in CI); (b) `vercel deploy --prebuilt` from Actions with a token ([guide](https://vercel.com/kb/guide/how-can-i-use-github-actions-with-vercel)); (c) Cloudflare Pages direct upload. **Recommend (a) on Vercel Hobby while the project is unpaid and personal; switch to (c) before any money or employer tie** ([Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines)). Shapes T8.
11. **Publisher identity, framing and right of reply.** Name on the site: personal name with a Dutch contact, or a project pseudonym. Framing: "successor to clinical-trials-tracker.com" or "follows the Keestra et al. 2021 method". Contacting Keestra et al./UAEM before launch: yes/no. Right of reply: contact address plus public corrections log, or advance notice to named sponsors. **Recommend personal name, a "not affiliated with Soilytix" line, "follows the Keestra method" until the authors agree otherwise, contact them, and contact plus corrections log at launch** (landscape.md D7–D8; legal.md D4–D5). Blocks T12.
12. **Licences.** Code is MIT already (`pyproject.toml`). Derived data: CC BY 4.0, CC0, or no explicit licence. CC BY 4.0 is only compatible while ICTRP and ISRCTN data stay out of the published dataset (critique.md contradiction 15). **Recommend CC BY 4.0 for derived CT.gov data**, re-checked before adding any other registry. Shapes T9.
13. **Publication linkage (first extension).** (a) none; (b) self-hosted TrialScout, MIT, sensitivity 92.5%, specificity 81.2%, about USD 0.043 per trial ([JCE 2026](https://doi.org/10.1016/j.jclinepi.2026.112484), [repo](https://github.com/lahnstrom/trialscout)); (c) our own deterministic NCT-ID linkage in PubMed/Europe PMC metadata, with TrialScout as a cross-check. **Recommend (c) first**: free, explainable, shown only as "possible publication", and never changes the registry headline. (b) needs the owner to agree to pay for LLM calls. Blocks T14.
14. **Validation sample and coders.** 100, 200 or 400 trials per release; one or two coders; who. **Recommend 200 stratified trials, two coders, for the first release that names sponsors, then per major method version.** Nothing in the repo commits anyone's hours yet. Blocks T11.
15. **Legal-duty axis at launch.** (a) "not determined" everywhere, plus static notes on UK/EU timing; (b) add US "probable ACT" flags; (c) all three jurisdictions. No UK trial can be legally overdue before about 28 Apr 2027 ([SI 2025/538](https://www.legislation.gov.uk/uksi/2025/538/made), Sch 14 para 2(8)), and EU due dates need CTIS end-of-trial dates. **Recommend (a) for v1 and (b) as an extension.** Blocks T13.

## Tasks

### T1. Fetch a dated ClinicalTrials.gov snapshot
- Depends on: none
- Problem and direction: There is no data pipeline. Add `fetch`: page through `GET /api/v2/studies` with `filter.advanced=AREA[StudyType]INTERVENTIONAL`, `pageSize=1000`, `nextPageToken`→`pageToken`, keeping every other parameter fixed ([OpenAPI spec](https://clinicaltrials.gov/api/oas/v2)). Request only the classification fields in data-sources.md §1. Include the date structs and `type`s, the results submit/QC/post dates, `unpostedEvents`, `dispFirstSubmitDate`, `statusVerifiedDate`, `lastUpdatePostDateStruct`, `enrollmentInfo`, `whyStopped`, `leadSponsor`, `responsibleParty.type`, `collaborators` and the FDA oversight flags. Request no investigator, official, contact or point-of-contact fields (legal.md §2). Pace at about one request per 2 s and retry with backoff on 429/5xx. The ~50 req/min limit is **[unverified]** ([OpenAPI](https://clinicaltrials.gov/api/oas/v2) documents none). Write `data/raw/ctgov-<YYYY-MM-DD>.jsonl.gz` and `manifest.json`, containing `apiVersion`, `dataTimestamp` from `/api/v2/version`, the `totalCount` from the first page (`countTotal=true`), the rows written, the field list and the code SHA. Abort without writing a manifest when rows written ≠ `totalCount`, so a partial pull can never be published (critique.md gap 14). Rejected: AACT (account, unread terms); the `studies/download` zip (not in the spec); httpx/requests (stdlib `urllib` suffices).
- Files and commands: `src/trial_results_tracker/fetch.py`, CLI subcommand `fetch --out data/raw` in `__main__.py`, `mise run fetch`, `tests/test_fetch.py` with a recorded two-page fixture in `tests/fixtures/` (no network in tests).
- Done when: merged on main with `mise run check` green, plus `mise run fetch` locally produces a gzipped JSONL whose line count equals the manifest's `totalCount`, a test proves a short pull raises instead of writing a manifest, and no person-level field name appears in the field list (asserted by a test).
- Blocked by decision: none

### T2. Parse raw records into typed trial rows
- Depends on: T1
- Problem and direction: Classification must not touch raw JSON. Add a `Trial` frozen dataclass and a pure `parse(record) -> Trial`. Normalise partial dates (`YYYY-MM`, `YYYY`) to the *last* day of the period, the reading most favourable to the sponsor, and keep a `date_precision` field. Do this for PCD, completion and results dates and for `statusVerifiedDate` too (critique.md gap 6). Keep `type` (ACTUAL/ESTIMATED) beside each date and keep `sponsor_raw` and `sponsor_class` unchanged. Derive `latest_unposted_event` from `unpostedEvents` by date. Unknown enum values become a typed "unrecognised" value rather than crashing, and are counted in the build report. Raising on unknown enums was rejected: an API minor-version change (currently 2.0.5, [version](https://clinicaltrials.gov/api/v2/version)) should flag rows, not kill the deploy.
- Files and commands: `src/trial_results_tracker/model.py`, `src/trial_results_tracker/parse.py`, `tests/test_parse.py` (fixtures include NCT01245270, a submit/post gap, and NCT01916382, RELEASE then RESET twice, from data-sources.md §1).
- Done when: merged on main with `mise run check` green, plus tests cover a full date, a month-partial date, a year-partial date, a missing PCD, an ESTIMATED PCD, an unknown status enum and an unposted-event sequence, and parsing a full local snapshot completes without exceptions.
- Blocked by decision: none

### T3. Implement the Keestra-2021 replication rule set
- Depends on: T2
- Problem and direction: The first published numbers should be a faithful replication, so v1.0 changes can be measured against them later. Create `classify.py`: a pure `classify(trial, as_of, rules) -> Category` with no I/O (AGENTS.md rule 5). Ship the `KEESTRA_2021` rule set, transcribed from the predecessor's code, not its paper: threshold 365 + 30, results date = `results_first_submitted`, WITHDRAWN/SUSPENDED = no requirement, everything unmatched = inconsistent ([clinical_trial.py](https://github.com/LeeSean96/GlobalHealthRanking/blob/master/src/ClinicalTrialsTracker/model/clinical_trial.py), [definitions.py](https://github.com/LeeSean96/GlobalHealthRanking/blob/master/src/ClinicalTrialsTracker/definitions.py)). Read the source to settle the missing-PCD rule, which methodology.md and data-sources.md read differently (critique.md contradiction 3), and record the line cited in a docstring. Keep the MIT notice if any code is copied. The enum includes v1.0's extra categories from the start so T6 only adds rules.
- Files and commands: `src/trial_results_tracker/classify.py`, `tests/test_classify_keestra.py` (one test per rule, plus the 395-day boundary on both sides).
- Done when: merged on main with `mise run check` green, plus every Keestra category has a direct test, the boundary at exactly 395 days is tested, and the module imports nothing that does I/O (checked by a test on `classify.__dict__` or by import lint).
- Blocked by decision: none

### T4. Publish snapshots as GitHub Releases and pin one
- Depends on: T1
- Problem and direction: Raw data must be reproducible but never committed (AGENTS.md rule 4). Add `.github/workflows/refresh.yml`, `workflow_dispatch` only for now. It runs `mise run fetch`, creates release `data-<YYYY-MM-DD>` with the `.jsonl.gz` and `manifest.json` as assets ([Releases limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)), then commits the tag name to a one-line `SNAPSHOT` file on `main`. Releases are immutable once published; a same-day re-run fails rather than overwriting. Rejected: R2 (another account) and Hugging Face (degrades with daily commits, [limits](https://huggingface.co/docs/hub/storage-limits)). The scheduled trigger is added in T8.
- Files and commands: `.github/workflows/refresh.yml` (`permissions: contents: write`), `SNAPSHOT`, `mise run snapshot` (wraps `gh release create`), README "Configuration" section updated.
- Done when: merged on main with `mise run check` green, plus one manual dispatch produced a public `data-<date>` release with both assets and a bot commit updating `SNAPSHOT`, and re-running the same day fails without changing the release.
- Blocked by decision: none

### T5. Build an unnamed aggregate site from the pinned snapshot
- Depends on: T3, T4
- Problem and direction: The deploy still serves a placeholder. `build` should read `SNAPSHOT`, download the release assets over public HTTPS (no token, so Vercel's Git build can run it), verify the row count against the manifest, parse, classify with `KEESTRA_2021`, and render static HTML. Produce:
  - an overview page with counts and shares per category, marked "Keestra-2021 replication" with the data date and code SHA (AGENTS.md rule 1);
  - a methodology page stating the rules and the modifications statement (legal.md §1);
  - a footer naming the publisher, crediting ClinicalTrials.gov, and stating it is not affiliated with Soilytix.

  Show no sponsor names (naming gate, D7). Use plain HTML and CSS with no client JS, analytics or cookies (legal.md §5). If the download fails the build fails; it never falls back to a placeholder. Rejected: a JS framework or DuckDB-WASM (bundle size **[unverified]**, not needed for aggregates).
- Files and commands: `src/trial_results_tracker/snapshot.py` (download + verify), `src/trial_results_tracker/render.py`, `site/` templates, `__main__.py` `build`, `vercel.json` unchanged, `tests/test_build.py` extended with a fixture snapshot via a `--snapshot-dir` override.
- Done when: merged on main with `mise run check` green, plus the Vercel deployment from that push shows category counts for the pinned snapshot with the data date and method label visible, and the page source contains no sponsor name.
- Blocked by decision: none

### T6. Add the methodology v1.0 rule set and a Keestra crosswalk
- Depends on: T3
- Problem and direction: Keestra's rules count suspended trials as exempt and lump returned-in-QC and stale records together (methodology.md §2–5). Add `V1_0` next to `KEESTRA_2021` in `classify.py`, implementing D1–D4:
  - the reporting date;
  - one 395-day threshold;
  - suspended handling;
  - missing or ESTIMATED PCD;
  - zero-enrolment TERMINATED;
  - the "submitted, returned in QC" category;
  - "status overdue" for open statuses past PCD + 395 d.

  Add a `crosswalk(trials, as_of)` that cross-tabulates the two rule sets, and render it on the methodology page so readers see how much each correction moves the numbers. Switch the site's default rule set to `V1_0` and keep `KEESTRA_2021` as the comparison. Rejected: replacing Keestra's rules outright (loses comparability) and replicating them unchanged (keeps known errors).
- Files and commands: `src/trial_results_tracker/classify.py`, `src/trial_results_tracker/crosswalk.py`, `tests/test_classify_v1.py`, `docs/methodology.md` (the versioned method text; replaces the research recommendation).
- Done when: merged on main with `mise run check` green, plus every v1.0 rule has a direct test that cites its decision number, the deployed methodology page shows the crosswalk table for the pinned snapshot, and every number on the site names `v1.0`.
- Blocked by decision: 1, 2, 3, 4

### T7. Show the headline with confidence intervals and the stale-status range
- Depends on: T6
- Problem and direction: A single "% unreported" hides the TranspariMED problem: stale status inflates it, and some results are missed ([TranspariMED](https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results)). Compute the headline as due-not-reported over due, with a Wilson 95% CI and the denominator, as the Nordic and FDAAA studies report proportions with CIs ([Nilsonne 2025](https://doi.org/10.1016/j.jclinepi.2025.111710), [Lancet 2020](https://doi.org/10.1016/s0140-6736(19)33220-9)). Beside it, show an upper bound that counts status-overdue and inconsistent trials as unreported (D5). Wording stays a registry observation ("no summary results on ClinicalTrials.gov within 12 months of primary completion, as of <date>"), never "failed" or "hid" (legal.md §3). Rejected: Kaplan–Meier time-to-report in v1 (useful later, not needed for the headline).
- Files and commands: `src/trial_results_tracker/stats.py` (pure, stdlib `math`), `render.py`, `tests/test_stats.py` (Wilson against hand-computed values, including n = 0 and p = 0/1).
- Done when: merged on main with `mise run check` green, plus the deployed overview shows point estimate, CI, denominator and upper bound with the data date, and a test covers the zero-denominator case.
- Blocked by decision: 5

### T8. Schedule the refresh, deploy through the pin, and notify Telegram
- Depends on: T4, T5
- Problem and direction: Publishing must be continuous without manual dispatch. Add a `schedule` cron to `refresh.yml` at the D9 cadence. The `SNAPSHOT` commit then triggers the Vercel Git build, which serves as the deploy (D10a). Telegram notification is added as a step with `if: always()`. It calls `sendMessage` with rows, category deltas versus the previous manifest, release URL, and pass/fail, using `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as repo secrets of a new bot, not mario's ([sendMessage](https://core.telegram.org/bots/api#sendmessage)). Add both keys to `.env.example` and a `mise run notify` for local testing. Document the 60-day inactivity rule and the fact that the pin commit is meant to count as activity **[unverified]** ([docs](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/disabling-and-enabling-a-workflow)). Rejected for now: `vercel deploy --prebuilt` with three Vercel secrets (D10b), kept as the fallback.
- Files and commands: `.github/workflows/refresh.yml`, `src/trial_results_tracker/notify.py`, `.env.example`, `mise.toml` (`notify`), `tests/test_notify.py` (message formatting only; no network).
- Done when: merged on main with `mise run check` green, plus one scheduled run completed end to end (release, pin commit, Vercel deploy live with the new data date) and its Telegram message arrived, and a forced failure run also sent a failure message.
- Blocked by decision: 9, 10

### T9. Publish per-trial and per-sponsor downloads with provenance
- Depends on: T6
- Problem and direction: Journalists and researchers use CSV downloads ([FDAAA TrialsTracker](https://fdaaa.trialstracker.net/)). Emit:
  - `trials.csv.gz` with one row per trial: NCT ID, `sponsor_raw`, `sponsor_class`, category for each rule set, PCD and its type, submit and post dates, the stale flag, the evidence basis ("registry only"), and a legal-duty column fixed at "not determined";
  - `sponsors.csv` with counts per raw lead-sponsor string;
  - a `manifest.json` with method version, data timestamp, code SHA and licence.

  Pool `INDIV` and person-named sponsors into one unnamed bucket in both files (D8; detection is `class = INDIV` plus responsible-party investigator equal to lead sponsor, critique.md gap 8). Data licence per D12. Sponsor names are present in the downloads but not ranked or featured on pages. This counts as naming, so confirm with D7 whether downloads wait for the gate. Rejected: Parquet in v1 (adds a pyarrow dependency for no user need yet).
- Files and commands: `src/trial_results_tracker/export.py`, `render.py` (download links and licence line), `tests/test_export.py`.
- Done when: merged on main with `mise run check` green, plus the deployed site links both files with the manifest, a test proves no `INDIV` sponsor name appears in either file, and every row carries the evidence basis and data date.
- Blocked by decision: 7, 8, 12

### T10. Curate a sponsor alias table seeded from ROR
- Depends on: T9
- Problem and direction: 44,409 distinct raw lead-sponsor strings exist and only 2,082 have 30 or more interventional trials (engineering.md, own measurement). Raw strings would split institutions such as "Uppsala Universitet" and "Uppsala University" ([CTIS preprint](https://doi.org/10.64898/2026.04.03.26350111)). Add `sponsors/aliases.csv`, committed and reviewable, with columns `sponsor_raw, sponsor_id, ror_id, match_method, reviewed_by, reviewed_on`. A script `mise run sponsors:seed` proposes ROR matches using only `chosen: true` ([ROR matching](https://ror.readme.io/docs/matching); ROR data CC0, [FAQ](https://ror.org/about/faqs/)) for raw strings above the D6 threshold. Proposals land unreviewed, and only reviewed rows are used. Do not roll up parents and children (D6). Rejected: trusting ROR scores (ROR advises against it) and the EU tracker's private spreadsheet (not reviewable).
- Files and commands: `sponsors/aliases.csv`, `src/trial_results_tracker/sponsors.py` (pure lookup), `scripts` entry in `__main__.py` (`sponsors-seed`), `mise.toml` task, `tests/test_sponsors.py`.
- Done when: merged on main with `mise run check` green, plus every sponsor above the ranking threshold has a reviewed row, `match_method` is set on every row, and an unreviewed row is provably ignored by a test.
- Blocked by decision: 6

### T11. Draw and score a validation sample
- Depends on: T6
- Problem and direction: Naming institutions needs measured accuracy. TranspariMED found errors in at least 9 of 38 trials at one sponsor ([TranspariMED](https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results)). Add `validate sample` to draw a seeded, stratified random sample per category (size per D14) into a coding CSV with a link to each live registry page. Add `validate score` to read the coders' CSVs and compute per-category agreement with Wilson CIs and inter-coder agreement. Results go in `docs/validation/<method>-<snapshot>.md` and are linked from the methodology page. The coding happens outside the repo; only the sample definition and the scores are committed.
- Files and commands: `src/trial_results_tracker/validate.py`, `docs/validation/`, `tests/test_validate.py` (seeded sampling is deterministic; scoring on a toy table).
- Done when: merged on main with `mise run check` green, plus the same seed and snapshot reproduce the same sample, and one completed two-coder round for v1.0 is published with per-category agreement.
- Blocked by decision: 14

### T12. Publish the named sponsor league table, sponsor pages and corrections process
- Depends on: T7, T10, T11
- Problem and direction: Naming institutions is the point of the tracker (AGENTS.md rule 1), but only after the gate. Rank reviewed sponsors with at least the D6 number of due trials. Order by point estimate and show the CI, and break ties alphabetically with a visible tie marker (critique.md gap 9). Each sponsor gets a static page listing its due-not-reported trials, linked to the registry. Put the stale-status and inconsistent trials in a separate "check your registry record" list. Add the right-of-reply process:
  - a contact address;
  - `CORRECTIONS.md` as a public log;
  - a GitHub issue template for disputes;
  - a per-trial dispute note that never deletes data.

  Also add a methods line that points legal-compliance readers to the Bennett trackers ([FDAAA](https://fdaaa.trialstracker.net/), [EU](https://eu.trialstracker.net/)). Rejected: pages for all 44k raw strings (they exceed Cloudflare's 20k-file limit, [limits](https://developers.cloudflare.com/pages/platform/limits/)) and roll-ups.
- Files and commands: `render.py`, `site/templates/sponsor.html`, `CORRECTIONS.md`, `.github/ISSUE_TEMPLATE/correction.yml`, `tests/test_render_sponsors.py`.
- Done when: merged on main with `mise run check` green, plus the lawyer consult is recorded as done in `docs/` (date only, no advice text), the T11 validation for this method version is linked, the deployed league table shows only sponsors above threshold with CIs, and no `INDIV` sponsor appears.
- Blocked by decision: 6, 7, 11

### T13. Add a US "probable ACT" legal-duty column
- Depends on: T9
- Problem and direction: The legal-duty axis exists but always reads "not determined" (AGENTS.md rule 2). Infer "probable ACT" from `isFdaRegulatedDrug`/`isFdaRegulatedDevice`, phase, study type and dates, following 42 CFR 11.10's definition ([11.10](https://www.law.cornell.edu/cfr/text/42/11.10)) and the FDAAA tracker's MIT code ([repo](https://github.com/ebmdatalab/clinicaltrials-act-tracker)). Its current pACT logic has not been re-checked against 11.10 (critique.md gap 12); do that check as part of this task. Certified delays (`dispFirstSubmitDate`) are not yet due, up to the 11.44(b)/(c) backstop ([11.44](https://www.law.cornell.edu/cfr/text/42/11.44)). Label the column "appears overdue under FDAAA, absent an unpublished extension". The only "violation" wording allowed is a quote of CT.gov's `fdaaa801Violation` flag, attributed to FDA. Add static notes that UK duties start for trials ending on or after 28 Apr 2026 ([SI 2025/538](https://www.legislation.gov.uk/uksi/2025/538/made)) and that EU dates need CTIS. Never merge this column into the WHO categories.
- Files and commands: `src/trial_results_tracker/legal_us.py` (pure), `export.py`, `render.py`, `tests/test_legal_us.py`.
- Done when: merged on main with `mise run check` green, plus each 11.10 criterion has a test, the WHO category of every trial is unchanged by this task (asserted on the fixture snapshot), and the site's wording contains no "breach" or "illegal".
- Blocked by decision: 15

### T14. Add a "possible publication" secondary measure
- Depends on: T9
- Problem and direction: Registry-only counts miss results published in journals ([TranspariMED](https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results); Nilsonne et al. found more reporting once publications were searched, [JCE 2025](https://doi.org/10.1016/j.jclinepi.2025.111710)). Per D13, link due-not-reported trials to candidate publications by exact NCT-ID mention in PubMed/Europe PMC metadata, and cache the results in the release as `publications.csv.gz` with method and query date. Show "possible publication found" per trial and as a separate share. It never changes the registry headline (the WHO standard is registry posting). Rejected for this task: TrialScout in the headline (specificity 81.2% means false positives, [JCE 2026](https://doi.org/10.1016/j.jclinepi.2026.112484)) and Trials to Publications (no documented API; licence **[unverified]**, [PMC9006700](https://pmc.ncbi.nlm.nih.gov/articles/9006700)).
- Files and commands: `src/trial_results_tracker/publications.py`, `fetch` extension or a `link-publications` subcommand, `refresh.yml` step, `export.py`, `tests/test_publications.py` (recorded fixtures, no network).
- Done when: merged on main with `mise run check` green, plus the headline numbers are byte-identical with and without the publications file (asserted by a test), every link carries its method and query date, and the site states the evidence basis ("registry plus NCT-ID publication search") wherever the secondary measure appears.
- Blocked by decision: 13

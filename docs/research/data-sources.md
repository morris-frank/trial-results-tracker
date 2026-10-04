---
date: 2026-10-04
area: Data sources and access
---

## Question

Which registries and datasets can feed trial-results-tracker, how exactly do we get the data, and which fields are needed to reproduce the Keestra et al. 2021 categories (no reporting requirement, due-not-reported, due-reported-in-time, due-reported-late, completed-not-due, ongoing, inconsistent data)? Recommend a v1 source and a v2 extension.

Probes marked "observed 2026-10-04" were run live against the endpoint on that date; they show behaviour, not a documented contract.

## Findings

### 1. ClinicalTrials.gov API v2 (primary candidate)

**Status and endpoints**
- `GET https://clinicaltrials.gov/api/v2/version` returned `apiVersion 2.0.5`, `dataTimestamp 2026-10-02T09:00:04` (observed 2026-10-04). https://clinicaltrials.gov/api/v2/version
- OpenAPI spec lists these paths: `/studies`, `/studies/{nctId}`, `/studies/metadata`, `/studies/search-areas`, `/studies/enums`, `/stats/size`, `/stats/field/values`, `/stats/field/sizes`, `/version`. https://clinicaltrials.gov/api/oas/v2
- No authentication is needed for any call made here (observed 2026-10-04).

**Paging**
- `/studies` paginates with a `nextPageToken`, which goes back in as `pageToken`. Each later request must keep the same parameters, except `countTotal`, `pageSize` and `pageToken`. The last page carries no token. https://clinicaltrials.gov/api/oas/v2
- `pageSize` defaults to 10 and is "coerced down to 1,000, if greater than that". https://clinicaltrials.gov/api/oas/v2
- `countTotal=true` returns `totalCount` on the first page (CSV: `x-total-count` header). https://clinicaltrials.gov/api/oas/v2
- Formats: `json` (one study per line) or `csv` for `/studies`. `/studies/{nctId}` also offers `json.zip`, `fhir.json` and `ris`. `fields=` limits the response to named fields; `filter.advanced` accepts Essie `AREA[...]` expressions. https://clinicaltrials.gov/api/oas/v2
- Scale: `/stats/size` reported 605,599 studies with an average JSON size of 17,301 bytes, so roughly 10.5 GB uncompressed for the full registry (derived). Filtering on `AREA[StudyType]INTERVENTIONAL` returned 462,154 studies; interventional plus `OverallStatus` COMPLETED or TERMINATED returned 288,935; interventional with `HasResults` true returned 75,647 (all observed 2026-10-04). https://clinicaltrials.gov/api/v2/stats/size
- At 1,000 studies per page, the 462k interventional studies take about 463 requests if only the needed `fields` are requested (derived).

**Rate limits**
- The OpenAPI spec documents no rate limit. https://clinicaltrials.gov/api/oas/v2
- Third-party documentation puts the limit at about 50 requests per minute per IP. [unverified — not found on an official NLM page; the official docs pages are JS-rendered and could not be read] https://cdn.jsdelivr.net/npm/@saibolla/ada@0.1.3/skills/clinicaltrials-database/references/api_reference.md

**Bulk download**
- `GET https://clinicaltrials.gov/api/v2/studies/download?format=json.zip` (and the `/api/int/...` variant used by the website) returns `application/zip` named `ctg-studies.json.zip` (observed 2026-10-04). The OpenAPI spec does not list this path, so treat it as unstable. [unverified as a documented contract] https://clinicaltrials.gov/data-api/how-download-study-records
- The legacy "classic" XML API, which the Keestra tracker code read (`required_header/download_date`, `primary_completion_date`, `results_first_submitted`), has been replaced by v2. [unverified retirement date] https://clinicaltrials.gov/data-api/about-api/api-migration , https://github.com/LeeSean96/GlobalHealthRanking/blob/master/src/ClinicalTrialsTracker/raw_data_to_clinical_trial_v1.py

**Fields needed** (piece names from `/studies/metadata`, observed 2026-10-04; https://clinicaltrials.gov/api/v2/studies/metadata)

| Need | v2 field path | Notes |
|---|---|---|
| Trial ID | `protocolSection.identificationModule.nctId` | |
| Interventional only | `protocolSection.designModule.studyType` | enum includes INTERVENTIONAL |
| Overall status | `protocolSection.statusModule.overallStatus` | Enum: ACTIVE_NOT_RECRUITING, COMPLETED, ENROLLING_BY_INVITATION, NOT_YET_RECRUITING, RECRUITING, SUSPENDED, TERMINATED, WITHDRAWN, plus expanded-access values (AVAILABLE, NO_LONGER_AVAILABLE, TEMPORARILY_NOT_AVAILABLE, APPROVED_FOR_MARKETING), WITHHELD and UNKNOWN. https://clinicaltrials.gov/api/v2/studies/enums |
| Status freshness | `statusModule.statusVerifiedDate`, `statusModule.lastUpdatePostDateStruct.date` | Needed to detect stale status (the TranspariMED critique) |
| Primary completion date + type | `statusModule.primaryCompletionDateStruct.{date,type}` | `type` enum is ACTUAL / ESTIMATED (there is no "ANTICIPATED" value in v2). `date` can be a partial date, e.g. `2012-09` (observed) |
| Study completion date | `statusModule.completionDateStruct` | For a sensitivity analysis only |
| Results submitted | `statusModule.resultsFirstSubmitDate` | |
| Results submitted, QC passed | `statusModule.resultsFirstSubmitQcDate` | |
| Results posted | `statusModule.resultsFirstPostDateStruct.date` | |
| Has results | `hasResults` | Defined as `Present(ResultsFirstSubmitDate)` in metadata, so it is true on submission, not on posting |
| QC-pending / returned results | `annotationSection.annotationModule.unpostedAnnotation.unpostedEvents[]{type,date}` and `unpostedResponsibleParty` | Event enum RESET / RELEASE / UNRELEASE. 9,365 studies carry at least one RESET event (observed). Example NCT01916382: RELEASE then RESET twice, `hasResults=false` |
| Certification / delay | `statusModule.dispFirstSubmitDate` | Delayed-results certification, relevant for legal-duty overlays |
| Why stopped | `statusModule.whyStopped` | Free text (markup) |
| Lead sponsor | `sponsorCollaboratorsModule.leadSponsor.{name,class}` | `class` enum: NIH, FED, OTHER_GOV, INDIV, INDUSTRY, NETWORK, AMBIG, OTHER, UNKNOWN |
| Responsible party | `sponsorCollaboratorsModule.responsibleParty.type` (+ investigator fields) | SPONSOR, PRINCIPAL_INVESTIGATOR, SPONSOR_INVESTIGATOR |
| Collaborators | `sponsorCollaboratorsModule.collaborators[]` | |
| FDAAA flags (optional overlay) | `oversightModule.isFdaRegulatedDrug`, `isFdaRegulatedDevice`, `fdaaa801Violation` | Only needed if a legal-duty view is added |

### 2. AACT (CTTI)

- AACT downloads the full ClinicalTrials.gov registry every day into a PostgreSQL database with "40+ connected tables". Access is by live cloud SQL or by downloading full snapshots, and both need a free account. https://aact.ctti-clinicaltrials.org/
- Earlier documentation said daily pipe-delimited flat files are kept until month end, with a permanent archive made on the first of each month. The redesigned site now returns 404 on those pages, so this is [unverified for the current site]. https://aact.ctti-clinicaltrials.org/pipe_files (404 on 2026-10-04)
- I found no terms of use, licence or dump size on the public pages; the documentation now sits behind login. [unverified] https://aact.ctti-clinicaltrials.org/
- CTTI's public repos `aact-proj` and `aact-sup` are MIT-licensed. That covers the code, not the data. https://github.com/ctti-clinicaltrials/aact-proj
- Column mapping, from earlier versions of the AACT data dictionary [unverified against the current schema, which sits behind login]: `studies.study_type`, `studies.overall_status`, `studies.primary_completion_date`, `studies.primary_completion_date_type`, `studies.results_first_submitted_date`, `studies.results_first_posted_date`, `studies.why_stopped`, `studies.verification_date`; `sponsors.lead_or_collaborator`, `sponsors.agency_class`, `sponsors.name`; `responsible_parties.responsible_party_type`; `pending_results.event`, `pending_results.event_date`.
- Assessment: AACT is a mirror of the same source. It adds SQL convenience and dated snapshots (useful for reconstructing the 2022-08-01 baseline), but it also adds an account dependency and terms we have not read.

### 3. EU CTIS public portal (trials authorised since 31 Jan 2022)

- EMA documents no public API or bulk export for CTIS; the portal offers interactive search. https://euclinicaltrials.eu/ , https://www.ema.europa.eu/en/human-regulatory-overview/research-development/clinical-trials-human-medicines/clinical-trials-information-system
- The portal's own front end calls a JSON backend that works without authentication (observed 2026-10-04; undocumented, so it may change without notice):
  - `POST https://euclinicaltrials.eu/ctis-public-api/search` with body `{"pagination":{"page":N,"size":S},"sort":{...},"searchCriteria":{...}}`. It returned `totalRecords 12549`. List fields: `ctNumber, ctStatus (numeric code), ctTitle, sponsor, sponsorType, trialPhase, trialCountries, decisionDate, decisionDateOverall, lastUpdated, lastPublicationUpdate, resultsFirstReceived (Yes/No), totalNumberEnrolled, ...`
  - `GET https://euclinicaltrials.eu/ctis-public-api/retrieve/{ctNumber}` returns top-level `ctStatus` (e.g. "Ended"), `ctPublicStatusCode`, `startDateEU`, `endDateEU`, `decisionDate`, `publishDate`, `events.trialEvents[].events[]{notificationType,date}` per member state (START_OF_TRIAL, EARLY_TERMINATION, ...), `earlyTerminationReason`, `authorizedApplication.trialGlobalEnd`, `authorizedApplication.authorizedPartI.sponsors`, and `results.summaryResults[]` / `results.laypersonResults[]` with `{status, versionType, isFinalResult, submissionDate}`. Example: 2022-500045-25-00, EARLY_TERMINATION 2024-05-17 in DK, final summary results submitted 2025-12-06.
- The R package `ctrdata` (MIT) already wraps CTIS, EUCTR, CTGOV2 and ISRCTN and is actively maintained (pushed 2026-10-04). It is a useful reference implementation for the undocumented endpoints. https://github.com/rfhb/ctrdata
- Legal deadline under the Clinical Trials Regulation: a summary of results is due within one year of the end of the trial in all Member States concerned (Art. 37(4)). [Article number and wording to be confirmed against the official text] https://eur-lex.europa.eu/eli/reg/2014/536/oj
- Third-party Apify scrapers exist (e.g. https://apify.com/crawlerbros/eu-ctis-scraper). They are not primary sources and should not be dependencies.

### 4. Legacy EudraCT / EU Clinical Trials Register (EUCTR)

- EUCTR covers trials under the old Directive, i.e. those started before CTIS. Summary-results posting there became mandatory for sponsors on 21 July 2014. https://www.ema.europa.eu/lv/news/posting-clinical-trial-summary-results-european-clinical-trials-database-eudract-become-mandatory-sponsors-21-july-2014
- The site has a text download endpoint. `GET https://www.clinicaltrialsregister.eu/ctr-search/rest/download/summary?query=<q>&mode=current_page` returned a plain-text record with sponsor, start date and per-country protocol status, e.g. `PL(Completed) BG(Completed) IT(Completed)` (observed 2026-10-04). Results are on per-trial pages, `https://www.clinicaltrialsregister.eu/ctr-search/trial/{eudract}/results`. https://www.clinicaltrialsregister.eu/ctr-search/trial/2010-022060-13/results
- The Bennett Institute's EU TrialsTracker extraction code (MIT) scrapes EUCTR and is the reference method for EU "due" logic. https://github.com/ebmdatalab/euctr-tracker-code
- Results status is only semi-machine-readable: there is a presence flag plus a results page, and status is per country, not global. A global end date has to be inferred. [inference from observed output]

### 5. ISRCTN

- Offers an XML API at `https://www.isrctn.com/api` (draft docs) and CSV export of search results. Study records are CC-BY; metadata is CC0. https://www.isrctn.com/page/faqs
- `GET https://www.isrctn.com/api/query/format/default?q=&limit=1` reported `totalCount="28804"` (observed 2026-10-04). Per-trial fields relevant to results: `overallEndDate`, `results/publicationStage` (e.g. "Results"), `results/basicReport`, `outputs/output[@outputType="resultsarticle", @dateUploaded]` with an external link. https://www.isrctn.com/api/query/format/default?q=ISRCTN15281137&limit=1
- Results are mostly links to publications, not registry-posted summary results, so "reported" means something different from ClinicalTrials.gov. [inference from the observed record]

### 6. DRKS (German Clinical Trials Register)

- Users can export individual or multiple studies from the public interface. BfArM's help names PDF/HTML/CSV/XML exports; no public API is mentioned. https://bfarm.de/EN/BfArM/Tasks/German-Clinical-Trials-Register/Search-studies/_node.html
- Terms: data from 2025 onward is CC BY 4.0. Older records may need copyright-holder consent before redistribution. Attribution and export date are required. https://bfarm.de/EN/BfArM/Tasks/German-Clinical-Trials-Register/Search-studies/_node.html
- Whether results status is machine-readable is [unverified].

### 7. WHO ICTRP

- The WHO Trial Registration Data Set includes Summary Results (item 33, with a date of first results posting) and an IPD sharing statement. https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set
- Data can be downloaded free as CSV or XML from the Search Portal (https://trialsearch.who.int/). Terms: attribute "WHO ICTRP"; **no use "for marketing, promotional or commercial purposes"**; keep the data current. No API is documented. https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set/downloading-records-from-the-ictrp-database
- Results fields are only as complete as each source registry. [unverified per registry]

### 8. What the predecessor actually computed

- Keestra/UAEM code: `REPORTING_THRESHOLD = 365 + 30` days. `primary_completion_date` (any type) is measured against the download date. `results_reported` comes from the presence of results, with `results_first_submitted` as the results date (submitted, not posted). Withdrawn or suspended means no reporting requirement. Completed or terminated plus over threshold means "due". Recruiting-type statuses with a future date mean "ongoing". Everything else, including UNKNOWN status, is "inconsistent data". https://github.com/LeeSean96/GlobalHealthRanking/blob/master/src/ClinicalTrialsTracker/model/clinical_trial.py , https://github.com/LeeSean96/GlobalHealthRanking/blob/master/src/ClinicalTrialsTracker/definitions.py
- The code's category enum has a single "Due and reported". The in-time/late split comes from `time_delay = results_date − completion_date`. https://github.com/LeeSean96/GlobalHealthRanking/blob/master/src/ClinicalTrialsTracker/model/enum/category.py

## Recommendation

**v1: ClinicalTrials.gov API v2, called directly, as a weekly snapshot.** Run the paged `/studies` query with `filter.advanced=AREA[StudyType]INTERVENTIONAL`, `pageSize=1000`, and only the fields in the table above, then save each run as a dated, immutable Parquet/JSONL snapshot so every number has provenance. That is about 463 requests per run. Keep `studies/download?format=json.zip` as a fallback only, because it is undocumented. Skip AACT for v1: it adds an account and unread terms, and all the needed fields are in v2.

Classification rules for v1 (`as_of` = snapshot date, `pcd` = `primaryCompletionDateStruct.date`; a partial date is resolved to the last day of its month, per Decision 4):

| Category | Rule |
|---|---|
| No reporting requirement | `overallStatus` in {WITHDRAWN, SUSPENDED} |
| Due, reported in time | status in {COMPLETED, TERMINATED} and `as_of − pcd > 395 d` and results date present and `results date − pcd ≤ 365 d` (results date per Decision 1) |
| Due, reported late | same, but `results date − pcd > 365 d` |
| Due, not reported | status in {COMPLETED, TERMINATED} and `as_of − pcd > 395 d` and no results date. Flag separately when `unpostedEvents` exist (submitted but in QC or returned) |
| Completed, not due | status in {COMPLETED, TERMINATED} and `as_of − pcd ≤ 395 d` |
| Ongoing | status in {NOT_YET_RECRUITING, RECRUITING, ENROLLING_BY_INVITATION, ACTIVE_NOT_RECRUITING} and `pcd` in the future (Keestra allows a 30-day tolerance) |
| Inconsistent data | everything else: UNKNOWN status, missing `pcd`, ongoing status with a past `pcd`, COMPLETED with `pcd.type = ESTIMATED`, WITHHELD / expanded-access values |

Carry `leadSponsor.name/class`, `responsibleParty.type`, `collaborators`, `whyStopped`, `statusVerifiedDate` and `lastUpdatePostDate` on every row, so sponsor rollups and stale-status flags need no re-fetch.

**v2: add EU CTIS, then EUCTR.**
- CTIS through the portal's `ctis-public-api` search/retrieve endpoints, rate-limited and cached. "Due" = 12 months after `endDateEU`; "reported" = `results.summaryResults[]` with `isFinalResult` true and its `submissionDate`.
- EUCTR through the text-download endpoint plus results pages, following the EU TrialsTracker method.
- Use `ctrdata` as the cross-check implementation.
- ISRCTN (API, CC-BY/CC0) is a cheap third source but measures publication rather than registry posting. Keep it as a separate indicator, not merged into the same categories.
- Do not use ICTRP as an ingestion source while its non-commercial clause is unresolved (Decision 6). DRKS waits until its export is verified.

## Open decisions

1. **Which date counts as "reported"?** Options: (a) `resultsFirstSubmitDate`, as Keestra did; (b) `resultsFirstPostDate`, the WHO "posted on registry" reading; (c) submitted, with QC-pending shown as its own state. **Recommend (c)**, publishing (a) and (b) as a sensitivity toggle so the result is comparable to Keestra.
2. **Which sponsor gets the trial?** Options: (a) lead sponsor only, as Keestra did; (b) responsible party; (c) lead sponsor plus a collaborator view. **Recommend (a) for the headline ranking**, with (c) as a secondary view. Sponsor name normalisation (free text, many variants) is a separate decision with real effort behind it.
3. **How to treat stale statuses** (UNKNOWN, or ongoing with a past `pcd`, the TranspariMED critique)? Options: (a) count them as inconsistent, as Keestra did; (b) treat them as due when `pcd` + 395 d has passed; (c) show them separately with `statusVerifiedDate`. **Recommend (c)**.
4. **Partial dates (YYYY-MM):** resolve to the first or the last day of the month? **Recommend the last day** (conservative toward sponsors), and document it.
5. **Undocumented endpoints** (CT.gov bulk zip, CTIS `ctis-public-api`): do we accept the breakage risk? Options: (a) use them with snapshot caching and contract tests; (b) only documented paths, so v1 has no CTIS; (c) ask EMA for official access. **Recommend (a) plus (c) in parallel.**
6. **WHO ICTRP non-commercial clause:** does a free public tracker count as non-commercial, and does that change if Soilytix or any sponsor is ever involved? **Recommend not ingesting ICTRP until a human reads the terms.** I am not giving legal advice here.
7. **AACT for historical baselines:** reconstruct the 2022-08-01 state from AACT monthly archives (needs an account and acceptance of terms) or start the time series at the first own snapshot? **Recommend starting fresh**, and opening an AACT account only if a 2022 comparison is wanted.
8. **Snapshot cadence and storage:** daily, weekly or monthly; committed to the repo or stored as external release assets? **Recommend weekly snapshots kept as GitHub release assets**, with only aggregates in the deployed site.

## Sources

- ClinicalTrials.gov API v2 OpenAPI spec — https://clinicaltrials.gov/api/oas/v2
- ClinicalTrials.gov API version / metadata / enums / stats — https://clinicaltrials.gov/api/v2/version , https://clinicaltrials.gov/api/v2/studies/metadata , https://clinicaltrials.gov/api/v2/studies/enums , https://clinicaltrials.gov/api/v2/stats/size
- ClinicalTrials.gov download and migration docs (JS-rendered, not readable here) — https://clinicaltrials.gov/data-api/how-download-study-records , https://clinicaltrials.gov/data-api/about-api/api-migration
- Third-party CT.gov rate-limit note [unverified] — https://cdn.jsdelivr.net/npm/@saibolla/ada@0.1.3/skills/clinicaltrials-database/references/api_reference.md
- AACT — https://aact.ctti-clinicaltrials.org/ ; CTTI repos — https://github.com/ctti-clinicaltrials/aact-proj
- CTIS portal — https://euclinicaltrials.eu/ ; EMA CTIS page — https://www.ema.europa.eu/en/human-regulatory-overview/research-development/clinical-trials-human-medicines/clinical-trials-information-system
- Regulation (EU) No 536/2014 — https://eur-lex.europa.eu/eli/reg/2014/536/oj
- EMA, EudraCT results mandatory from 21 July 2014 — https://www.ema.europa.eu/lv/news/posting-clinical-trial-summary-results-european-clinical-trials-database-eudract-become-mandatory-sponsors-21-july-2014
- EU Clinical Trials Register — https://www.clinicaltrialsregister.eu/ctr-search/search
- EU TrialsTracker code — https://github.com/ebmdatalab/euctr-tracker-code ; FDAAA TrialsTracker code — https://github.com/ebmdatalab/clinicaltrials-act-tracker
- ctrdata — https://github.com/rfhb/ctrdata
- ISRCTN FAQ and API — https://www.isrctn.com/page/faqs , https://www.isrctn.com/api
- DRKS / BfArM search and terms — https://bfarm.de/EN/BfArM/Tasks/German-Clinical-Trials-Register/Search-studies/_node.html
- WHO TRDS — https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set ; ICTRP download terms — https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set/downloading-records-from-the-ictrp-database ; ICTRP Search Portal — https://trialsearch.who.int/
- Keestra/UAEM tracker code — https://github.com/LeeSean96/GlobalHealthRanking

---
date: 2026-10-04
area: Landscape and reusable work
---

## Question

Is there, as of 2023–2026, a maintained tracker that measures **all** sponsors on ClinicalTrials.gov (or other registries) against the WHO standard (summary results on the registry within 12 months of completion) rather than against a legal duty? What existing code, data and tools can we reuse, who would use a successor to clinical-trials-tracker.com, and which outputs do they actually use? Is the gap real, and what differentiation is worth building?

## Findings

### 1. The predecessor: clinical-trials-tracker.com (Keestra et al. 2021)

- Method and categories as in the brief: Keestra et al., *Trials* 22:385 (2021), https://doi.org/10.1186/s13063-021-05330-5.
- The domain still answers (HTTP 200 on 2026-10-04), but the HTML is a client-rendered shell titled "ClinicalTrialsTracker.Web", which suggests a .NET web front end: https://clinical-trials-tracker.com. That the data froze at 2022-08-01 comes from the brief. I did not check it against the live page, because the content loads by JavaScript [unverified].
- The linked repository `LeeSean96/GlobalHealthRanking` is Python, MIT. It has 14 commits, and its last push was 2020-09-22. The README describes it as a ClinicalTrials.gov extraction tool for UAEM's ranking, with OpenRefine suggested for reconciliation: https://github.com/LeeSean96/GlobalHealthRanking (push date from the GitHub API, `gh api repos/LeeSean96/GlobalHealthRanking`). The repo has no documented sponsor normalisation. I could not tell whether it is the code that runs the live site, since the site's stack looks like .NET [unverified]. **Reuse value: low.** The categories are worth keeping; the code is not.

### 2. Bennett Institute trackers (legal-duty scope, not the WHO standard)

- **FDAAA TrialsTracker** covers only trials that FDAAA 2007 requires to report. Updates stopped after February 2024 and resumed in March 2025, after the team paid down technical debt and moved to the new ClinicalTrials.gov API. Its funding is uncertain ("we plan to seek additional funding"): https://www.bennett.ox.ac.uk/blog/2025/04/the-fdaaa-trialstracker-is-back-online/. On 2026-10-04 the live site showed data dated 2 October 2026. It offers a ranked-sponsors view, CSV download ("Download this data") and per-trial pages: https://fdaaa.trialstracker.net/.
  - Code: `ebmdatalab/clinicaltrials-act-tracker`, MIT, Python/Django with a BigQuery transform. The README says its deployment notes are out of date. Last push 2025-08-07 (GitHub API): https://github.com/ebmdatalab/clinicaltrials-act-tracker.
  - **Reusable:** its logic for classifying due, late and reported trials against registry dates, and its handling of the modernised CT.gov API. **Not reusable as is:** the ACT/pACT applicability filter, which is exactly the legal-duty scope we want to drop.
- **EU TrialsTracker** covers EUCTR trials due under EU rules. The live headline on 2026-10-04 read "78.6%" (18,818 of 23,934 due trials reported): https://eu.trialstracker.net/. The page shows no data date, and I found no CTIS coverage [unverified].
  - Code: `ebmdatalab/euctr-tracker-code`, MIT, Python/Django + Scrapy. Sponsor normalisation is done by hand in a spreadsheet. Last push 2025-04-09: https://github.com/ebmdatalab/euctr-tracker-code.
  - **Reusable:** the sponsor-normalisation approach and the static-JSON front-end pattern. EUCTR closes for new CTD trials as they move to CTIS (transition deadline 31 Jan 2025), so this tracker covers a shrinking legacy population: https://www.ema.europa.eu/en/documents/presentation/presentation-update-ctis-programme-ctis-info-day-may-2025-m-sultani_en.pdf.

### 3. Charité / BIH QUEST clinical-trial transparency dashboard (WHO-like standard, German UMCs only)

- A "Responsible Metrics dashboard for clinical trial transparency" built in R Shiny, licensed **AGPL-3.0**. It has per-UMC pages and a report-card page, and takes its data from IntoValue and from EU TrialsTracker history. Last push 2026-01-06: https://github.com/quest-bih/clinical-dashboard.
- Data: `maia-sh/intovalue-data`, R. GitHub records **no licence** for it. Last push 2026-01-21: https://github.com/maia-sh/intovalue-data. A Zenodo or OSF description states CC-BY 4.0 for the dataset: https://zenodo.org/records/7061742 [unverified that this record is the same dataset].
- A feasibility study of individualised trial-transparency report cards at Charité: https://github.com/quest-bih/tv-ct-transparency/.
- **Scope:** German university medical centres, with IntoValue cohorts linked to publications by hand. It does not cover all sponsors and is not a global feed. **Reuse:** the metric definitions and report-card design. AGPL means any code we copy would make our repo AGPL, so we should reuse ideas and not code.

### 4. TranspariMED, UAEM and campaign reports (periodic, not maintained trackers)

- TranspariMED publishes one-off league-table reports, for example the Nordic report of Feb 2024 (475 unreported trials). Its "Metascience fail" post found that at Rigshospitalet some "unreported" trials had results that had been missed, or were stale registry entries (cancelled trials still open, or trials not run by the institution): https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results.
- UAEM ran university rankings and FOI-based policy report cards. Examples: Dutch universities 2019 (https://www.transparimed.org/single-post/2019/10/31/dutch-universities-violate-clinical-trial-transparency-rules-on-a-large-scale), Danish universities 2018 (https://cphpost.dk/2018-09-14/news/danish-universities-urged-to-report-their-clinical-trial-results) and FOI requests for the UAEM Global Health Ranking (https://www.whatdotheyknow.com/request/clinical_trial_transparency_for_35). I found no 2023–2026 UAEM ranking update [unverified].
- Nilsonne et al. 2025, *J Clin Epidemiol* 181, looked at Nordic academic trials 2016–2019, with a manual publication search. Only 51.7% had reported two years after completion, and the median time to reporting was 690 days. Secondary coverage: https://www.researchprofessionalnews.com/?p=525115 and https://mdedge.com/content/ghost-research-haunting-nordic-medical-trials. I found no public dashboard or code for this study [unverified].
- CTIS. The Bruckner et al. 2026 preprint "Assessing Compliance with Reporting Requirements in European Phase II–IV Clinical Trials" found that 116 of the first 234 trials due on CTIS reported on time: https://www.clinicalleader.com/doc/under-half-of-ctis-trials-met-results-reporting-requirements-0001. BUKO Pharma-Kampagne published a German CTIS audit in June 2026: https://bukopharma.de/wp-content/uploads/2026/06/CTIS-legal-violations-in-Germany_2026.pdf. EMA's network replied to an NGO letter: https://www.ema.europa.eu/en/documents/other/joint-response-european-medicines-regulatory-network-letter-health-action-international-other-health-groups-missing-clinical-trial-results-ctis_en.pdf. These are audits. None of them is a maintained tracker.

### 5. Regulators and funders that publish their own monitoring

- UK HRA publishes yearly transparency data. For the first time it now includes whether trials that closed in 2023 posted summary results on a registry within 12 months, which is the WHO standard. The data is self-reported to the HRA and covers UK-approved studies: https://www.hra.nhs.uk/about-us/news-updates/new-research-transparency-data-on-uk-clinical-trials-published/ and https://www.hra.nhs.uk/planning-and-improving-research/policies-standards-legislation/research-transparency/hras-role-research-transparency/transparency-data-reports/.
- WHO Joint Statement (2017). Funders commit to results on the registry within 12 months, and to "monitor registration and endorse the development of systems to monitor results reporting", with public outputs: https://www.who.int/news/item/18-05-2017-joint-statement-on-registration. These funders are natural users of a WHO-standard tracker that runs across all sponsors.

### 6. Linkage tools and datasets (inputs, not trackers)

- **TrialScout** uses an LLM to match CT.gov trials to PubMed results publications. It is a medRxiv preprint from March 2026 by authors at Karolinska, Bern and Oxford: https://www.medrxiv.org/content/10.64898/2026.03.15.26348383v1.full.pdf. The *J Clin Epidemiol* publication exists (von Schreeb et al., doi 10.1016/j.jclinepi.2026.112484, Crossref checked 2026-10-04); the 92.5% sensitivity figure is reported in methodology.md from the paper. Code is at https://github.com/lahnstrom/trialscout under MIT (GitHub licence field, 2026-10-04); it is a self-hosted tool, and no hosted public API was found [unverified]. (Corrected 2026-10-04, see critique.md.)
- **Trials to Publications** is a free web tool that ranks candidate PubMed articles for an NCT ID with a probability score. It takes batch uploads of up to 10,000 trials, and its recall was extended to NCT mentions in the full text of PMC, Europe PMC and OpenAlex: https://www.medrxiv.org/content/10.1101/2025.06.09.25329285 and https://www.transparimed.org/single-post/clinical-trials-to-publications-search-tool. Its licence and terms for programmatic use are [unverified].
- **AACT (CTTI)** is a relational copy of ClinicalTrials.gov, refreshed daily, with source code on GitHub and static database downloads: https://ctti-clinicaltrials.org/?p=2178. It is a strong candidate to replace scraping. Its licence terms are [unverified].
- **ScanMedicine** (NIHR Innovation Observatory) searches across about 11 registries. It is a search tool, not a compliance tracker, and its beta launched in 2021: https://www.newcastlehelix.com/post/new-innovative-searchable-database-of-global-clinical-trials.

### 7. Who uses these, and which outputs they use

- **Campaigners** (TranspariMED, UAEM, BUKO, HAI) use league tables by institution and named lists of unreported trials for advocacy and press. Sources: the TranspariMED and BUKO links above.
- **Universities and UMCs** use per-institution pages and individual report cards that list trials to fix. The QUEST dashboard has a `report_card_page.R` and per-UMC pages, and the Charité feasibility study tested report cards: https://github.com/quest-bih/clinical-dashboard, https://github.com/quest-bih/tv-ct-transparency/.
- **Funders** need ongoing public monitoring of their own portfolio, which is the WHO Joint Statement commitment: https://www.who.int/news/item/18-05-2017-joint-statement-on-registration. Filtering a tracker by funder is not something any surveyed tracker offers [unverified that none does].
- **Journalists and researchers** use CSV downloads and ranked-sponsor views. FDAAA TrialsTracker offers both: https://fdaaa.trialstracker.net/.
- **Regulators** (HRA) publish aggregate numbers but no per-trial lists: https://www.hra.nhs.uk/planning-and-improving-research/policies-standards-legislation/research-transparency/hras-role-research-transparency/transparency-data-reports/.

### 8. Gap assessment

- I found **no maintained tracker** that measures all sponsors on ClinicalTrials.gov against the WHO 12-month standard regardless of legal duty. Bennett covers legal duty only (FDAAA, EUCTR). QUEST is WHO-like but limited to German UMCs. HRA is UK-only and self-reported. The others are one-off audits. This rests on the searches above, and an absence of evidence is not proof [unverified that no such tracker exists].
- One known weakness of all registry-only "unreported" counts is that they can be wrong in either direction. Stale registry status inflates them, and results published in journals are missed (TranspariMED "Metascience fail", link above).

## Recommendation

The gap is real but narrow. The differentiation is in **measurement quality, not coverage alone**. Build a WHO-standard, all-sponsor ClinicalTrials.gov tracker with these properties:

1. **Ingestion:** the CT.gov API v2 or AACT, not scraping. Follow Bennett's 2025 rebuild as the model.
2. **Two measures for every trial**, kept separate: (a) *registry summary results* under the WHO 12-month rule, as the primary measure that Keestra's categories keep; (b) *any public results*, meaning registry or a linked publication found through Trials to Publications-style or TrialScout-style linkage, with the confidence and method of each link shown. This answers the "Metascience fail" critique without blurring the WHO standard.
3. **A data-quality flag** for likely stale registry status (for example "Recruiting" long after the expected completion date), shown apart from "not reported".
4. **Outputs users already use:** sponsor league tables, per-institution pages with a list of trials to fix, CSV/Parquet downloads of the whole dataset, and a "last updated" stamp on every page.
5. **Licences:** reuse ideas from MIT Bennett code (MIT code may be copied with attribution). Do not copy AGPL QUEST code. Release our own code as MIT and the data under CC-BY 4.0 (to be decided, see below).

Leave CTIS, EUCTR and the other registries out of v1, and do not overlap with the Bennett FDAAA tracker's legal-duty framing. In the methods page, point readers to that tracker for questions about legal compliance.

## Open decisions

1. **Primary metric.** Options: (a) WHO strict, registry results only; (b) registry or publication; (c) both, shown as separate columns. **Recommended: (c)**, with (a) as the headline ranking so the series continues from Keestra.
2. **Publication linkage source.** Options: (a) none in v1; (b) the Trials to Publications tool; (c) TrialScout; (d) our own linkage of NCT IDs in PubMed, Europe PMC and OpenAlex metadata. **Recommended: (a) for the first release, then (d)**, checked against (b) and (c) once their licences and terms are confirmed.
3. **Ingestion source.** Options: (a) the CT.gov API v2 directly; (b) AACT snapshots. **Recommended: (a)** for daily freshness and to depend on fewer upstream parties. Fall back to (b) if API rate limits bite.
4. **Sponsor normalisation.** Options: (a) raw lead-sponsor string; (b) a hand-curated mapping table in the repo, as EU TrialsTracker does; (c) automated linking to ROR. **Recommended: (b) seeded by (c)**, with the mapping public and open to correction.
5. **Scope beyond CT.gov.** Options: (a) CT.gov only; (b) add EUCTR/CTIS; (c) add the WHO ICTRP registries. **Recommended: (a)** for v1. Revisit CTIS after the Bruckner preprint is peer reviewed.
6. **Code and data licence.** Options: (a) MIT code with CC-BY 4.0 data; (b) AGPL code to match QUEST. **Recommended: (a).**
7. **Naming and comparability claims.** Should we present this as a "successor to clinical-trials-tracker.com" (and contact Keestra et al. or UAEM), or as an independent tracker? **Recommended: contact the original authors first.** Until they agree, say "follows the Keestra et al. 2021 method" rather than "successor".
8. **Outreach and right of reply.** Should sponsors get a correction channel before their name appears in league tables? **Recommended: yes.** Add a public corrections issue template and a data-quality flag, so that the "Metascience fail" errors do not repeat.

## Sources

- Keestra et al. 2021, Trials 22:385 — https://doi.org/10.1186/s13063-021-05330-5
- clinical-trials-tracker.com — https://clinical-trials-tracker.com
- GlobalHealthRanking repo — https://github.com/LeeSean96/GlobalHealthRanking
- Bennett: FDAAA TrialsTracker back online (2025) — https://www.bennett.ox.ac.uk/blog/2025/04/the-fdaaa-trialstracker-is-back-online/
- FDAAA TrialsTracker — https://fdaaa.trialstracker.net/
- clinicaltrials-act-tracker repo — https://github.com/ebmdatalab/clinicaltrials-act-tracker
- EU TrialsTracker — https://eu.trialstracker.net/
- euctr-tracker-code repo — https://github.com/ebmdatalab/euctr-tracker-code
- EMA CTIS info day May 2025 — https://www.ema.europa.eu/en/documents/presentation/presentation-update-ctis-programme-ctis-info-day-may-2025-m-sultani_en.pdf
- QUEST clinical-dashboard — https://github.com/quest-bih/clinical-dashboard
- IntoValue data — https://github.com/maia-sh/intovalue-data
- Zenodo record (dataset licence) — https://zenodo.org/records/7061742
- QUEST report-card feasibility study — https://github.com/quest-bih/tv-ct-transparency/
- TranspariMED "Metascience fail" — https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results
- TranspariMED on Dutch universities — https://www.transparimed.org/single-post/2019/10/31/dutch-universities-violate-clinical-trial-transparency-rules-on-a-large-scale
- Copenhagen Post on Danish universities — https://cphpost.dk/2018-09-14/news/danish-universities-urged-to-report-their-clinical-trial-results
- UAEM FOI request — https://www.whatdotheyknow.com/request/clinical_trial_transparency_for_35
- Nilsonne et al. 2025 coverage — https://www.researchprofessionalnews.com/?p=525115 ; https://mdedge.com/content/ghost-research-haunting-nordic-medical-trials
- Bruckner et al. CTIS preprint coverage — https://www.clinicalleader.com/doc/under-half-of-ctis-trials-met-results-reporting-requirements-0001
- BUKO CTIS Germany 2026 — https://bukopharma.de/wp-content/uploads/2026/06/CTIS-legal-violations-in-Germany_2026.pdf
- EMRN response to HAI letter — https://www.ema.europa.eu/en/documents/other/joint-response-european-medicines-regulatory-network-letter-health-action-international-other-health-groups-missing-clinical-trial-results-ctis_en.pdf
- HRA transparency data news — https://www.hra.nhs.uk/about-us/news-updates/new-research-transparency-data-on-uk-clinical-trials-published/
- HRA transparency data reports — https://www.hra.nhs.uk/planning-and-improving-research/policies-standards-legislation/research-transparency/hras-role-research-transparency/transparency-data-reports/
- WHO Joint Statement 2017 — https://www.who.int/news/item/18-05-2017-joint-statement-on-registration
- TrialScout preprint — https://www.medrxiv.org/content/10.64898/2026.03.15.26348383v1.full.pdf
- Trials to Publications recall extension — https://www.medrxiv.org/content/10.1101/2025.06.09.25329285
- TranspariMED on Trials to Publications — https://www.transparimed.org/single-post/clinical-trials-to-publications-search-tool
- AACT (CTTI) — https://ctti-clinicaltrials.org/?p=2178
- ScanMedicine — https://www.newcastlehelix.com/post/new-innovative-searchable-database-of-global-clinical-trials

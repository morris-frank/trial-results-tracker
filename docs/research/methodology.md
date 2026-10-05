---
date: 2026-10-04
area: Methodology and follow-up research
---

## Question

How should "due", "reported" and the result categories be defined so the tracker's numbers survive scrutiny from sponsors, metaresearchers and journalists? What do the existing trackers and studies do on each contested point, and what versioned methodology should v1 ship with?

## Findings

### 1. How the reference methods define "due" and "reported"

| Method | Registry | Clock starts at | Due after | Counts as "reported" | Source |
|---|---|---|---|---|---|
| Keestra et al. 2021 (clinical-trials-tracker.com) | ClinicalTrials.gov | Primary completion date | 395 days (365 + 30-day QC grace) | Tabular summary results on the registry | [PMC8169390](https://europepmc.org/article/PMC/PMC8169390) |
| FDAAA TrialsTracker | ClinicalTrials.gov, applicable trials (ACT/pACT) only | Primary completion date; completion date if PCD missing | 1 year + 30 days | Results submitted, either posted or in QC review | [About](https://fdaaa.trialstracker.net/about/), [Lancet 2020](https://doi.org/10.1016/s0140-6736(19)33220-9) |
| EU TrialsTracker | EUCTR only, no CTIS | "Global end of trial date" | 1 year + 4 weeks | Results on EUCTR | [About](https://eu.trialstracker.net/about) |
| Nilsonne et al. 2025 (Nordic) | EUCTR and/or ClinicalTrials.gov, completed 2016–2019 | "Global completion date" | Separate measures: registry results within 1 year, any results within 2 years | Registry summary results *or* a publication found by manual search (journal articles, preprints) | [J Clin Epidemiol 2025](https://doi.org/10.1016/j.jclinepi.2025.111710) |
| IntoValue / QUEST dashboard | ClinicalTrials.gov + DRKS (publication metric); EUCTR via EU TrialsTracker (registry metric) | Completion date | 2 and 5 years for publication; 12 months for registry | Journal publication or registry summary results | [QUEST dashboard](https://quest-dashboard.charite.de/), [IntoValue 2](https://doi.org/10.1016/j.jclinepi.2021.12.012) |
| Bruckner et al. 2026 (CTIS audit, preprint) | CTIS, Phase II–IV | End of trial date | 12 months adult, 6 months paediatric, unless an extension was granted | "Fully reported" = participant numbers + outcome data for all primary endpoints + lay summary, checked manually | [medRxiv](https://doi.org/10.64898/2026.04.03.26350111) |

The WHO 2017 joint statement sets the norm the Keestra tracker uses: summary results on the registry within 12 months of *primary* study completion. Journal publication has an indicative 24-month target from study completion ([WHO](https://www.who.int/news/item/18-05-2017-joint-statement-on-registration)). The tracker is therefore measuring an ethical norm, not legal compliance. The FDAAA tracker measures the US legal duty, and the CTIS audit measures the EU legal duty.

### 2. Primary completion versus study completion

- The WHO norm and both ClinicalTrials.gov trackers start the clock at primary completion ([WHO](https://www.who.int/news/item/18-05-2017-joint-statement-on-registration), [PMC8169390](https://europepmc.org/article/PMC/PMC8169390), [FDAAA](https://fdaaa.trialstracker.net/about/)).
- The Nordic study and IntoValue use the overall or global completion date ([Nilsonne 2025](https://doi.org/10.1016/j.jclinepi.2025.111710), [QUEST](https://quest-dashboard.charite.de/)), and EU registries only have an end-of-trial date ([EU TrialsTracker](https://eu.trialstracker.net/about)). Those numbers are not directly comparable with a PCD-based tracker.
- ClinicalTrials.gov API v2 exposes both dates, each with `type` ACTUAL or ESTIMATED, as partial dates (month precision is common) ([API metadata](https://clinicaltrials.gov/api/v2/studies/metadata), [enums](https://clinicaltrials.gov/api/v2/studies/enums)).
- Keestra treats a finished trial with *no* primary completion date as "due but not reported" ([PMC8169390](https://europepmc.org/article/PMC/PMC8169390)). That can be challenged: it should be flagged as inconsistent, not counted as overdue.

### 3. Anticipated (ESTIMATED) versus actual dates

- The FDAAA tracker treats an anticipated PCD as binding, because the law makes sponsors responsible for keeping it accurate ([FDAAA](https://fdaaa.trialstracker.net/about/)).
- A COMPLETED or TERMINATED record whose PCD is still ESTIMATED is internally inconsistent. A live API count on 2026-10-04 returned 300 interventional COMPLETED/TERMINATED studies with PCD type ESTIMATED ([query](https://clinicaltrials.gov/api/v2/studies?filter.overallStatus=COMPLETED,TERMINATED&query.term=AREA%5BStudyType%5DINTERVENTIONAL%20AND%20AREA%5BPrimaryCompletionDateType%5DESTIMATED&countTotal=true)). [unverified: whether the `AREA[PrimaryCompletionDateType]` filter captures every such record]

### 4. Results submitted but in QC; submission versus posting date

- The API carries `resultsFirstSubmitDate`, `resultsFirstSubmitQcDate`, `resultsFirstPostDateStruct`, `dispFirstSubmitDate` (certificate of delay / extension request) and `annotationSection.unpostedAnnotation.unpostedEvents` with types RESET, RELEASE and UNRELEASE ([metadata](https://clinicaltrials.gov/api/v2/studies/metadata), [enums](https://clinicaltrials.gov/api/v2/studies/enums)).
- The FDAAA tracker counts submitted results that are in QC as reported, and it times compliance from *submission* ([Lancet 2020](https://doi.org/10.1016/s0140-6736(19)33220-9)). It also has an "Overdue (cancelled results)" state and assumes the full two-year delay when a certificate exists ([FDAAA](https://fdaaa.trialstracker.net/about/)).
- Keestra's text says "posted" and justifies the 30-day grace as QC time ([PMC8169390](https://europepmc.org/article/PMC/PMC8169390)). Its fastest example, NCT01245270, has results submitted 2013-08-23 but first posted 2014-08-15 ([API record](https://clinicaltrials.gov/api/v2/studies/NCT01245270)). The "22 days" it reports therefore matches the submission date, not the posting date. This is my inference from the record; the code was not checked.
- Implication: submission and posting can be a year apart. Which one counts as "reported" can move a trial between in-time, late and unreported, so the choice must be explicit.

### 5. Inactive, never-started and stale-status trials (TranspariMED 2024)

- TranspariMED's review of its own Nordic figures for Rigshospitalet found 5 trials not updated after cancellation, 3 with results the searchers missed, and 1 never run by that institution. Only 14 were confirmed unreported. Its lesson: "always check back with institutions to verify" ([TranspariMED](https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results)).
- ClinicalTrials.gov shows a recruiting, not-yet-recruiting or active record as "Unknown status" if it has not been verified for two years ([ACCC glossary](https://acori-glossary.accc-cancer.org/definition/last-verified)). On 2026-10-04 there were 67,831 interventional UNKNOWN-status studies, against 259,048 COMPLETED and 29,887 TERMINATED ([API query](https://clinicaltrials.gov/api/v2/studies?filter.overallStatus=UNKNOWN&query.term=AREA%5BStudyType%5DINTERVENTIONAL&countTotal=true)). A further 4,351 open-status interventional records had a PCD before 2025-01-01 ([API query](https://clinicaltrials.gov/api/v2/studies?filter.overallStatus=RECRUITING,NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION&query.term=AREA%5BStudyType%5DINTERVENTIONAL%20AND%20AREA%5BPrimaryCompletionDate%5DRANGE%5BMIN,2024-12-31%5D&countTotal=true)).
- Registry status is often wrong: one audit found 31% of trials had an incorrect status or a status update delayed by more than a year ([BMJ Open 2017](https://bmjopen.bmj.com/content/7/10/e017719)).
- Keestra counts UNKNOWN and "past PCD but still ongoing" as "inconsistent data". Among the 30 UK universities that was 687 trials (42%) ([PMC8169390](https://europepmc.org/article/PMC/PMC8169390)). Withdrawn and suspended trials are "no reporting requirement" ([same](https://europepmc.org/article/PMC/PMC8169390)).
- The CTIS audit dropped 19 cancelled trials without enrolment and 24 with approved extensions from its due cohort ([medRxiv](https://doi.org/10.64898/2026.04.03.26350111)). The EU tracker keeps terminated trials as due and has no systematic exemption for withdrawn trials without enrolment ([EU TrialsTracker](https://eu.trialstracker.net/about)).

### 6. Attribution: lead sponsor, responsible party, collaborator

- ClinicalTrials.gov records `leadSponsor.name/class`, `collaborators[]`, and `responsibleParty.type` (SPONSOR, PRINCIPAL_INVESTIGATOR, SPONSOR_INVESTIGATOR) with the investigator's affiliation ([metadata](https://clinicaltrials.gov/api/v2/studies/metadata), [enums](https://clinicaltrials.gov/api/v2/studies/enums)).
- Keestra attributes to the lead sponsor ([PMC8169390](https://europepmc.org/article/PMC/PMC8169390)). IntoValue and QUEST attribute a trial to an institution if it is the responsible party or sponsor, *or* if the PI is affiliated with it ([QUEST](https://quest-dashboard.charite.de/)), and they keep lead and facility affiliation tables ([intovalue-data](https://github.com/maia-sh/intovalue-data)). The Nordic study includes trials "led by" a university or hospital ([Nilsonne 2025](https://doi.org/10.1016/j.jclinepi.2025.111710)). [unverified: the exact Nordic attribution rule; the protocol at osf.io/wua3r could not be retrieved]
- TranspariMED found a trial registered under an institution that never ran it ([TranspariMED](https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results)). Attribution errors are real, not theoretical.

### 7. Sponsor-name normalisation and grouping

- The EU TrialsTracker reconciles mergers, splits and renames by hand, does not double-count child organisations in parent totals, and lists only sponsors with 50 or more trials on its homepage ([EU TrialsTracker](https://eu.trialstracker.net/about)). The FDAAA tracker's About page does not document its approach ([FDAAA](https://fdaaa.trialstracker.net/about/)).
- The CTIS audit notes variant spellings such as "Uppsala Universitet" and "Uppsala University", and does no sponsor-level analysis because the cohort is small ([medRxiv](https://doi.org/10.64898/2026.04.03.26350111)).
- ROR's affiliation-matching API returns ranked candidates and a `chosen: true` flag. ROR advises using that flag, not the confidence score ([ROR docs](https://ror.readme.io/docs/matching)). ROR data is CC0 ([ROR FAQ](https://ror.org/about/faqs/)).
- Mapping CT.gov lead-sponsor strings to ROR has no published accuracy figure. [unverified: precision and recall of ROR matching on CT.gov sponsor strings]

### 8. Publication linkage

- **TrialScout**: an LLM (gpt-5.1) matches CT.gov trials to PubMed results. Against human coders: sensitivity 92.5%, specificity 81.2%. In 200 disagreements, human error was the cause 61.5% of the time. On a random 9,600 completed or terminated trials it found publications for 63.6% ([J Clin Epidemiol 2026](https://doi.org/10.1016/j.jclinepi.2026.112484), [medRxiv preprint](https://doi.org/10.64898/2026.03.15.26348383)). Cost was about USD 0.043 per trial ([preprint](https://www.medrxiv.org/content/10.64898/2026.03.15.26348383v1.full)). Code and validation data are at [github.com/lahnstrom/trialscout](https://github.com/lahnstrom/trialscout) under MIT (GitHub licence field: MIT; last push 2026-07-29). The repo is a Node.js tool with a `GET /api/trials/{NCT}` server you run yourself. The preprint mentions a web interface at metaresearch.se/trialscout. [unverified: whether that hosted interface offers a public bulk API or terms of use] The first author is listed as Ahnström on medRxiv and von Schreeb in J Clin Epidemiol ([Europe PMC record](https://doi.org/10.1016/j.jclinepi.2026.112484)).
- **Trials to Publications** (Smalheiser & Holt): a logistic-regression model with precision 90.4%, recall 84.6% and AUC 0.95, plus a web interface that takes batches of up to 10,000 NCT IDs. It has no documented API. Code is on Dryad with no licence stated in the article ([PMC9006700](https://pmc.ncbi.nlm.nih.gov/articles/9006700), [Dryad](https://doi.org/10.5061/dryad.sqv9s4n5f)). A 2025 extension adds NCT mentions from full text in PMC, Europe PMC and OpenAlex ([medRxiv](https://www.medrxiv.org/content/10.1101/2025.06.09.25329285)).
- Specificity of about 81% means a fully automatic "published" flag would include false positives. TrialScout's own authors note there is no true gold standard ([JCE abstract](https://doi.org/10.1016/j.jclinepi.2026.112484)).

### 9. Validation sample sizes used by others

- Keestra: manual validation of the tracker is described in Supplementary File 1 ([PMC8169390](https://europepmc.org/article/PMC/PMC8169390)). [unverified: sample size; the supplement was not retrieved]
- Nordic: 2,112 trials, with systematic manual searches for publications ([Nilsonne 2025](https://doi.org/10.1016/j.jclinepi.2025.111710)). The TrialScout paper says at least two independent researchers searched each trial and resolved disagreements by consensus ([preprint](https://www.medrxiv.org/content/10.64898/2026.03.15.26348383v1.full)).
- TrialScout: 5,774 human-coded trials (IntoValue plus Nordic) and a 200-case adjudication of disagreements ([preprint](https://www.medrxiv.org/content/10.64898/2026.03.15.26348383v1.full)).
- CTIS audit: the full due cohort of 234 trials checked by hand. Two people extracted dates, and seven team members checked document content ([medRxiv](https://www.medrxiv.org/content/10.64898/2026.04.03.26350111v1.full)).
- TranspariMED: checking findings back with institutions found errors in at least 9 of 38 trials at one sponsor ([TranspariMED](https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results)).

### 10. Reporting uncertainty

- The Nordic study and the FDAAA study report proportions with 95% CIs, and the FDAAA study also reports Kaplan–Meier time-to-report ([Nilsonne 2025](https://doi.org/10.1016/j.jclinepi.2025.111710), [Lancet 2020](https://doi.org/10.1016/s0140-6736(19)33220-9)).
- The EU tracker uses a minimum-size threshold for its headline league table (50 or more trials) ([EU TrialsTracker](https://eu.trialstracker.net/about)).
- The CTIS audit concludes that new registry results functions "will require quality assurance processes" ([medRxiv](https://doi.org/10.64898/2026.04.03.26350111)).

### 11. Reusable code

| Repo | Licence | Last push | Source |
|---|---|---|---|
| LeeSean96/GlobalHealthRanking (Keestra tracker) | MIT | 2020-09-22 | [GitHub](https://github.com/LeeSean96/GlobalHealthRanking) |
| ebmdatalab/clinicaltrials-act-tracker (FDAAA) | MIT | 2025-08-07 | [GitHub](https://github.com/ebmdatalab/clinicaltrials-act-tracker) |
| ebmdatalab/euctr-tracker-code | MIT | 2025-04-09 | [GitHub](https://github.com/ebmdatalab/euctr-tracker-code) |
| quest-bih/dashboard | AGPL-3.0 | 2026-09-23 | [GitHub](https://github.com/quest-bih/dashboard) |
| quest-bih/IntoValue2 | MIT | 2023-04-14 | [GitHub](https://github.com/quest-bih/IntoValue2) |
| maia-sh/intovalue-data | none declared | 2026-01-21 | [GitHub](https://github.com/maia-sh/intovalue-data) |
| lahnstrom/trialscout | MIT | 2026-07-29 | [GitHub](https://github.com/lahnstrom/trialscout) |

The licence and date columns come from the GitHub API on 2026-10-04. Copying AGPL code into this repo would bring AGPL obligations. intovalue-data has no licence, so its code should not be copied; reusing its data needs a separate check.

## Recommendation

Adopted as methodology v1.0 with D1–D15 resolved as recommended in `docs/plan.md`; the versioned method text is `docs/methodology.md`, which supersedes the list that stood here.

## Open decisions

1. **Reporting date: submission or first posting?**
   - Options: (a) `resultsFirstSubmitDate`, as FDAAA does; (b) `resultsFirstPostDate`, the strict WHO reading of "publicly available"; (c) both, with two headlines.
   - **Recommended: (a) as the headline, with posting shown per trial.** Submission is the sponsor's action, and QC delay sits with the registry.
2. **Comparability with Keestra 2021 versus corrected definitions.**
   - Options: (a) replicate Keestra exactly (suspended exempt; finished trials with no PCD counted as due-not-reported); (b) v1.0 corrections as above, plus a published crosswalk.
   - **Recommended: (b)**, plus a one-off rerun of Keestra's rules on the same snapshot, so readers can see how much the changes move the numbers.
3. **Suspended trials.**
   - Options: (a) no requirement (Keestra); (b) ongoing; (c) due once PCD + 365 has passed.
   - **Recommended: (b).** Suspension is a pause, not an exemption.
4. **Stale open-status and UNKNOWN trials in the headline.**
   - Options: (a) exclude them from the denominator and show them separately; (b) count them as unreported; (c) show both, as a range.
   - **Recommended: (c)**, with (a) as the point estimate.
5. **Attribution unit.**
   - Options: (a) lead sponsor; (b) responsible party; (c) IntoValue-style institution, which also counts PI affiliation.
   - **Recommended: (a) for v1.** (c) needs affiliation matching and manual work outside v1 scope.
6. **Ranking threshold.**
   - Options: 10, 20 or 50 due trials, or no ranking (search only).
   - **Recommended: 20 due trials**, revisited once CI widths on real data are known. The EU tracker uses 50 total trials.
7. **Sponsor grouping depth.**
   - Options: (a) aliases only (spelling variants); (b) also merge hospitals into their universities and subsidiaries into parents.
   - **Recommended: (a).** Roll-ups are judgement calls that sponsors will dispute.
8. **Right of reply before naming sponsors.**
   - Options: (a) publish immediately; (b) publish with a corrections log and contact form; (c) notify ranked sponsors before each release.
   - **Recommended: (b) at launch**, moving to (c) for ranked sponsors if capacity allows. This follows TranspariMED's lesson.
9. **Publication linkage.**
   - Options: (a) none in v1; (b) TrialScout in v1 as a secondary measure; (c) TrialScout feeding the headline.
   - **Recommended: (a) for v1 and (b) for v1.1.** Self-hosted LLM cost is about USD 0.043 per trial, and someone must agree to pay it.
10. **Validation sample size and coders.**
    - Options: 100, 200 or 400 trials per release; one or two coders.
    - **Recommended: 200 trials, two coders.** Someone must commit the hours; nothing in this repo does that yet.
11. **Methodology licence and pre-registration.**
    - Options: (a) document the methods in-repo only; (b) also pre-register v1.0 on OSF before the first public numbers, as the Nordic and CTIS teams did.
    - **Recommended: (b).**

## Sources

- Keestra SM et al. 2021, *Trials* 22:385. https://doi.org/10.1186/s13063-021-05330-5 ; full text https://europepmc.org/article/PMC/PMC8169390
- WHO joint statement on public disclosure of results, 2017. https://www.who.int/news/item/18-05-2017-joint-statement-on-registration
- FDAAA TrialsTracker, About. https://fdaaa.trialstracker.net/about/
- DeVito NJ, Bacon S, Goldacre B. *Lancet* 2020. https://doi.org/10.1016/s0140-6736(19)33220-9
- EU TrialsTracker, About. https://eu.trialstracker.net/about
- Nilsonne G et al. 2025, *J Clin Epidemiol* 181:111710. https://doi.org/10.1016/j.jclinepi.2025.111710 ; preprint https://doi.org/10.1101/2024.02.04.24301363
- Riedel N et al. 2022 (IntoValue 2). https://doi.org/10.1016/j.jclinepi.2021.12.012
- QUEST/Charité dashboard. https://quest-dashboard.charite.de/ ; code https://github.com/quest-bih/dashboard
- IntoValue data. https://github.com/maia-sh/intovalue-data ; https://doi.org/10.5281/zenodo.5141342
- Bruckner T et al. 2026, CTIS compliance preprint. https://doi.org/10.64898/2026.04.03.26350111 ; protocol https://osf.io/sn4j2/
- TrialScout, *J Clin Epidemiol* 2026. https://doi.org/10.1016/j.jclinepi.2026.112484 ; preprint https://doi.org/10.64898/2026.03.15.26348383 ; code https://github.com/lahnstrom/trialscout
- Smalheiser NR, Holt AW, Trials to Publications. https://pmc.ncbi.nlm.nih.gov/articles/9006700 ; Dryad https://doi.org/10.5061/dryad.sqv9s4n5f ; 2025 extension https://www.medrxiv.org/content/10.1101/2025.06.09.25329285
- TranspariMED, "Metascience fail", Nov 2024. https://www.transparimed.org/single-post/metascience-fail-four-lessons-from-inaccurate-data-on-missing-clinical-trial-results
- ClinicalTrials.gov API v2: metadata https://clinicaltrials.gov/api/v2/studies/metadata ; enums https://clinicaltrials.gov/api/v2/studies/enums ; example record https://clinicaltrials.gov/api/v2/studies/NCT01245270
- Last-verified / unknown-status definition. https://acori-glossary.accc-cancer.org/definition/last-verified
- Registry status accuracy, BMJ Open 2017. https://bmjopen.bmj.com/content/7/10/e017719
- ROR affiliation matching https://ror.readme.io/docs/matching ; ROR FAQ (CC0) https://ror.org/about/faqs/
- Code repos: https://github.com/LeeSean96/GlobalHealthRanking ; https://github.com/ebmdatalab/clinicaltrials-act-tracker ; https://github.com/ebmdatalab/euctr-tracker-code ; https://github.com/quest-bih/IntoValue2

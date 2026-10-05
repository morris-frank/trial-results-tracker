---
date: 2026-10-04
area: Critique of the research notes
---

Completeness and skeptic pass over `data-sources.md`, `methodology.md`, `landscape.md`, `legal.md` and `engineering.md`. Each claim below was re-fetched on 2026-10-04. Three clear errors were fixed in place, each marked "Corrected 2026-10-04" in its note.

## Claim checks

| # | Claim (note) | Verdict | Evidence |
|---|---|---|---|
| 1 | CT.gov API v2: `pageSize` coerced down to 1,000; `hasResults` = `Present(ResultsFirstSubmitDate)` (data-sources, engineering) | **Confirmed**, with one caveat. The metadata *description* of `hasResults` says "posted results on public site", but its `sourceType` is `FUNC Present(ResultsFirstSubmitDate)`. Use the submit/post date fields, never `hasResults`, as the "reported" signal. | https://clinicaltrials.gov/api/oas/v2 (line 417 of spec); https://clinicaltrials.gov/api/v2/studies/metadata |
| 2 | Repo licences: GlobalHealthRanking MIT (last push 2020-09-22); TrialScout MIT; QUEST dashboard AGPL-3.0; intovalue-data no licence; clinicaltrials-act-tracker MIT (methodology, landscape, legal) | **Confirmed** in methodology. **Wrong** in landscape, which said no TrialScout licence was found, and in legal, which marked the Keestra licence unverified. Both fixed in place. | `gh api repos/{owner}/{repo}`; https://github.com/lahnstrom/trialscout ; https://github.com/LeeSean96/GlobalHealthRanking |
| 3 | WHO ICTRP download terms: no marketing/promotional/commercial use; attribute "WHO ICTRP"; keep current; show processing date; no WHO name or emblem (data-sources, legal) | **Confirmed** verbatim. | https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set/downloading-records-from-the-ictrp-database |
| 4 | ISRCTN: named free-text fields are CC BY; metadata CC0 for contributions from 1 Jan 2019 (legal; data-sources says "study records CC-BY, metadata CC0") | **Confirmed, but incomplete.** The same terms page also prohibits copying or storing site content "to make or populate a database or publication of any kind", except for an insubstantial part under fair dealing. How that clause sits with the CC0/CC BY grants is unresolved. No CC BY version is stated. data-sources' summary is too loose: pre-2019 metadata is not CC0. | https://www.isrctn.com/page/terms |
| 5 | UK SI 2025/538: in force 28 Apr 2026; reg 25(2) results summary within 12 months of the day after conclusion; reg 25(12) public registry = ICTRP primary/partner/data provider; Phase I deferral of up to 30 months; 10-year cap; Sch 14 para 2(8): reg 25 does not apply to old-rules trials ending before the relevant day, and 25(2)(b) lay summary does not apply to old-rules trials ending on or after it (legal) | **Confirmed.** Reg 1(2) gives commencement as 12 months after making (made 28 Apr 2025). Two additions are missing from legal.md. (a) Sch 14 defines "end of trial date" as the protocol conclusion date, and for multinational trials the end in *all* participating countries, not the PCD. (b) A breach of reg 25(2)(a) is an offence under amended reg 49 and attracts an infringement notice under reg 48. | https://www.legislation.gov.uk/uksi/2025/538/made (XML: /made/data.xml) |
| 6 | EU CTR Art 37(4): summary of results within one year of end of trial in all Member States concerned; the paediatric 6-month rule is not in Art 37 (data-sources, legal) | **Confirmed.** Art 37 makes no mention of paediatric trials or of 6 months. data-sources still marks the article number "to be confirmed"; it can be cleared. | https://www.legislation.gov.uk/eur/2014/536/article/37 |
| 7 | 42 CFR 11.44: results due ≤1 year after PCD (a); certified delay up to 2 years after certification; good-cause extensions (e) (legal) | **(a) and (e) confirmed. The delay claim was wrong in detail and has been fixed.** Initial approval is 11.44(**c**) and a new use is 11.44(**b**). Both give 30 days after approval or withdrawal, with a backstop of 2 years after certification. methodology.md cites the FDAAA tracker's "assumes the full two-year delay" and still matches. | https://www.law.cornell.edu/cfr/text/42/11.44 |
| 8 | Competitors: FDAAA TrialsTracker stopped Feb 2024 and resumed Mar 2025, legal-duty scope only; TrialScout published in J Clin Epidemiol; Nilsonne 2025 JCE 181 (landscape, methodology) | **Confirmed.** Bennett blog states the stop and resume dates, uncertain funding, and the move to the new CT.gov API. Crossref returns TrialScout (von Schreeb et al., JCE, issued 2026-12) and Nilsonne et al. (JCE vol 181). The claim that "no maintained all-sponsor WHO-standard tracker exists" remains an absence-of-evidence claim **[unverified]**. | https://www.bennett.ox.ac.uk/blog/2025/04/the-fdaaa-trialstracker-is-back-online/ ; https://api.crossref.org/works/10.1016/j.jclinepi.2026.112484 ; https://api.crossref.org/works/10.1016/j.jclinepi.2025.111710 |

Additional check that changed a note: Vercel Hobby. legal.md said donations "would need checking". Vercel states "Asking for Donations **does not** fall under commercial usage". Fixed in place. https://vercel.com/docs/limits/fair-use-guidelines

Not re-checked: the current ClinicalTrials.gov terms. The archived 2014 page could not be fetched here (web.archive.org is blocked for this tool), and the live page is JS-rendered. The data-attribution duties in legal.md §1 for CT.gov therefore still rest on an unrefetched archive **[unverified]**.

## Contradictions

1. **"Due" threshold and the in-time cut.** data-sources: due = `as_of − pcd > 395 d`, in time = `results − pcd ≤ 365 d`. methodology: due = PCD + 365 d, with the 395-day grace applied *only* to the in-time/late cut. Keestra's code (per data-sources) uses 395 for due. The two notes give different numbers for the same trial at the boundary. One rule has to be picked.
2. **Suspended trials.** data-sources: no reporting requirement (as Keestra). methodology: ongoing (recommended (b)).
3. **Missing PCD.** data-sources: inconsistent. methodology §2 says Keestra counted it as due-not-reported, which conflicts with data-sources' reading of the same code ("everything else … inconsistent"). methodology also recommends a completion-date fallback (`pcd_fallback`, rec. 2) *and* lists "missing PCD" under inconsistent (rec. 5). That is internally contradictory.
4. **ESTIMATED PCD on finished trials.** data-sources: inconsistent. methodology rec. 3: due requires `type = ACTUAL`, so such trials are never due. FDAAA tracker: an estimated PCD is binding. The notes do not settle it.
5. **Withdrawn / zero-enrolment.** methodology adds "TERMINATED with actual enrolment 0" to no-requirement. data-sources does not, and does not list `enrollmentInfo` among the fields to pull.
6. **Cadence and storage.** data-sources: *weekly* snapshots as release assets. engineering: *nightly* releases `data-YYYY-MM-DD`. landscape: API chosen "for daily freshness".
7. **Thresholds.** Ranking at 20 due trials (methodology); naming at N=5 due trials (legal); static sponsor pages at 30 total trials on raw strings (engineering); EU tracker uses 50. The three notes use different units (due trials vs total trials) as well as different numbers.
8. **Bulk download path.** data-sources: `/api/v2/studies/download?format=json.zip` works. engineering: only `/api/int/studies/download` is cited, as internal. Both agree not to depend on it.
9. **Rate limit.** Both notes rely on different third-party pages, a jsdelivr npm package and a glama.ai mirror, for "~50 req/min". Neither is official, and two secondary copies do not make one primary source.
10. **AACT.** landscape calls it "a strong candidate to replace scraping" and recommends "API v2 or AACT". data-sources, engineering and legal all recommend skipping it for v1.
11. **Ingestion order after v1.** legal: ISRCTN second, CTIS later. data-sources: CTIS then EUCTR, with ISRCTN only as a separate publication-type indicator.
12. **Publication linkage.** methodology: self-hosted TrialScout in v1.1. landscape: our own NCT-ID linkage (d), with TrialScout only as a cross-check.
13. **QUEST dashboard repo.** methodology cites `quest-bih/dashboard` (AGPL, pushed 2026-09-23). landscape cites `quest-bih/clinical-dashboard` (AGPL, pushed 2026-01-06). Both exist and neither has a description, so it is unclear which one is live.
14. **TranspariMED.** legal marks it "not fetched, cited in brief". methodology and landscape fetched and quoted it. legal's [unverified] tag can be dropped.
15. **Data licence vs sources.** landscape recommends CC BY 4.0 for our data. ICTRP forbids commercial use, while CC BY permits it, and ISRCTN's terms bar populating databases. These are compatible only while ICTRP and ISRCTN stay out of the published dataset. No note says so.

## Gaps

1. **Which clock date for UK/EU legal axes.** The WHO axis runs on PCD. UK reg 25 and EU Art 37 run on end of trial (all countries). No note says which CT.gov field approximates the end date (`completionDateStruct`?) or how to label the mismatch.
2. **Applicability by country.** No rule for identifying a "UK CTIMP" or an "EU-CTR" trial from CT.gov fields. Location countries, phase, intervention type and EudraCT secondary IDs are not in the field table.
3. **Cross-registry duplicates.** No dedup strategy for one trial registered on CT.gov, EUCTR/CTIS and ISRCTN (`secondaryIdInfos`), nor for results posted on a different registry than the one scored.
4. **Results posted then removed.** RESET/UNRELEASE semantics are named but not specified. Which event sequence counts as submitted, returned, or cancelled? Does a later posted version override an earlier one?
5. **Snapshot reproducibility.** CT.gov `dataTimestamp` lagged two days, and records are edited retroactively. No note covers whether a re-pull for the same `as_of` should match, or how to version the history of a corrected record.
6. **Partial dates.** Rules exist for PCD. None exist for results dates or for `statusVerifiedDate` (month precision), which feed the stale-status flag.
7. **Sponsor alias table ownership.** Format, location, licence, review workflow and who resolves disputes are all unspecified. 44,409 raw strings were measured, but there is no effort estimate.
8. **Individual-sponsor detection.** legal requires bucketing person-named sponsors beyond `class = INDIV`. No method or field is given (for example responsible-party name equal to lead sponsor).
9. **CI uncertainty for small sponsors.** Wilson CIs are proposed, but there is no rule for ordering the league table (point estimate vs lower bound) or for showing ties.
10. **Keestra baseline comparison.** Decision 7 (data-sources) and history (engineering) defer AACT, yet methodology wants a Keestra-rules rerun "on the same snapshot". It is unclear whether any comparison to the 2022-08-01 numbers is planned, and whether the old site's data can be retrieved at all.
11. **Contact with Keestra/UAEM.** Recommended in landscape, but no owner or channel is given.
12. **Legal-duty axis maintenance.** FDAAA "probable ACT" logic would be re-derived from Bennett's MIT code. No note has checked that code's current pACT rules against 42 CFR 11.10. *Resolved 2026-10-05 (T13): see legal.md section 4, "Re-check of the FDAAA TrialsTracker's pACT logic".*
13. **CT.gov current terms** are not re-verified (see above). AACT terms remain unread.
14. **Failure modes of the nightly job.** Partial pulls, API schema changes (the version moves from 2.0.5) and a guard against publishing a half-classified snapshot are not covered. Contract tests are mentioned only for undocumented endpoints.
15. **Accessibility and i18n** of a page that names institutions, and how the Dutch publisher name and "not Soilytix" statement are displayed. Imprint duty is listed as a lawyer question but has no placeholder in the build.
16. **Who does the 200-trial dual coding per release.** methodology flags this but it is unowned, and it gates naming sponsors (legal rec. 7).

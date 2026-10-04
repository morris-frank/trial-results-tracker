---
date: 2026-10-04
area: Legal, ethical and reputational
---

> Research notes, not legal advice. Each claim has a URL. Anything not checked against a primary text in this session is marked **[unverified]**. The last subsection lists what a lawyer should confirm.

## Question

What legal and ethical limits apply to a public tracker that names institutions for not reporting trial results, when it is run by a private individual in the Netherlands and hosted on Vercel? The questions are:

1. May we republish data from ClinicalTrials.gov, AACT, CTIS/EMA, ISRCTN and ICTRP, and on what terms?
2. What is the GDPR exposure from investigator and contact names, and should we drop them?
3. What are the defamation and accuracy risks of naming institutions (NL/EU and UK), and which practices reduce them?
4. Which legal reporting duties actually exist (FDAAA 801 / 42 CFR Part 11, EU CTR Art 37, UK SI 2025/538), so that "legally overdue" is only applied where a duty exists and is kept separate from "misses the WHO standard"?

## Findings

### 1. Data licences and terms of use

| Source | Reuse permitted? | Conditions that bind us | Status |
|---|---|---|---|
| ClinicalTrials.gov | Yes, free to all requesters | Credit ClinicalTrials.gov as the source. Keep data current. **Show the date the data were processed by ClinicalTrials.gov.** **State every change we made to the data and describe it fully.** Do not claim proprietary rights or present the database as anything other than a US Government database. Do not use extracted email addresses for marketing. Data "carry an international copyright outside the United States", and some data may carry third-party copyright. | Verified against the archived classic-site terms, last reviewed May 2014 ([archive](https://web.archive.org/web/2024/https://classic.clinicaltrials.gov/ct2/about-site/terms-conditions)). The current page ([clinicaltrials.gov/about-site/terms-conditions](https://clinicaltrials.gov/about-site/terms-conditions)) is rendered client-side, so its text could not be extracted. Whether the wording is unchanged is **[unverified]**. |
| AACT (CTTI) | Derived from ClinicalTrials.gov ([aact](https://aact.ctti-clinicaltrials.org/)) | CTTI's general citation policy asks for credit to "Clinical Trials Transformation Initiative" with a link ([CTTI citation policy](https://ctti-clinicaltrials.org/?p=7671)). No AACT-specific licence was found. | AACT licence **[unverified]**. The ClinicalTrials.gov terms still apply to the underlying data. |
| EMA (CTIS, EU CTR register) | Yes, for commercial and non-commercial use | EMA must be credited as the source in every copy. Third-party copyright material is excluded ([EMA legal notice](https://www.ema.europa.eu/en/about-us/legal-notice)). | Whether the legal notice formally covers the CTIS public portal and clinicaltrialsregister.eu is **[unverified]**. Neither had its own terms in what was checked. |
| ISRCTN | Yes | Scientific/lay free-text fields (summary, objectives, interventions, outcomes, basic results, etc.) are **CC BY 4.0** and need attribution. All other content is metadata and needs no attribution. For contributions from 1 Jan 2019 onward, metadata is **CC0** ([ISRCTN terms](https://www.isrctn.com/page/terms)). | Verified |
| WHO ICTRP | Yes, free download | Credit "WHO ICTRP". Keep data current. **Show the date WHO ICTRP processed the data.** No proprietary claim. **No use "for marketing, promotional or commercial purposes".** **No use of the WHO name or emblem** with the data ([ICTRP terms](https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set/downloading-records-from-the-ictrp-database)). Separate crawling-service conditions exist ([WHO](https://www.who.int/publications/m/item/who-ictrp-crawling-service---conditions-of-use)). | Verified |
| Keestra/GlobalHealthRanking code | MIT | Keep the copyright and licence notice if any code is reused. | Verified via GitHub API licence field, 2026-10-04 ([repo](https://github.com/LeeSean96/GlobalHealthRanking)) |

What this means for the build:
- Every page and download needs a **data-as-of stamp per source** and a **"modifications" statement**: our derivation rules, category logic and any cleaning. ClinicalTrials.gov requires both, and ICTRP requires the date.
- The ICTRP non-commercial clause is the tightest constraint. It also lines up with Vercel Hobby's non-commercial limit (§5). Any monetisation, sponsorship or consultancy built on the site would conflict with both.
- Do not put WHO branding on the site. Wording such as "WHO standard" with a citation is fine, but a WHO logo is not **[unverified: whether naming "the WHO standard" counts as using the WHO name in association with data]**.

### 2. GDPR exposure

- Registry records carry personal data. ClinicalTrials.gov exposes `responsibleParty.investigatorFullName`, `overallOfficials.name/affiliation`, `centralContacts.name/phone/email` and `resultsSection.moreInfoModule.pointOfContact` (title, email, phone). The lead sponsor can be an individual: `leadSponsor.class` includes `INDIV` ([CT.gov API metadata](https://clinicaltrials.gov/api/v2/studies/metadata), [enums](https://clinicaltrials.gov/api/v2/studies/enums)).
- Data being publicly available does not take it out of the GDPR. Republishing it is a new processing operation that needs its own lawful basis (Art 6) and transparency (Art 14). Art 14(5)(b) allows an exemption where informing people individually would take disproportionate effort, but the information must still be made public ([GDPR, EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj)). Text not re-fetched this session: **[unverified]**, though these are standard provisions.
- The household exemption does not cover publishing to the whole internet. That follows from CJEU *Lindqvist* (C-101/01) **[unverified: not fetched]**.
- Art 85 lets member states exempt journalistic and academic expression. The Dutch implementing law (UAVG) has an Art 43 headed "Uitzonderingen inzake journalistieke doeleinden of academische, artistieke of literaire uitdrukkingsvormen" and an Art 44 for scientific research and statistics ([UAVG, wetten.overheid.nl](https://wetten.overheid.nl/BWBR0040940/2021-07-01)). The exact scope of Art 43, and whether a hobbyist tracker qualifies, is **[unverified]**. It is a lawyer question.
- The controller would be the Dutch individual, so the supervisory authority is the Autoriteit Persoonsgegevens. **[unverified]**: this follows from GDPR Art 55/56.

**Finding:** the tracker's purpose is to rank organisations, and it needs no person-level fields for that. Dropping them removes most of the GDPR surface. The remaining problem is rows where the **lead sponsor is a natural person** (`INDIV`, and some `OTHER` rows whose names are people). A person-named "due, not reported" row is personal data and an accusation about an individual at the same time. That is a GDPR issue and a defamation issue together.

### 3. Defamation and accuracy

**Netherlands (home jurisdiction).**
- Civil liability falls under the general tort, Art 6:162 BW: "een inbreuk op een recht ... of met hetgeen volgens ongeschreven recht in het maatschappelijk verkeer betaamt", unless a justification applies ([BW 6:162](https://wetten.overheid.nl/jci1.3:c:BWBR0005289&boek=6&titeldeel=3&afdeling=1&artikel=162)). Dutch courts balance freedom of expression against reputation. The factors include how well the factual basis supports the statement, how it is phrased, and whether the subject was heard **[unverified: case-law factors not fetched]**.
- Criminal defamation offences (smaad/laster, Arts 261–262 Sr) exist. The public-interest defence in Art 261(3) is **[unverified: text not retrieved]**.

**EU anti-SLAPP.** Directive (EU) 2024/1069 had a transposition deadline of 7 May 2026. The Dutch bill was described as narrow: one amendment on security for costs ([EAPIL, May 2026 status](https://eapil.org/2026/05/07/status-of-the-anti-slapp-directive-transpositions-at-the-7-may-2026-deadline/); [EAPIL Feb 2025](https://eapil.org/2025/02/18/progress-and-challenges-for-slapp-targets-from-the-perspective-of-eu-and-dutch-pil/)). Whether it has been enacted is **[unverified]**. The Directive covers cross-border cases only, so its use against a domestic Dutch claim is limited **[unverified]**.

**United Kingdom (relevant because UK sponsors are named).**
- Defamation Act 2013 s1 requires serious harm. Under s1(2), a body trading for profit must show serious financial loss ([s1](https://www.legislation.gov.uk/ukpga/2013/26/section/1)). The s1(2) wording is from the Act and was not quoted in the fetch, so **[unverified]** verbatim.
- s4 gives a defence for publication on a matter of public interest where the defendant reasonably believed publishing was in the public interest ([s4](https://www.legislation.gov.uk/ukpga/2013/26/section/4)).
- s9 limits jurisdiction over non-UK-domiciled defendants: the court must be satisfied that England and Wales is clearly the most appropriate place to bring the action ([s9](https://www.legislation.gov.uk/ukpga/2013/26/section/9)). A Dutch-domiciled publisher therefore has some protection, but not immunity.
- Whether public bodies (NHS trusts, universities) can sue at all is **[unverified]**. It is a lawyer question.

**Accuracy risks specific to this tracker** (each one is a way the site could make a false statement of fact):
- **Stale registry status.** Trials left as "Recruiting/Active" or with wrong completion dates distort the counts. TranspariMED's Nov 2024 "Metascience fail" critique says stale status inflates "unreported" **[unverified: not fetched here; cited in brief]**.
- **Results submitted but not yet posted.** ClinicalTrials.gov separates `resultsFirstSubmitDate` from `resultsFirstPostDateStruct`. A trial can be compliant on submission while QC delays posting ([API metadata](https://clinicaltrials.gov/api/v2/studies/metadata)). 42 CFR 11.44 deadlines are about **submission** ([11.44](https://www.law.cornell.edu/cfr/text/42/11.44)).
- **Lawful delays.** Certified delays and good-cause extensions (§4) are visible only through `dispFirstSubmitDate` and related fields. If these are ignored, the site will label legally compliant trials as late.
- **Results published elsewhere** (journal, CTIS, EudraCT, ISRCTN, national registry). The WHO standard is registry posting, so a trial with a paper but no registry entry is accurately "not reported on registry". It is not accurate to call its results "unpublished" or "hidden".
- **Sponsor mis-attribution.** Lead-sponsor strings are free text, and name normalisation can merge or split institutions wrongly. Precedent: Keestra et al. 2021 classified by lead sponsor (per brief).

**Practices that lower risk**, consistent with both s4 public-interest reasoning and Dutch balancing:
- Publish the full methodology and the code (the repo is public). Link each count to the trial IDs behind it.
- Date-stamp every snapshot and keep earlier snapshots immutable, so any statement can be traced to the data as of that date.
- Phrase labels as observations about the registry: "No summary results posted on ClinicalTrials.gov within 12 months of primary completion (as of YYYY-MM-DD)". Avoid "failed", "hid", "violated", "breach" and "illegal".
- Never say "in breach of the law" unless a duty is established (§4). The only label that comes from a regulator rather than from us is ClinicalTrials.gov's own `fdaaa801Violation` flag (set when FDA has issued a Notice of Noncompliance) ([API metadata](https://clinicaltrials.gov/api/v2/studies/metadata); [CU Anschutz on NoNC flag](https://research.cuanschutz.edu/crs/clinical-research-support/clinical-research-administration/clinicaltrials.gov-support/tips-of-the-week-archive/tip-of-the-week-april-2-2020/fda-issues-first-notice-of-noncompliance-to-an-individual-investigator-for-failing-to-submit-results-to-clinicaltrials.gov)).
- Run a **correction / right-of-reply process**: a public contact address, a stated response time, a public corrections log, and a per-trial "dispute" note that does not delete data. Fixes should go upstream: the registry is the source, so the usual fix is "update your registry record". The next refresh then picks it up.
- Name the publisher (the Dutch "imprint" duty for non-commercial sites is **[unverified]**). An anonymous accuser is less credible and does not escape liability.
- Hide or aggregate individual-person sponsors (§2).

### 4. Legal reporting duties: what lets us say "legally due"

**US: FDAAA 801 / 42 CFR Part 11**
- The duty applies only to **applicable clinical trials (ACTs)**. These are controlled clinical investigations of FDA-regulated drugs or biologics, *other than phase 1*, and prospective device studies, *other than small feasibility studies* ([42 CFR 11.10](https://www.law.cornell.edu/cfr/text/42/11.10)). Registration is required for ACTs initiated after 27 Sep 2007, or ongoing on 26 Dec 2007 ([11.22](https://www.law.cornell.edu/cfr/text/42/11.22)). The Final Rule's effective date (18 Jan 2017) and the rules for older ACTs are **[unverified]** in this session.
- Results are due **no later than 1 year after the primary completion date** ([11.44(a)](https://www.law.cornell.edu/cfr/text/42/11.44)).
- A **delayed submission with certification** applies when approval, licensure or clearance is being sought: for an initial approval under 11.44(c), for a new use under 11.44(b). Results are then due 30 days after approval/withdrawal, and in either case no later than 2 years after the certification was submitted ([11.44(b)–(c)](https://www.law.cornell.edu/cfr/text/42/11.44)). (Corrected 2026-10-04: an earlier draft attributed the initial-approval case to (b); see critique.md.)
- **Good-cause extensions** are possible, and more than one can be requested ([11.44(e)](https://www.law.cornell.edu/cfr/text/42/11.44)).
- ClinicalTrials.gov does not publish ACT status as a field. The proxies are `isFdaRegulatedDrug`, `isFdaRegulatedDevice`, phase, study type, dates, and US-site/IND fields ([API metadata](https://clinicaltrials.gov/api/v2/studies/metadata)). ACT is therefore an **inference**, the same "probable ACT" approach used by FDAAA TrialsTracker (per brief).
- Enforcement: civil money penalties after a Notice of Noncompliance ([CU Anschutz](https://research.cuanschutz.edu/crs/clinical-research-support/clinical-research-administration/clinicaltrials.gov-support/tips-of-the-week-archive/tip-of-the-week-april-2-2020/fda-issues-first-notice-of-noncompliance-to-an-individual-investigator-for-failing-to-submit-results-to-clinicaltrials.gov)). The amount is current-inflation-adjusted **[unverified]**.

**EU: CTR 536/2014 and the Directive-era trials**
- Art 37(4): "Irrespective of the outcome of a clinical trial, within one year from the end of a clinical trial in all Member States concerned, the sponsor shall submit to the EU database a summary of the results", together with a lay summary. If a delay for scientific reasons is set out in the protocol, the summary is due as soon as it is available ([Art 37 text](https://www.legislation.gov.uk/eur/2014/536/article/37)). This is the legislation.gov.uk copy of the original EU text, and the EUR-Lex copy could not be fetched. The clock runs from the **end of trial in all member states**, not from primary completion.
- **Paediatric: 6 months.** This deadline is **not in the text of Art 37(4)**. It comes from the Paediatric Regulation (EC) 1901/2006 and Commission Guideline 2012/C 302/03: 6 months, extendable to 12 for objective scientific reasons in some cases ([Guideline 2012/C 302/03](https://gmp-compliance.org/files/guidemgr/2012_302-03_en.pdf); [EMA results posting guidance](https://euctis-sr.ema.europa.eu/docs/guidance/Trial%20results_Modalities%20and%20timing%20of%20posting.pdf)). Regulators say the 6-month deadline also applies under the CTR ([Norwegian Medical Products Agency](https://www.dmp.no/en/approval-of-medicines/clinical-trials/reporting-when-a-clinical-trial-is-completed)). The exact legal basis under the CTR is **[unverified]**. Directive-era trials that ended on or after 21 Jul 2014 had 12 months (6 for paediatric) on EudraCT under that guideline (same sources).
- The CTR applies to CTIMPs (medicinal products) only. Device and behavioural trials are out of scope. **[unverified]** as a citation, though it follows from the Regulation's scope.
- The CTIS transparency rules were revised from 18 Jun 2024. Deferral of publication was removed for applications from that date ([EMA news](https://www.ema.europa.eu/et/news/revised-transparency-rules-eu-clinical-trials-information-system-ctis)). Older deferrals can make results look missing from the public portal when the sponsor has in fact submitted them **[unverified scale]**.

**UK: SI 2025/538** ([legislation.gov.uk](https://www.legislation.gov.uk/uksi/2025/538/made))
- In force 28 Apr 2026 ([legislation.gov.uk](https://www.legislation.gov.uk/uksi/2025/538); [Penningtons](https://penningtonslaw.com/insights/navigating-the-new-landscape-2026-clinical-trial-regulations-changes-and-contract-review-requirements)). It amends the Medicines for Human Use (Clinical Trials) Regulations, so it covers **CTIMPs only** **[unverified scope wording]**.
- New reg 25(2): within **12 months beginning with the day after the conclusion of the trial**, the sponsor must post a results summary in the same public registry or registries used for registration, and offer participants a lay summary. A "public registry" is a WHO ICTRP primary or partner registry, or a data provider to it (reg 25(12)).
- Deferrals: the Authority can defer for up to 30 months, renewable. **Phase I trials can receive an automatic deferral of up to 30 months.** The total is capped at **10 years** (reg 25(5)–(11)). Deferrals do not appear in the registry **[unverified]**, so a UK trial past 12 months may be lawfully deferred.
- **Transitional (Sch 14 para 2(8)):** reg 25 **does not apply to trials whose end-of-trial date is before 28 Apr 2026**. For older-rules trials ending on or after that date, the lay summary duty (25(2)(b)) does not apply. **So no UK trial can be legally overdue before about 28 Apr 2027.** Every UK "due, not reported" label before then is about the WHO standard only.

**Labelling consequence.** The tracker should have two independent axes:
1. **WHO standard (all trials):** the Keestra categories, unchanged.
2. **Legal duty (where determinable):** `US-FDAAA probable ACT`, `EU-CTR`, `UK-CTIMP (post-28 Apr 2026)`, or `no legal duty identified / unknown`. Only the FDA's own Notice of Noncompliance flag supports a statement that a breach occurred. In every other case the site can say at most "appears overdue under [rule], absent an unpublished deferral/extension".

### 5. Hosting: Vercel

- Vercel Hobby is "restricted to non-commercial personal use only". Commercial use means any deployment "used for the purpose of financial gain of anyone involved in any part of the production of the project" ([Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines); [Hobby plan](https://vercel.com/docs/plans/hobby)). This is fine for an unpaid hobby tracker. Vercel states that asking for donations "does not fall under commercial usage"; grants or paid consulting tied to the site would still need checking (corrected 2026-10-04, see critique.md).
- Vercel is a US provider. Its take-down handling and cooperation with legal demands follow its own terms, which were **[unverified]** this session. If a Dutch or UK claimant demands removal, the host may act before any court decides.
- Use no analytics or cookies by default. That avoids cookie-consent duties under the Dutch Telecommunicatiewet **[unverified: not fetched]**.

### 6. What a lawyer should confirm

1. Whether NL UAVG Art 43 (academic expression) or Art 44 (research) covers a privately run public tracker, and whether Art 14 notices are needed if no person-level fields are published.
2. Whether ranking named institutions on "due, not reported", with methodology and right of reply, fits within Dutch case law on freedom of expression versus reputation. Whether criminal smaad/laster is a realistic exposure.
3. UK exposure: how s9 forum works for a Dutch-domiciled individual; s1(2) for pharma; whether NHS bodies and universities can sue.
4. Whether ICTRP's "no commercial purposes" clause and Vercel Hobby limits are breached by grant funding, donations, or the publisher's employment (Soilytix is unrelated, but the publisher's identity should be stated).
5. The current ClinicalTrials.gov terms text, since only the 2014 archived wording was verified, and AACT's terms.
6. Whether legal-duty labels ("probable ACT", "EU-CTR", "UK CTIMP") need extra disclaimers, and whether the `fdaaa801Violation` flag may be quoted as "FDA has found a violation".
7. Whether there is a Dutch imprint or identification duty for a non-commercial site.

## Recommendation

Build the tracker as a **descriptive, date-stamped registry audit**, not an accusation engine:

- **Data:** ingest ClinicalTrials.gov via the API or AACT first, ISRCTN second, and CTIS/EU CTR and ICTRP later. Show per-source credits, "data processed on" dates and a modifications statement in the footer and in every download. No WHO emblem, and no commercial use.
- **Personal data:** keep no person-level fields in the published dataset or site (`overallOfficials`, `centralContacts`, `pointOfContact`, `investigatorFullName`). Rank only organisations. Rows whose lead sponsor is `INDIV`, or is detected as a person, are aggregated into an "individual sponsors" bucket with no names, and trial IDs remain clickable to the registry. Publish a short privacy statement.
- **Labels:** keep the WHO-standard categories (Keestra) as the primary axis, worded as registry observations with an as-of date. Add a separate legal-duty axis that defaults to "not determined". Never use "illegal", "breach" or "violation", except to quote the FDA's own Notice of Noncompliance flag, attributed. Treat **submission** date, not post date, as reporting, and treat certified delays and extensions as not-yet-due for FDAAA rows.
- **UK:** show "UK legal duty applies only to CTIMPs ending on or after 28 Apr 2026, earliest due ~28 Apr 2027" wherever UK sponsors appear.
- **Process:** publish the methodology page and correction policy before the first named ranking goes live. Provide a contact address, a right-of-reply note per institution, a public corrections log and immutable snapshots.
- **Before launch:** a one-hour consult with a Dutch media/privacy lawyer on items 1–3 of §6. This is cheap compared with the risk and is the gating item for naming institutions.

## Open decisions

1. **Person-level data.** Options: (a) drop all person fields and bucket individual sponsors anonymously; (b) drop contacts but show individual sponsors by name; (c) mirror registry fields as-is. **Recommend (a).**
2. **Legal-duty labelling at launch.** Options: (a) WHO standard only, with legal duty added later; (b) WHO standard plus "probable ACT" for the US only; (c) all three jurisdictions from day one. **Recommend (b)**, plus a static note on UK and EU timing. EU-CTR due dates need CTIS end-of-trial dates that are not yet ingested.
3. **Naming threshold.** Options: (a) name every lead sponsor; (b) name only sponsors with ≥N due trials (e.g. N=5, a judgement call), and aggregate the rest; (c) show only top-level aggregates and no named list. **Recommend (b)**: it lowers small-n noise and individual-sponsor exposure, and matches Keestra-style ranking.
4. **Right-of-reply mechanics.** Options: (a) contact email plus corrections log; (b) a pre-publication notice to named institutions before the first public ranking; (c) none. **Recommend (a) at launch, (b) for any press push.**
5. **Publisher identity on the site.** Options: (a) personal name with a Dutch contact; (b) a pseudonymous project name with a contact form. **Recommend (a).** Anonymity weakens credibility and gives no legal shield. Make clear it is unrelated to Soilytix.
6. **Hosting tier and funding.** Options: (a) stay on Vercel Hobby and take no money; (b) accept donations or grants and move to Pro or Cloudflare Pages; (c) decide later. **Recommend (a) now.** Revisit before taking any money, because of the ICTRP non-commercial clause and Vercel Hobby terms.
7. **Legal review before naming.** Options: (a) launch the methodology and an unnamed aggregate first, and name institutions after a lawyer consult; (b) launch named immediately. **Recommend (a).**
8. **ICTRP ingestion.** Options: (a) use ICTRP as a cross-registry source; (b) go direct to each registry (CTIS, ISRCTN, DRKS, etc.) to avoid ICTRP's non-commercial and "keep current" obligations. **Recommend (b)** for core counts, and use ICTRP only for discovery.

## Sources

- ClinicalTrials.gov terms (current, client-rendered): https://clinicaltrials.gov/about-site/terms-conditions
- ClinicalTrials.gov terms (archived classic, reviewed May 2014): https://web.archive.org/web/2024/https://classic.clinicaltrials.gov/ct2/about-site/terms-conditions
- ClinicalTrials.gov API v2 metadata: https://clinicaltrials.gov/api/v2/studies/metadata ; enums: https://clinicaltrials.gov/api/v2/studies/enums
- AACT: https://aact.ctti-clinicaltrials.org/ ; CTTI citation policy: https://ctti-clinicaltrials.org/?p=7671
- EMA legal notice: https://www.ema.europa.eu/en/about-us/legal-notice
- EMA revised CTIS transparency rules: https://www.ema.europa.eu/et/news/revised-transparency-rules-eu-clinical-trials-information-system-ctis
- ISRCTN terms: https://www.isrctn.com/page/terms
- WHO ICTRP download terms: https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set/downloading-records-from-the-ictrp-database ; crawling conditions: https://www.who.int/publications/m/item/who-ictrp-crawling-service---conditions-of-use
- GDPR (Regulation 2016/679): https://eur-lex.europa.eu/eli/reg/2016/679/oj
- UAVG (NL): https://wetten.overheid.nl/BWBR0040940/2021-07-01
- BW 6:162: https://wetten.overheid.nl/jci1.3:c:BWBR0005289&boek=6&titeldeel=3&afdeling=1&artikel=162
- Defamation Act 2013 s1/s4/s9: https://www.legislation.gov.uk/ukpga/2013/26/section/1 , /section/4 , /section/9
- Anti-SLAPP status: https://eapil.org/2026/05/07/status-of-the-anti-slapp-directive-transpositions-at-the-7-may-2026-deadline/ ; https://eapil.org/2025/02/18/progress-and-challenges-for-slapp-targets-from-the-perspective-of-eu-and-dutch-pil/
- 42 CFR 11.10: https://www.law.cornell.edu/cfr/text/42/11.10 ; 11.22: https://www.law.cornell.edu/cfr/text/42/11.22 ; 11.44: https://www.law.cornell.edu/cfr/text/42/11.44
- FDA NoNC / violation flag: https://research.cuanschutz.edu/crs/clinical-research-support/clinical-research-administration/clinicaltrials.gov-support/tips-of-the-week-archive/tip-of-the-week-april-2-2020/fda-issues-first-notice-of-noncompliance-to-an-individual-investigator-for-failing-to-submit-results-to-clinicaltrials.gov
- EU CTR Art 37: https://www.legislation.gov.uk/eur/2014/536/article/37
- Commission Guideline 2012/C 302/03: https://gmp-compliance.org/files/guidemgr/2012_302-03_en.pdf ; EMA posting guidance: https://euctis-sr.ema.europa.eu/docs/guidance/Trial%20results_Modalities%20and%20timing%20of%20posting.pdf
- Norwegian Medical Products Agency (paediatric 6 months under CTR): https://www.dmp.no/en/approval-of-medicines/clinical-trials/reporting-when-a-clinical-trial-is-completed
- UK SI 2025/538: https://www.legislation.gov.uk/uksi/2025/538 ; made text: https://www.legislation.gov.uk/uksi/2025/538/made
- Penningtons on 2026 UK changes: https://penningtonslaw.com/insights/navigating-the-new-landscape-2026-clinical-trial-regulations-changes-and-contract-review-requirements
- Vercel fair use: https://vercel.com/docs/limits/fair-use-guidelines ; Hobby plan: https://vercel.com/docs/plans/hobby

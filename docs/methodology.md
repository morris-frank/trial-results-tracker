---
date: 2026-10-05
area: Methodology v1.1
---

The rules the tracker uses to sort a trial into a reporting category. The code is `V1_1` in `src/trial_results_tracker/classify.py`; every rule below has a test in `tests/test_classify_v1.py` or `tests/test_classify_v1_1.py` that names its decision (D1–D5, D16, `docs/plan.md`). Evidence and alternatives are in `docs/research/methodology.md`. Every published number carries the method version (`v1.1`), the ClinicalTrials.gov `dataTimestamp` and the code commit.

## Standard

WHO best practice: summary results on the registry within 12 months of primary completion ([WHO 2017](https://www.who.int/news/item/18-05-2017-joint-statement-on-registration)). This is a registry observation, not a legal finding; the legal-duty column is separate: a US "probable ACT" inference (`legal_us.py`), UK and EU not determined (AGENTS.md rule 2).

## Scope and evidence basis

Interventional ClinicalTrials.gov studies from a dated API v2 snapshot. Evidence basis: **registry only**. Publications, EUCTR and CTIS are not searched.

## Rules

1. **Clock.** Primary completion date (PCD). A partial date sits on the last day of its month or year, the reading most favourable to the sponsor. There is no fallback to the study completion date.
2. **Threshold (D2).** One number, 395 days (12 months plus a 30-day QC grace), used for both cuts:
   - a finished trial is *due* once more than 395 days have passed since PCD;
   - a due trial reported *in time* submitted results no more than 395 days after PCD.
   Until the threshold passes, a finished trial is "completed, not yet due" even if it has already submitted results, so the due cohort is defined by time alone.
3. **Reported (D1).** The reporting date is the sponsor's own act: `resultsFirstSubmitDate`, or, where that is absent (the registry sets it only once results post), the date of the earliest event in `unpostedEvents`. A derived submission whose last unposted event is UNRELEASE was withdrawn by the sponsor and is not reported. The posting date is shown beside it per trial but does not decide the category. A submission whose latest unposted event is RESET, with nothing posted, is **due, submitted but returned in QC**, not reported.
4. **Finished trials (D4).** COMPLETED or TERMINATED trials are classified on the rules above only when their PCD is present and of type ACTUAL. A missing, ESTIMATED or untyped PCD makes the record **inconsistent**. A TERMINATED trial with actual enrolment 0 has **no reporting requirement**.
5. **Open statuses (D3, D5, D16).** Not yet recruiting, recruiting, enrolling by invitation, active not recruiting and **suspended** (a pause, not an exemption) are **ongoing** until PCD + 395 days. An open-status trial without a PCD is ongoing. Past PCD + 395 days:
   - with results submitted, or **active, not recruiting** with an ACTUAL PCD (primary completion has happened; only follow-up continues), the trial is scored on rules 2–3 like a finished trial;
   - **not yet recruiting** is **probably never started**;
   - anything else is **status overdue**, a status that is probably stale.
6. **Withdrawn** trials have no reporting requirement.
7. Every other status (UNKNOWN, expanded-access statuses, missing or unrecognised values) is **inconsistent**.

## Categories

| Category | Counted as unreported? |
|---|---|
| No reporting requirement | No; outside the denominator |
| Due, not reported | Yes |
| Due, reported in time | No |
| Due, reported late | No |
| Due, submitted but returned in QC | Shown separately |
| Completed, not yet due | No; outside the denominator |
| Ongoing | No; outside the denominator |
| Status overdue | Never in the point estimate; in the upper bound (D5) |
| Probably never started | No; outside the denominator and the upper bound (D16) |
| Inconsistent | Never in the point estimate; in the upper bound (D5) |

Stale registry status is not non-reporting (AGENTS.md rule 3). How the headline and its upper bound are computed is plan task T7.

## Changes from v1.0 (D16)

v1.0 sent every open-status trial past PCD + 395 days to status overdue before looking at results, so the upper bound counted trials that had submitted results as unreported, and follow-up after an actual primary completion dropped out of the denominator. On `data-2026-10-05` (data timestamp 2026-10-02, 462,154 trials) v1.1 moves 5,197 trials, all out of status overdue:

| v1.0 | v1.1 | Trials |
|---|---|---:|
| Status overdue | Due, not reported | 2,677 |
| Status overdue | Probably never started | 1,148 |
| Status overdue | Due, reported in time | 703 |
| Status overdue | Due, reported late | 453 |
| Status overdue | Due, submitted but returned in QC | 216 |

The point estimate goes from 70.45% (186,959 of 265,371 due) to 70.39% (189,636 of 269,420), and the upper bound from 77.90% to 77.44%. `V1_0` stays in `classify.py` for this comparison.

## Changes from the Keestra-2021 replication

`KEESTRA_2021` transcribes the predecessor's code and stays as the comparison; `crosswalk(trials, as_of)` in `src/trial_results_tracker/crosswalk.py` counts trials per pair of Keestra-2021 and v1.1 categories so readers can see what each change moves.

| Point | Keestra-2021 | v1.1 |
|---|---|---|
| Due at exactly 395 days | Due | Not yet due |
| In-time cut | Not used; reported means submitted at any time | Submitted ≤ 395 days after PCD |
| Month-only PCD | First of the month | Last of the month |
| Suspended | No reporting requirement | Ongoing, then scored as due if results were submitted, else status overdue |
| Finished, missing PCD | Due | Inconsistent |
| Finished, ESTIMATED PCD | Treated as actual | Inconsistent |
| TERMINATED, 0 actual enrolment | Due | No reporting requirement |
| Submission returned in QC | Reported | Own category |
| Open status, PCD past | Inconsistent after 30 days | Ongoing to 395 days, then by D16: due, probably never started or status overdue |

## Not decided here

Which categories enter the headline and the upper bound is fixed in T7 (D5). Sponsor attribution, grouping and naming wait for D6–D8 and the naming gate.

## Validation

Two coders classify a seeded, stratified sample of 200 trials by hand (D14, plan task T11); `validate sample` and `validate score` in `src/trial_results_tracker/validate.py` draw and score it. Results per method and snapshot are in `docs/validation/`: [v1.1 on data-2026-10-05](validation/v1.1-data-2026-10-05.md) (sample drawn, coding pending; it replaces the uncoded v1.0 sample).

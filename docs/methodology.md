---
date: 2026-10-05
area: Methodology v1.0
---

The rules the tracker uses to sort a trial into a reporting category. The code is `V1_0` in `src/trial_results_tracker/classify.py`; every rule below has a test in `tests/test_classify_v1.py` that names its decision (D1–D5, `docs/plan.md`). Evidence and alternatives are in `docs/research/methodology.md`. Every published number carries the method version (`v1.0`), the ClinicalTrials.gov `dataTimestamp` and the code commit.

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
3. **Reported (D1).** The reporting date is `resultsFirstSubmitDate`, the sponsor's own act. The posting date is shown beside it per trial but does not decide the category. A submission whose latest unposted event is RESET, with nothing posted, is **due, submitted but returned in QC**, not reported.
4. **Finished trials (D4).** COMPLETED or TERMINATED trials are classified on the rules above only when their PCD is present and of type ACTUAL. A missing, ESTIMATED or untyped PCD makes the record **inconsistent**. A TERMINATED trial with actual enrolment 0 has **no reporting requirement**.
5. **Open statuses (D3, D5).** Not yet recruiting, recruiting, enrolling by invitation, active not recruiting and **suspended** (a pause, not an exemption) are **ongoing** until PCD + 395 days, then **status overdue**. An open-status trial without a PCD is ongoing.
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
| Inconsistent | Never in the point estimate; in the upper bound (D5) |

Stale registry status is not non-reporting (AGENTS.md rule 3). How the headline and its upper bound are computed is plan task T7.

## Changes from the Keestra-2021 replication

`KEESTRA_2021` transcribes the predecessor's code and stays as the comparison; `crosswalk(trials, as_of)` in `src/trial_results_tracker/crosswalk.py` counts trials per pair of categories so readers can see what each change moves.

| Point | Keestra-2021 | v1.0 |
|---|---|---|
| Due at exactly 395 days | Due | Not yet due |
| In-time cut | Not used; reported means submitted at any time | Submitted ≤ 395 days after PCD |
| Month-only PCD | First of the month | Last of the month |
| Suspended | No reporting requirement | Ongoing, then status overdue |
| Finished, missing PCD | Due | Inconsistent |
| Finished, ESTIMATED PCD | Treated as actual | Inconsistent |
| TERMINATED, 0 actual enrolment | Due | No reporting requirement |
| Submission returned in QC | Reported | Own category |
| Open status, PCD past | Inconsistent after 30 days | Ongoing to 395 days, then status overdue |

## Not decided here

Which categories enter the headline and the upper bound is fixed in T7 (D5). Sponsor attribution, grouping and naming wait for D6–D8 and the naming gate.

## Validation

Two coders classify a seeded, stratified sample of 200 trials by hand (D14, plan task T11); `validate sample` and `validate score` in `src/trial_results_tracker/validate.py` draw and score it. Results per method and snapshot are in `docs/validation/`: [v1.0 on data-2026-10-05](validation/v1.0-data-2026-10-05.md) (sample drawn, coding pending).

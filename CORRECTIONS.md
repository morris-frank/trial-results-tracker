# Corrections log

The public log of every correction and dispute (docs/plan.md T12). Report one with the
[correction form](https://github.com/morris-frank/trial-results-tracker/issues/new?template=correction.yml).

- **A dispute never deletes data.** While it is open, its trial stays listed with a note.
  The note is a row in `sponsors/disputes.csv`: `nct_id`, `opened_on`, `issue` (the
  correction request's URL) and `note`, as it should read on the site.
- **The registry is the source.** When a registry record is wrong, the fix is to update it
  on ClinicalTrials.gov; the next data refresh picks it up.
- **Our errors are fixed in code, with a test, and logged here.** When a rule, an alias row
  or a category is wrong, it is fixed in code and listed below.
- **Closing a dispute.** Remove its row from `sponsors/disputes.csv` and add its outcome
  below.

| Opened | Closed | Issue | Trials or sponsor | Outcome |
| ------ | ------ | ----- | ----------------- | ------- |

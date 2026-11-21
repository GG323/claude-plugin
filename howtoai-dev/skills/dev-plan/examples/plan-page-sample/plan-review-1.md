# Login rate limit: plan review round 1

Change `2026-11-19-login-rate-limit` · Size: Medium · Reviewers: comprehension, critic · Threshold: 80 · Result: not clean

## Summary

| Severity | Raised | Kept | Outside | Held back | Refuted | Weakened |
| --- | --- | --- | --- | --- | --- | --- |
| Blocker | 0 | 0 | 0 | 0 | 0 | 0 |
| Major | 2 | 1 | 0 | 0 | 1 | 0 |
| Nit | 1 | 1 | 0 | 0 | 0 | 0 |

## Findings

### critic

| ID | Severity | Confidence | Verdict | Mark | Location | Finding | Recommendation | Resolution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1-K1 | Major | 90 | stands | confirmed | Design details | No cleanup of old rows | Expire rows after 15 minutes | fixed: Design details |
| P1-K2 | Nit | 85 | not verified | inferred | Risks | Wording | Reword | open |

## Outside this change

none

## Appendix: held back

| ID | Severity | Confidence | Reason held back | Finding |
| --- | --- | --- | --- | --- |
| none | | | | |

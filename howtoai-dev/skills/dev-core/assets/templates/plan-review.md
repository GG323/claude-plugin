# {title}: plan review round {n}

Change `{change_id}` · Size: {size} · Reviewers: {goldfish viewpoints run} · Threshold: {threshold} · Result: {clean / not clean}

Written by `findings.py tally`; only the Resolution cells are filled by hand.

## Summary

Counted by the severity each finding was raised with; Raised = Kept + Outside + Held back + Refuted, and Weakened counts the kept, outside, or held-back findings the verifier lowered.

| Severity | Raised | Kept | Outside | Held back | Refuted | Weakened |
| --- | --- | --- | --- | --- | --- | --- |
| Blocker | {n} | {n} | {n} | {n} | {n} | {n} |
| Major | {n} | {n} | {n} | {n} | {n} | {n} |
| Nit | {n} | {n} | {n} | {n} | {n} | {n} |

## Findings

### {viewpoint}

| ID | Severity | Confidence | Verdict | Mark | Location | Finding | Recommendation | Resolution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {P1-K1} | {Blocker / Major / Nit} | {0-100} | {stands / weakened from X / not verified} | {confirmed / inferred} | {plan section or file:line} | {finding, with the quote} | {recommendation} | {open, then fixed: / decided: / asked: / declined: / outside: } |

## Outside this change

Verified Blocker, Critical, or Major findings outside the change under review. They do not count against this round; each needs a decision.

| ID | Severity | Confidence | Verdict | Viewpoint | Location | Finding | Recommendation | Why outside | Resolution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {P1-K4} | {Blocker / Major} | {0-100} | {stands / weakened from X} | {viewpoint} | {plan section or file:line} | {finding, with the quote} | {recommendation} | {marked outside the change by the reviewer} | {open, then outside: <follow-up> / declined: <evidence>} |

"none" when there are none.

## Appendix: held back

| ID | Severity | Confidence | Reason held back | Finding |
| --- | --- | --- | --- | --- |
| {id} | {severity} | {score} | {below threshold: scorer reason / refuted: verifier evidence / outside the change, Nit / duplicate of ID} | {finding} |

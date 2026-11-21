# {title}: review round {n}

Change `{change_id}` · Diff: {base}..{head} · Reviewers: {goldfish viewpoints run} · Verdict: {blocked / changes requested / approved} · Result: {clean / not clean}

## Summary

| Impact | Findings | AUTO-FIX | ASK |
| --- | --- | --- | --- |
| Critical | {n} | {n} | {n} |
| Major | {n} | {n} | {n} |
| Minor | {n} | {n} | {n} |
| Nit | {n} | {n} | {n} |

Counts come from the tally script. Outside this change: {n} (not counted above). Findings scored under the confidence threshold are in the appendix.

## Findings by area

### {area}

| ID | Impact | Confidence | Mark | Location | Finding | Proposed fix | Handling | Your choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R{n}-01 | {Critical / Major / Minor / Nit} | {0-100} | {confirmed / inferred} | {file:line} | {finding, with the quoted line} | {smallest fix} | {AUTO-FIX / ASK} | {fix now / later / decline: reason} |

## Test inspection

- **Runs:** {suites run, results, and where the output is}
- **Temporary tests:** {tests added to confirm a finding or close a gap, and whether each was removed or promoted}
- **Coverage gaps:** {untested paths found; "none"}

## Outside this change

Verified Blocker, Critical, or Major findings outside the change under review. They do not count against this round; each needs a decision.

| ID | Severity | Confidence | Verdict | Viewpoint | Location | Finding | Recommendation | Why outside | Your choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R{n}-C4 | {Critical / Major} | {0-100} | {stands / weakened from X} | {viewpoint} | {file:line} | {finding, with the quoted line} | {smallest fix} | {unchanged line: not in this round's diff / marked outside the change by the reviewer} | {later / decline: reason} |

"none" when there are none.

## Appendix: low confidence and filtered

| ID | Confidence | Reason held back | Finding |
| --- | --- | --- | --- |
| {id} | {score} | {below threshold / refuted / outside the change, Minor or Nit / duplicate of ID} | {finding} |

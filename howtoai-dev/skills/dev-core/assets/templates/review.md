# {title}: review round {n}

Change `{change_id}` · Diff: {base}..{head} · Reviewers: {goldfish viewpoints run} · Verdict: {blocked / changes requested / approved}

## Summary

| Impact | Findings | AUTO-FIX | ASK |
| --- | --- | --- | --- |
| Critical | {n} | {n} | {n} |
| Major | {n} | {n} | {n} |
| Minor | {n} | {n} | {n} |
| Nit | {n} | {n} | {n} |

Counts come from the tally script. Findings scored under the confidence threshold are in the appendix.

## Findings by area

### {area}

| ID | Impact | Confidence | Mark | Location | Finding | Proposed fix | Handling | Your choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R{n}-01 | {Critical / Major / Minor / Nit} | {0-100} | {confirmed / inferred} | {file:line} | {finding, with the quoted line} | {smallest fix} | {AUTO-FIX / ASK} | {fix now / later / decline: reason} |

## Test inspection

- **Runs:** {suites run, results, and where the output is}
- **Temporary tests:** {tests added to confirm a finding or close a gap, and whether each was removed or promoted}
- **Coverage gaps:** {untested paths found; "none"}

## Appendix: low confidence and filtered

| ID | Confidence | Reason held back | Finding |
| --- | --- | --- | --- |
| {id} | {score} | {below threshold / pre-existing / lint or CI catches it / unchanged line} | {finding} |

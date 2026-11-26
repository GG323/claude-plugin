# {title}: plan

Change `{change_id}` · Size: {size} · Status: {waiting for approval | approved on YYYY-MM-DD}

Every decision names its source and is marked **confirmed** (file and line, or doc link) or **inferred** (with the reason). Workbook statements are technology rules kept by `dev-workbook`, cited by ID, for example `csharp.patterns.004`; the first time an ID is cited, its text follows in quotes. Sources: user, project (a file in this repository), tool (a workbook statement), industry (a named public standard), or general reasoning. The dev settings are `AGENTS/settings.json`.

## Goal

{One or two sentences: what changes for whom, and why.}

## Out of scope

- {What this change will not do; "none" when nothing is excluded.}

## Scope and size

| Item | Kind | Fact | Evidence | Mark |
| --- | --- | --- | --- | --- |
| {item} | {caller / data / contract / test / untested / outside effect / convention / reuse / reproduction} | {fact} | {file:line, or the search run} | {confirmed / inferred: reason} |

**Size:** {Small / Medium / Large} - {one-line reason citing the riskiest fact}

## Decisions

| # | Decision | Source | Evidence | Mark | Confirmed by you |
| --- | --- | --- | --- | --- | --- |
| 1 | {decision} | {user / project / tool / industry / general} | {file:line, doc link, or workbook ID} | {confirmed / inferred: reason} | {yes, round N / not yet} |

## Architecture

{Components, what calls what, data flow, and what changes in each. A diagram when the shape branches or loops. Small changes: "unchanged" plus the touched component.}

## Tools and services

{Each tool, service, or integration in use or added, with its workbook; "none added" when unchanged.}

## Languages and frameworks

{Each language and framework touched, with its version and workbook.}

## Design details

{Per layer or component: the change, interfaces and contracts, data and migrations, error handling, and what is reused.}

## Verification: success and proof

| Criterion | Method | Passing result |
| --- | --- | --- |
| {observable outcome} | {unit / integration / e2e / manual check} | {the exact result that counts as a pass} |

- **End-to-end path:** {the real user path that proves the main journey, and how an agent drives it: browser, terminal, or HTTP calls}
- **Side effects to confirm:** {records saved, files written, messages sent to a test catcher; "none"}
- **Behaviour that must not change:** {existing behaviour the change could break; required for bug fixes}
- **Cannot be verified here:** {criteria left unverified and why; "none"}

## Risks

| Risk | Impact | Fallback |
| --- | --- | --- |
| {risk} | {Critical / Major / Minor} | {what we do if it happens} |

## Assumptions and open questions

- **Assumed:** {assumption and why}
- **Open:** {question still waiting for an answer; "none"}

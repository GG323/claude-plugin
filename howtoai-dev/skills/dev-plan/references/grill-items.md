# Grill items

## Items

What to ask; `grilling` supplies how. Ask an item only when the change touches it and no fact, workbook, setting, lesson, or convention answers it. The safest choice applies when the user will not decide.

| Layer | Item: ask when | Safest choice |
| --- | --- | --- |
| Architecture | Goal and success: always, unless the request states an observable outcome | the narrowest reading of the request |
| Architecture | Scope edge: the request could reach a neighbouring feature | leave the neighbour out |
| Architecture | Where it lives: a new component, or more than one place could own it | the component that already owns the behaviour |
| Architecture | Data and contracts: a schema, stored format, public API, or message changes | expand then contract: keep the old shape working |
| Architecture | Irreversible steps: a step a revert cannot undo | copy first, and a rollback step |
| Architecture | Outside effects: sends, payments, migrations on shared systems, external services | behind a flag, off by default |
| Architecture | Overall design (Large): after the architect proposals | the pragmatic proposal |
| Tools and services | New service or library the project does not use yet | what the project already runs |
| Tools and services | Hosting and environments: a new deployable, queue, or store | the existing hosting |
| Tools and services | Secrets and identities: a new credential or access | an existing identity with the least access; never a new secret in code |
| Tools and services | Test targets: a database, queue, or API the settings do not allow yet | a local or ephemeral target |
| Languages and frameworks | A new language or framework | the project's existing language |
| Languages and frameworks | A version change of a framework or runtime | stay on the current version |
| Languages and frameworks | A technology with no workbook and no precedent: run `dev-workbook` Create first, then ask the pattern | the pattern the official docs recommend |
| Details | Error behaviour users see | the pattern the product already uses |
| Details | Limits and numbers with no source ("5 failed logins in 15 minutes?") | the stricter value, from a workbook or industry source when one exists |
| Details | Agreed terms: a word means two things in the request and the code | propose one definition |
| Details | Done for a bug fix: narrow or broad | the narrow fix, the others as follow-ups |

## Defaults

State these with their source under **Assumed — tell me if wrong**; ask only when the facts contradict them:

- the existing stack, libraries, versions, and conventions (naming, structure, logging, error handling) the explorers found;
- the tracker and plan format from the settings (`tracker.kind`, Markdown when unset; `plan.publish`, `auto` when unset);
- the review weight from the size;
- tests in the project's existing frameworks, else the workbook's Testing statements;
- backwards compatibility kept for every existing contract.

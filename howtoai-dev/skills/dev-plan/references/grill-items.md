# Grill items

## Contents

- [How to use this list](#how-to-use-this-list)
- [Architecture](#architecture)
- [Tools and services](#tools-and-services)
- [Languages and frameworks](#languages-and-frameworks)
- [Details](#details)
- [Defaults](#defaults)
- [Skills and agents](#skills-and-agents)

## How to use this list

The `grilling` method supplies how to ask; this file supplies what. Ask the layers in this order, because an answer in one layer often removes questions in the next. An item is asked only when the change touches it and nothing in the scope facts, workbooks, settings, lessons, or code conventions answers it. Each row gives when to ask, an example question, and the safest choice for when the user will not decide.

## Architecture

| Crucial item | Ask when | Example question | Safest choice |
| --- | --- | --- | --- |
| Goal and success | Always, unless the request states an observable outcome | "What should a user see when this works?" | The narrowest reading of the request |
| Scope edge | The request could reach into a neighbouring feature | "Does 'export' include the scheduled exports, or only the button?" | Leave the neighbour out of scope |
| Where it lives | A new component, or more than one place could own it | "Should rate limiting sit in the API gateway or in the login handler?" | The component that already owns the behaviour |
| Data and contracts | A schema, stored format, public API, or message changes | "Can existing clients keep sending `email`, or do they all move to `login`?" | Expand then contract: keep the old shape working |
| Irreversible steps | A step a revert cannot undo | "The backfill rewrites 2 million rows; is a copy of the table first acceptable?" | Copy first, and a rollback step |
| Outside effects | Sends, payments, migrations on shared systems, external services | "Should the new reminder emails go to real users in the first release?" | Behind a flag, off by default |
| Overall design (Large) | After the architect proposals in draft | "Which design: minimal, clean, or pragmatic?" | The pragmatic proposal |

## Tools and services

| Crucial item | Ask when | Example question | Safest choice |
| --- | --- | --- | --- |
| New service or library | The plan needs something the project does not use yet | "Add Redis for the rate-limit counters, or keep them in the database?" | What the project already runs |
| Hosting and environments | A new deployable, queue, or store | "Where does the worker run: the existing App Service plan or a new container?" | The existing hosting |
| Secrets and identities | The change needs a new credential or access | "Which existing managed identity should the job use?" | An existing identity with the least access; never a new secret in code |
| Test targets | Tests need a database, queue, or API not yet allowed in the settings | "Run the integration tests against a Testcontainers database?" | A local or ephemeral target |

## Languages and frameworks

| Crucial item | Ask when | Example question | Safest choice |
| --- | --- | --- | --- |
| New language or framework | The plan brings one the project does not use | "Write the new tool in C# like the rest, or in Python?" | The project's existing language |
| Version change | The change needs a newer framework or runtime | "Upgrade to .NET 9 for this, or stay on .NET 8?" | Stay on the current version |
| Technology with no workbook | A technology with no workbook and no precedent | (run `dev-workbook` Create first, then ask the pattern) | The pattern the official docs recommend |

## Details

| Crucial item | Ask when | Example question | Safest choice |
| --- | --- | --- | --- |
| Error behaviour users see | A failure is visible to users | "When the limit is hit, show a wait time or a generic message?" | The pattern the product already uses |
| Limits and numbers | The plan needs a value with no source | "How many failed logins before the lockout: 5 in 15 minutes?" | The stricter value, from a workbook or industry source when one exists |
| Agreed terms | A word means two things in the request and the code | "By 'account', do you mean the tenant or the user?" | Propose one definition |
| Done for a bug fix | The fix could be narrow or broad | "Fix only the export timeout, or every job using the same client?" | The narrow fix, with the others listed as follow-ups |

## Defaults

State these, with their source, under **Assumed — tell me if wrong**; ask only when the facts contradict them:

- The existing stack, libraries, and versions.
- The existing conventions for naming, structure, logging, and error handling, as the explorers found them.
- The tracker and the plan format, from the settings (`tracker.kind`, Markdown when none is set; `plan.publish`, `auto` when none is set).
- The review weight from the size.
- Tests: the frameworks the project already uses; the workbook's Testing statements otherwise.
- Backwards compatibility kept for every existing contract.

## Skills and agents

- `grilling` - the method these items are asked with.
- `dev-workbook` - Create, for a technology with no workbook.
- No agents are used.

# Stage: draft

For a bug report, Scope and size has a `reproduction` row; when it has none, run scope's [Reproduce](scope.md#reproduce) section first.

## Architect proposals

Large only; Small and Medium skip to [Fill the plan](#fill-the-plan).

1. Start three general-purpose subagents in one message, one per stance in [architects.md](../references/architects.md). Each brief holds only the workspace path, the restated request, the Scope and size section, the answers and defaults from `questions.md`, the stance text, and the output format. Save each reply as it came to `<change folder>/raw/architects/<stance>.md`.
2. Compare them in one table (stance, shape in one line, files touched, new dependencies, main risk, effort), recommend one with the reason, and ask it as one `grilling` question in the architecture layer. Record what the user chose, combinations included, in `questions.md`.

## Fill the plan

Goal: a `plan.md` a reviewer and `dev-test` can act on with no other context.

- Fill every section from the scope facts, answers, defaults, and (Large) the chosen design. Keep every section; an empty one gets its stated placeholder ("none", "unchanged").
- **Small:** Goal, Out of scope, Scope and size, Decisions, Verification, Risks (one line will do), and Assumptions; Architecture, Tools and services, Languages and frameworks, and Design details say "unchanged" and name the touched component. **Medium:** every section in full. **Large:** every section, top-down by layer, with a component diagram when the shape branches or loops.
- **Decisions:** one row each, with source, evidence (file and line, doc link, or workbook ID), mark, and "yes, round N" when the user confirmed it or "not yet" for a stated default.
- **Design details:** the exact files, interfaces and contracts, data changes with migration and rollback, error handling, and what is reused. A data or contract change that cannot be undone has an expand-then-contract order or an explicit "irreversible" note in Risks.
- Set the status line to "waiting for approval".

## Verification

Every criterion lets `dev-test` write a test without asking: an observable outcome, its method (unit, integration, end-to-end, or manual check), and the exact result that passes. Also fill:

- **End-to-end path:** the real user path for the main journey, and how an agent drives it (browser, terminal, or HTTP).
- **Side effects:** records saved, files written, messages sent to a test catcher; or "none".
- **Behaviour that must not change:** required for a bug fix, with the regression it guards against.
- **Cannot be verified here:** what stays unverified and why; or "none".

Cite the workbook's Testing statements for the touched technologies by ID.

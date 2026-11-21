# Stage: draft

## Contents

- [Architect proposals](#architect-proposals)
- [Fill the plan](#fill-the-plan)
- [Verification](#verification)
- [Skills and agents](#skills-and-agents)

## Architect proposals

Large changes only; for Small and Medium, skip to [Fill the plan](#fill-the-plan).

1. Start three general-purpose subagents in one message, one per stance in [architects.md](../references/architects.md): minimal, clean, and pragmatic. Each brief gives the workspace path, the restated request, the Scope and size section of `plan.md`, the answers and defaults from `questions.md`, the workbook statements, the stance text, and the output format from that file. No other context. Save each reply as it came to `<change folder>/raw/architects/<stance>.md`.
2. Show the user the three designs as one comparison table (stance, shape in one line, files touched, new dependencies, main risk, effort) and recommend one, naming why it fits this change. Ask it as one `grilling` question in the architecture layer and record it in `questions.md`. The user may combine parts; record what they chose.

## Fill the plan

1. Fill every section of `plan.md` from the scope facts, the answers, the defaults, and, for Large, the chosen design. Keep every section; one with nothing to say gets its stated placeholder ("none", "unchanged").
2. **By size:**
   - **Small:** Goal, Out of scope, Scope and size, the Decisions that were made, Verification, Risks (one line is enough), and Assumptions. Architecture, Tools and services, Languages and frameworks, and Design details say "unchanged" and name the touched component.
   - **Medium:** every section in full.
   - **Large:** every section, written top-down by layer, with a diagram of the components when the shape branches or loops.
3. **Decisions:** one row per decision from grill and draft, with its source, evidence (file and line, doc link, or workbook ID), mark, and "yes, round N" when the user confirmed it, or "not yet" for a stated default.
4. **Design details** name the exact files to change or add, the interfaces and contracts, data changes with their migration and rollback, error handling, and what is reused. A data or contract change that cannot be undone has an expand-then-contract order or an explicit "irreversible" note in Risks.
5. Set the status line to "waiting for approval".

## Verification

Every criterion must let `dev-test` write a test without asking:

- Each criterion is an observable outcome, with its method (unit, integration, end-to-end, or manual check) and the exact result that counts as a pass.
- **End-to-end path:** the real user path that proves the main journey, and how an agent drives it: a browser, the terminal, or HTTP calls.
- **Side effects:** records saved, files written, messages sent to a test catcher; or "none".
- **Behaviour that must not change:** required for a bug fix, with the regression it guards against.
- Apply the workbook's Testing statements for the touched technologies and cite their IDs.
- **Cannot be verified here:** what is left unverified and why; "none" otherwise.

## Skills and agents

- `grilling` - the architecture question for a Large change.
- `dev-workbook` - the statements cited in the plan.
- Agents: three general-purpose subagents for the architect stances, Large only.

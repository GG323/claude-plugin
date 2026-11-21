# Route: set up a target

## Contents

- [Find what exists](#find-what-exists)
- [Get the workbooks](#get-the-workbooks)
- [Draft the target entry](#draft-the-target-entry)
- [Ask and write](#ask-and-write)
- [Skills and agents](#skills-and-agents)

## Find what exists

Entered from [SKILL.md](../SKILL.md#routes) when the target is not in the targets file.

1. `DEPLOY discover --workspace "<workspace>"`. It lists the project's container files, Kubernetes manifests, Helm charts, Kustomize folders, Terraform folders, CI files, deploy scripts, and hosting files, and the deploy CLIs on PATH.
2. For each CLI the target needs, read its state with read-only commands: its version, and its current context or account (for example `kubectl config get-contexts`, `docker context ls`). Name contexts and accounts only, never tokens.
3. When a CLI the target needs is missing, propose its install from the official source or the platform's package manager (for example `winget`), with its license, and wait for the user's yes; the user signs in to it themselves.
4. Read the project's README and its deploy files, so the entry describes what the project already does, not a guess.

## Get the workbooks

1. List the technologies the target uses: the runtime (for example `dotnet`), the packaging (`docker`), and the platform (`kubernetes`).
2. For each, `WORKBOOK resolve --workspace "<workspace>" --stage deploy --paths <the deploy files> --topics "Deployment and operations" Commands Pitfalls --markdown`. A technology in `missing` has no workbook yet: hand it to `dev-workbook`'s Create route, which finds or makes one from official sources after the user's yes.
3. Keep the statements that shape the steps: build and image rules, how the platform rolls out and rolls back, how its image store works, and how to read its failures.

## Draft the target entry

1. Fill an entry in the shape of [assets/target-example.json](../assets/target-example.json):
   - `technologies`: the list from the workbooks step.
   - `production`: ask the user when the target's name or tools do not say; a local cluster on this computer is usually not production, a shared server or cloud usually is.
   - `ready`: read-only commands that show the target answers (for example `kubectl --context <context> cluster-info`).
   - `steps`: in order, each with an `id`, the exact `command`, a `rollback` (a command, or `none: <why>`), and, for a rollout, a `watch` command that waits for it to finish.
   - `checks`: health URLs with the expected status and text, or read-only commands.
   - Every command names its context or account explicitly, so a run never lands on whatever context happens to be current.
2. When a deploy file is missing (for example no Kubernetes manifest), draft the smallest one that runs the app, from the workbook statements, and list it as a file to write.
3. `DEPLOY target write --workspace "<workspace>" --file "<entry.json>"` without `--write` validates the entry and prints the preview; fix every problem it lists.

## Ask and write

1. Show the user in one message: the target entry (steps, rollback, checks, production or not), each deploy file to write in full, and each install, with a recommendation. Wait for the yes; never assume one.
2. After the yes: write the approved deploy files, then `DEPLOY target write --workspace "<workspace>" --file "<entry.json>" --write`.
3. Go to the [Deploy](deploy.md) route with the new target.

## Skills and agents

- [SKILL.md](../SKILL.md) - the rules; [Deploy](deploy.md) - the next route; [scripts/deploy.py](../scripts/deploy.py) - discover and target.
- `dev-workbook` - Resolve and Create.
- No agents are used.

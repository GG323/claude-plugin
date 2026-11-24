# Route: set up a target

## Contents

- [Find what exists](#find-what-exists)
- [Get the workbooks](#get-the-workbooks)
- [Draft the target entry](#draft-the-target-entry)
- [Ask and write](#ask-and-write)
- [Skills and agents](#skills-and-agents)

## Find what exists

Entered from [SKILL.md](../SKILL.md#routes) when the target is not in the targets file. Ask everything this route needs in one message, in [Ask and write](#ask-and-write): the entry, the deploy files, any install, any workbook to make, and starting a stopped target.

1. `DEPLOY discover --workspace "<workspace>"`. It lists the project's container files, Kubernetes manifests, Helm charts, Kustomize folders, Terraform folders, CI files, deploy scripts, and hosting files, and the deploy CLIs on PATH.
2. For each CLI the target needs, read its state with read-only commands (where a stopped local target cannot answer, record its start commands and ask to run them in Ask and write): its version, and its current context or account (for example `kubectl config get-contexts`, `docker context ls`). Name contexts and accounts only, never tokens.
3. When a CLI the target needs is missing, propose its install from the official source or the platform's package manager (for example `winget`), with its license, and wait for the user's yes; the user signs in to it themselves.
4. Read the project's README and its deploy files, so the entry describes what the project already does, not a guess.

## Get the workbooks

1. List the technologies the target uses: the runtime (for example `dotnet`), the packaging (`docker`), and the platform (`kubernetes`).
2. `WORKBOOK resolve --workspace "<workspace>" --stage deploy --technologies <every technology in the list> --paths <the deploy files> --markdown`; naming the technologies matters, because a platform with no deploy files yet (no manifest) matches no path. A technology in `missing` has no workbook yet: list it for [Ask and write](#ask-and-write): `dev-workbook`'s Create route finds or makes it from official sources after the user's yes.
3. Keep the statements that shape the steps: build and image rules, how the platform rolls out and rolls back, how its image store works, and how to read its failures.

## Draft the target entry

1. Fill an entry in the shape of [assets/target-example.json](../assets/target-example.json):
   - `technologies`: the list from the workbooks step.
   - `production`: ask the user when the target's name or tools do not say; a local cluster on this computer is usually not production, a shared server or cloud usually is.
   - `shell`: the shell the commands are written for (`bash`, `powershell`, or `cmd`), when it matters, for example for commands that run through `wsl.exe`.
   - `ready`: read-only commands that show the target answers (for example `kubectl --context <context> cluster-info`).
   - `start`: for a local target that can be stopped (a cluster in a VM), the commands that start it, or `none: <why>`.
   - `steps`: in order, each with an `id`, the exact `command`, a `rollback` (a command, or `none: <why>`), and, for a rollout, a `watch` command that waits for it to finish. A step that is undone differently the first time (a first `apply` has no earlier version to go back to) says both in its rollback, for example `rollout undo ...; on the first deploy: delete -f ...`.
   - Values that change per run (an image tag) appear once, as a placeholder such as `{tag}` in every step and deploy file that uses them, so the build and the manifest can never disagree; the Deploy route fills them in.
   - `checks`: health URLs with the expected status and text, or read-only commands.
   - Every command names its context or account explicitly, so a run never lands on whatever context happens to be current.
2. When a deploy file is missing (for example no Kubernetes manifest), draft the smallest one that runs the app, from the workbook statements, and list it as a file to write (with the file tools, see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)).
3. Write the entry to `<entry.json>` (with the file tools, see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)), since it names real hosts, then `DEPLOY target write --workspace "<workspace>" --file "<entry.json>"` without `--write` validates the entry and prints the preview; fix every problem it lists.

## Ask and write

1. Show the user in one message: the target entry (steps, rollback, checks, production or not), each deploy file to write in full, each install, each workbook to make through `dev-workbook`'s Create route, and starting a stopped target, each with a recommendation. Wait for the yes; never assume one.
2. After the yes: make the approved workbooks (the Create route's own question is answered by this yes), add any statement they give that changes a step, write the approved deploy files, then `DEPLOY target write --workspace "<workspace>" --file "<entry.json>" --write`, and run the approved start commands.
3. Go to the [Deploy](deploy.md) route with the new target, passing each deploy file or folder you just wrote to its gate as `--new-file <path>`, so the first deploy is not stopped for them; tell the user to commit them with the next commit.

## Skills and agents

- [SKILL.md](../SKILL.md) - the rules; [Deploy](deploy.md) - the next route; [scripts/deploy.py](../scripts/deploy.py) - discover and target.
- `dev-workbook` - Resolve and Create.
- No agents are used.

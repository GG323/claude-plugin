# Route: set up a target

Done: after one approval message, the target's entry is in `targets.json`, its approved deploy files, workbooks, and installs are in place, and the first deploy starts. Everything this route needs from the user is asked once, in [Ask and write](#ask-and-write).

## Find what exists

1. `DEPLOY discover --workspace "<workspace>"` lists the project's deploy files (container files, Kubernetes manifests, Helm charts, Kustomize and Terraform folders, CI files, deploy scripts, hosting files) and the deploy CLIs on PATH.
2. Read each CLI's state the target needs with read-only commands: its version and its current context or account (for example `kubectl config get-contexts`, `docker context ls`). Name contexts and accounts only, never tokens. Where a stopped local target cannot answer, record its start commands to ask about in Ask and write.
3. A CLI the target needs is missing: propose its install from the official source or the platform's package manager (for example `winget`), with its license, and wait for the user's yes; the user signs in to it themselves.
4. Read the project's README and deploy files, so the entry describes what the project already does, not a guess.

## Get the workbooks

1. List the technologies the target uses: the runtime (for example `dotnet`), the packaging (`docker`), and the platform (`kubernetes`).
2. `WORKBOOK resolve --workspace "<workspace>" --stage deploy --technologies <every technology in the list> --paths <the deploy files> --markdown`. Name the technologies: a platform with no deploy files yet matches no path. A technology in `missing` has no workbook yet: list it for Ask and write, where `dev-workbook`'s Create route finds or makes it from official sources after the user's yes.
3. Keep the statements that shape the steps: build and image rules, how the platform rolls out and back, its image store, and how to read its failures.

## Draft the target entry

1. Fill an entry in the shape of [assets/target-example.json](../assets/target-example.json):
   - `technologies`: the list from the workbooks step.
   - `production`: ask the user when the target's name or tools do not say; a local cluster on this computer is usually not production, a shared server or cloud usually is.
   - `shell`: `bash`, `powershell`, or `cmd`, when it matters (for example for commands run through `wsl.exe`).
   - `ready`: read-only commands that show the target answers (for example `kubectl --context <context> cluster-info`).
   - `start`: for a local target that can be stopped (a cluster in a VM), the commands that start it, or `none: <why>`.
   - `steps`: in order, each with an `id`, the exact `command`, a `rollback` (a command, or `none: <why>`), and, for a rollout, a `watch` command that waits for it to finish. A step undone differently the first time says both, for example `rollout undo ...; on the first deploy: delete -f ...`.
   - Values that change per run (an image tag) appear as one placeholder such as `{tag}` in every step and deploy file that uses them, so the build and the manifest never disagree.
   - `checks`: health URLs with the expected status and text, or read-only commands.
   - Every command names its context or account, so a run never lands on whatever context is current.
2. When a deploy file is missing (for example no Kubernetes manifest), draft the smallest one that runs the app from the workbook statements, and list it as a file to write (with the file tools, see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)).
3. Write the entry to `<entry.json>` (with the file tools, see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)), since it names real hosts, then `DEPLOY target write --workspace "<workspace>" --file "<entry.json>"` without `--write` validates it and prints the preview; fix every problem it lists.

## Ask and write

1. Show the user in one message, each with a recommendation: the target entry (steps, rollback, checks, production or not), each deploy file to write in full, each install, each workbook to make, and starting a stopped target. Wait for the yes; never assume one.
2. After the yes: make the approved workbooks (this yes answers the Create route's own question), add any statement they give that changes a step, write the approved deploy files, run `DEPLOY target write --workspace "<workspace>" --file "<entry.json>" --write`, and run the approved start commands.
3. Go to [Deploy](deploy.md), passing each deploy file or folder you just wrote to its gate as `--new-file <path>`, so the first deploy is not stopped for them; tell the user to commit them with the next commit.

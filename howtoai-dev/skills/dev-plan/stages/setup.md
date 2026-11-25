# Stage: setup

## Settings

Goal: the workspace and its merged dev settings (`plan_folder`, `tracker`, `review`, `workbooks.technologies`).

1. `DEVCORE root --cwd "<the session's working directory>"`. With no workspace found, ask the user which folder it is and pass `--workspace` from then on.
2. `DEVCORE settings --workspace "<workspace>"`. When `configured` is false, run `dev-core`'s Setup route now (that section of its `SKILL.md`), then read the settings again.

## Change folder

Goal: one change folder, new or resumed.

1. Read `<workspace>/<plan_folder>/INDEX.md` when it exists. When the user named a change, or one at stage `plan` or `accept` matches the request, ask in one line whether to continue it. If yes, read `DEVCORE state "<folder>"` and its files, and resume at the first stage whose output is missing, then skip the rest of this stage except [Recall](#recall):

   | Missing | Resume at |
   | --- | --- |
   | `size` in state | [scope](scope.md) |
   | answers in `questions.md` for open crucial items | [grill](grill.md) |
   | `{placeholder}` text in `plan.md` | [draft](draft.md) |
   | no `plan-review-<n>.md`, or the stop rule not met | [review](review.md) |
   | a needed split with an empty `wi/` | [split](split.md) |
   | no plan approval in state | [accept](accept.md) |

2. Otherwise `DEVCORE new-change --workspace "<workspace>" --title "<short plain title from the request>"`, and say "Started change `<change-id>`."
3. Copy `dev-core`'s `plan.md` and `questions.md` templates (`../dev-core/assets/templates/`) into the folder with the file tools (see `dev-core`'s [Plan folder contract](../../dev-core/SKILL.md#plan-folder-contract)), filling only `{title}` and `{change_id}`. Add no sections: the templates are exempt from the title and contents rules.

## Recall

- Read `<workspace>/AGENTS/howtoai/dev/lessons.md` when it exists; keep the lessons that match the request, its areas, or its technologies, and cite them by ID where they shape a decision.
- From `INDEX.md`, check the open changes (not `done` or `dropped`) that may touch the same area. An overlap is a scope fact, for example "change `2026-11-12-session-cache` also edits `src/auth/`".

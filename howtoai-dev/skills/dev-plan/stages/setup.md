# Stage: setup

## Contents

- [Settings](#settings)
- [Change folder](#change-folder)
- [Recall](#recall)
- [Skills and agents](#skills-and-agents)

## Settings

1. Run `DEVCORE root --cwd "<the session's working directory>"` for the workspace. With no workspace found, ask the user which folder it is and pass `--workspace` from then on.
2. Run `DEVCORE settings --workspace "<workspace>"`. When `configured` is false, run `dev-core`'s Setup route now (read that section of `dev-core`'s `SKILL.md`), then run `DEVCORE settings` again. Keep the merged settings: `plan_folder`, `tracker`, `review`, and `workbooks.technologies` are used by later stages.

## Change folder

1. Read `<workspace>/<plan_folder>/INDEX.md` when it exists. When the user named a change, or a change at stage `plan` or `accept` has a title that matches the request, ask in one line whether to continue it. When they continue, read its `state.json` (`DEVCORE state "<folder>"`) and its files, and go on at the first stage whose output is missing:

   | Missing | Resume at |
   | --- | --- |
   | `size` in state | [scope](scope.md) |
   | answers in `questions.md` for open crucial items | [grill](grill.md) |
   | `plan.md` still has `{placeholder}` text | [draft](draft.md) |
   | no `plan-review-<n>.md`, or the loop's stop rule not met | [review](review.md) |
   | a split is needed and `wi/` is empty | [split](split.md) |
   | no plan approval in state | [accept](accept.md) |

   Skip the rest of this stage when resuming, except [Recall](#recall).
2. Otherwise start one: `DEVCORE new-change --workspace "<workspace>" --title "<short plain title from the request>"`. Tell the user in one line: "Started change `<change-id>`."
3. Copy `dev-core`'s templates `plan.md` and `questions.md` (in `../dev-core/assets/templates/` from this skill's folder) into the change folder, filling only `{title}` and `{change_id}` now. Keep each template's own shape: the templates are exempt from the workspace's title and contents-list rules, so add no sections to them.

## Recall

1. **Lessons.** Read `<workspace>/.howtoai/dev/lessons.md` when it exists. Search it for the words of the request, the areas it names, and the technologies in the settings; keep the lessons that apply and cite them by ID where they shape a decision.
2. **Open work.** From `INDEX.md`, list the changes not at `done` or `dropped`. Read the titles and the `plan.md` goals of those that may touch the same area. An overlap is a scope fact for the next stage, for example "change `2026-11-12-session-cache` also edits `src/auth/`".

## Skills and agents

- `dev-core` - settings, Setup, the change folder, and the templates.
- No agents are used in this stage.

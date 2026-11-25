"""Nontechnical-form sweep (from F1 fix batch 4).

Every line of INSTALL.md, and of dev-core SKILL.md's Setup route, that could hand the user a command, path, or file
name must either give its form "for a nontechnical user" on the same line, or be on AGENT_ONLY below with a reason.
A new or reworded line fails until someone classifies it. An AGENT_ONLY entry that matches no flagged line fails
too, so the list cannot go stale. Both files must also hold the precedence rule.

Run: py -3 -I -B nontechnical_sweep.py <howtoai-dev plugin folder> [--list]
Exit 0 when every flagged line passes, 1 otherwise.
"""
import os
import re
import sys

CLI = re.compile(r"(claude|git|gh|az|winget|docker|kubectl|py|python3?|dotnet|terraform|npm|pip)\s", re.I)
USER_FACING = re.compile(
    r"\b(user|users|ask|asks|offer|show|shown|say|says|tell|give|report|have them|they run|type)\b", re.I)
ALWAYS = re.compile(
    r"where it is stored|From `|What was left out|command for the user|`fix` lines?|show the command|shown as found", re.I)
DOTTED_KEY = re.compile(r"^[a-z_]+(\.[a-z_]+)+$")  # a setting key such as `environments.deny`
DOTFILE = re.compile(r"^\.[A-Za-z][\w.-]*$")  # a file such as `.gitignore`
FORM = "for a nontechnical user"
PRECEDENCE = "For a nontechnical user, the nontechnical form wins over any step's wording"

# Lines that are flagged but never reach a nontechnical user, each named by a phrase it holds.
AGENT_ONLY = {
    "Preview every write.": "a write preview keeps the exact path, the one exception the rules allow",
    "entry in `AGENTS.md` holds two required settings": "describes where the setting lives; no message text",
    "**Yes:** Git version control is on, so do not ask it separately": "dev mode on only, a developer choice",
    "The plugin lives in `<plugins folder>/howtoai-dev/`": "dev mode on only, a developer step",
    "**Git before links.**": "dev mode on only, a developer step",
    "**Links.** For each skill folder": "dev mode on only, a developer step",
    "**Hooks.** Plugin hooks load only from an installed plugin": "dev mode on only, a developer step",
    "Read the `dev hooks` item": "dev mode on only, a developer step",
    "These are the user's defaults for every workspace. Ask them only when": "the agent's condition for asking; the question names no file",
    "Show the values as a preview with `DEVCORE setup": "a write preview",
    "The project's tracker and its project": "the tracker's own identifiers, which the user gives",
    "**Project settings:** `DEVCORE setup": "a write preview, then the agent's own commands",
    "**Install record:** copy": "agent runs it; never shown to the user",
    "Hand the finished install to the `skill-builder` skill": "the agent's brief to skill-builder; never shown to the user",
    "Ask whether Git version control is on or off, recommending its current value": "turning dev mode off, a developer step",
    "When the pointer names another workspace, say that the links serve": "turning dev mode off, a developer step",
    "Hand the removal of the three hook registrations": "turning dev mode off, a developer step",
    "under `UserPromptSubmit`, matcher `*`": "the update-config brief for dev mode's hooks, a developer step",
    "the user's defaults in `~/.claude/howtoai/dev-settings.json` and the project's settings": "the output contract's file list; never shown to the user",
    "| `devmode.py` exits 1 with `needs_setting` |": "the agent's fix; the question is worded by the rules",
    "| `devmode.py link` refuses a destination |": "dev mode on only, a developer step",
    "Send requested changes or reported problems with this procedure": "feedback for whoever maintains the procedure",
    "When the user asks to set up or install `howtoai-dev`, follow the plugin's `INSTALL.md`": "the agent's routing; never shown to the user",
    "After the answers, show the settings as a preview in its own message": "a write preview",
    "**Gate commands:** the lint, format-check, and build": "a lookup the agent runs; recorded, never shown",
    "Safest choices when the user will not decide": "the agent's fallback choices; never shown to the user",
}


def handed(span):
    return (bool(CLI.match(span)) or bool(re.search(r"[/\\~<]|\.(md|json|ya?ml|py|txt|env)\b", span))
            or bool(DOTTED_KEY.match(span)) or bool(DOTFILE.match(span)))


def rows(plugin):
    for rel, section in (("INSTALL.md", None), ("skills/dev-core/SKILL.md", "Setup")):
        with open(os.path.join(plugin, rel), encoding="utf-8") as f:
            text = f.read()
        if section:
            found = re.search(rf"^### {section}\n(.*?)(?=^#{{2,3}} )", text, re.S | re.M)
            text = found.group(1) if found else ""
        yield rel, text


def check(plugin):
    flagged, used, problems = [], set(), []
    for rel, text in rows(plugin):
        if PRECEDENCE not in text:
            problems.append(f"{rel}: no precedence rule")
        for number, line in enumerate(text.splitlines(), 1):
            spans = re.findall(r"`([^`]+)`", line)
            if not ((USER_FACING.search(line) and any(handed(s) for s in spans)) or ALWAYS.search(line)):
                continue
            if FORM in line.lower():
                flagged.append(("form", rel, number, line))
                continue
            names = [phrase for phrase in AGENT_ONLY if phrase in line]
            if names:
                used.update(names)
                flagged.append(("agent", rel, number, line))
            else:
                flagged.append(("MISS", rel, number, line))
                problems.append(f"{rel}:{number}: no nontechnical form and not on AGENT_ONLY: {line.strip()[:160]}")
    for phrase in sorted(set(AGENT_ONLY) - used):
        problems.append(f"stale AGENT_ONLY entry, matches no flagged line: {phrase}")
    return flagged, problems


def main():
    plugin = os.path.abspath(sys.argv[1])
    flagged, problems = check(plugin)
    if "--list" in sys.argv:
        for kind, rel, number, line in flagged:
            print(f"{kind:5} {rel}:{number}: {line.strip()[:150]}")
    for p in problems:
        print("PROBLEM", p)
    print(f"flagged={len(flagged)} problems={len(problems)}")
    return 0 if flagged and not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())

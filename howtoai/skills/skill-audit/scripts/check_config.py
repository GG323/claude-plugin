"""Scripted checks of non-Markdown configuration for skill-audit.

Checks I5 to I9 from references/checks.md and prints the result as JSON:

  I5  settings.json and settings.local.json: valid JSON, known keys, permission
      modes, and enabled plugins that name a known marketplace.
  I6  permission rules in those files: rule syntax, tool names, and rules that
      Claude Code skips or never matches.
  I7  hooks (in settings files, a plugin's hooks/hooks.json, or a manifest):
      event names, handler types and fields, and the programs and scripts each
      command hook runs.
  I8  plugin and marketplace manifests (.claude-plugin/plugin.json and
      marketplace.json): valid JSON, required fields, names, and component paths.
  I9  MCP and LSP server definitions (.mcp.json, .lsp.json, and manifest
      mcpServers and lspServers): a command or URL per server, literal
      credentials, and packages or images that are not pinned to one version.

Commands that other settings run (statusLine, subagentStatusLine) are checked
under I5, and hooks declared in a skill's or agent's frontmatter under I7.
A package or image that is not pinned (npx, bunx, pnpx, npm exec, pnpm or yarn
dlx, uvx, uv tool run, uv run --with, or pipx run without an exact version;
docker without a version tag or @sha256 digest), also inside cmd /c, sh -c,
bash -c, or pwsh -c, is a suggestion in the user's own configuration and a
defect in a candidate, because the code that runs could change after the review
and a candidate cannot be pinned without editing it. In a candidate a docker
image needs an @sha256 digest (a tag can be moved) and docker compose is a defect.

Targets:
  --root <.claude folder>  the global folder (default ~/.claude) or a workspace's
                           .claude folder; for a workspace, plugin and marketplace
                           manifests and .mcp.json files anywhere in the workspace
                           are checked too, except under --exclude folders.
  --candidate <folder>     one isolated copy of a third-party tool that
                           skill-finder is vetting. Every config file in it is
                           checked; programs a hook or server needs are listed
                           under "needs" instead of being looked up on PATH,
                           because the candidate is not installed here.

Known keys, events, and rule forms follow the Claude Code docs as checked on
2026-11-09: https://code.claude.com/docs/en/settings-reference,
https://code.claude.com/docs/en/permissions, https://code.claude.com/docs/en/hooks,
https://code.claude.com/docs/en/plugins/manifest-reference, and
https://code.claude.com/docs/en/plugins/marketplace-reference. A key the docs add
later shows up as an unknown-key suggestion until the lists below are updated.

Reads files only; runs nothing it checks. Writes nothing.

Usage:
  py -3 check_config.py [--root <.claude folder> | --candidate <folder>]
                        [--exclude <folder> ...] [--as-of YYYY-MM-DD]
"""

import argparse
import datetime
import json
import os
import re
import shlex
import shutil
import sys

SETTINGS_FILES = ("settings.json", "settings.local.json")

# Top-level settings keys from the settings reference index.
SETTINGS_KEYS = set("""
$schema advisorModel agent agentPushNotifEnabled allowAllClaudeAiMcps allowClaudeInChromeWithManagedMcp
allowedChannelPlugins allowedHttpHookUrls allowedMcpServers allowedProviders allowManagedHooksOnly
allowManagedMcpServersOnly allowManagedPermissionRulesOnly alwaysThinkingEnabled apiKeyHelper
askUserQuestionTimeout appendPlugins attribution autoCompactEnabled autoCompactWindow autoConnectIde
autoContinueAtUsageLimit autoInstallIdeExtension autoMemoryDirectory autoMemoryEnabled autoMode
autoScrollEnabled autoUpdatesChannel availableModels availableModelsMatch awaySummaryEnabled awsAuthRefresh
awsCredentialExport axScreenReader bashEditDiffEnabled bashOutputMaxChars blockedMarketplaces
browserExternalPageTools channelsEnabled claudeInChromeDefaultEnabled claudeMd claudeMdExcludes
cleanupPeriodDays companyAnnouncements copyFullResponse copyOnSelect crossSessionInbound defaultShell
defaultToAgentsView deniedMcpServers deniedModels desktopSessionCleanupPeriodDays dialogExpiry diffTool
disableAgentView disableAllHooks disableArtifact disableAutoMode disableBrowserExternalNavigation
disableBundledSkills disableClaudeAiConnectors disableCommandPluginSources disableDeepLinkRegistration
disableDesktopLocalSessions disabledMcpjsonServers disableMobileSimulatorTools disableRemoteControl
disableSideloadFlags disableSkillShellExecution disableWorkflows editorMode effortLevel emojiCompletionEnabled
enableAllProjectMcpServers enableArtifact enabledMcpjsonServers enabledPlugins enableWorkflows
enforceAvailableModels env externalEditorContext extraKnownMarketplaces fallbackModel fastMode
fastModePerSessionOptIn feedbackDrafts feedbackSurveyRate fileCheckpointingEnabled fileSuggestion
footerLinksRegexes forceLoginGatewayUrl forceLoginMethod forceLoginOrgUUID forceRemoteSettingsRefresh
gatewayInternalNetworks gcpAuthRefresh hooks httpHookAllowedEnvVars idleCompaction includeCoAuthoredBy
includeGitInstructions inputNeededNotifEnabled isolatePeerMachines keybindingFlavor language
leftArrowOpensAgents managedMcpServers managedSourcesBehavior maxEffortLevel maxProseWidth minimumVersion
model modelOverrides modelPicker modelPricing modelSettings otelHeadersHelper outputStyle
parentSettingsBehavior permissionExplainerEnabled permissions plansDirectory pluginConfigs
pluginSuggestionMarketplaces pluginTrustMessage policyHelper preferredNotifChannel prefersReducedMotion
prependPlugins processWrapper promptCacheTtl promptSuggestionEnabled prStatusFooterEnabled prUrlTemplate
remote remoteControlAtStartup requiredMaximumVersion requiredMinimumVersion respectGitignore
respondToBashCommands sandbox showClearContextOnPlanAccept showThinkingSummaries showTurnDuration
skillListingBudgetFraction skillListingMaxDescChars skillOverrides skipAutoPermissionPrompt
skipDangerousModePermissionPrompt skipWebFetchPreflight spellcheck spinnerTipsEnabled spinnerTipsOverride
spinnerVerbs sshConfigs sshHostAllowlist sshHostCommands statusLine strictKnownMarketplaces
strictPluginOnlyCustomization subagentPromptCacheTtl subagentStatusLine switchModelsOnFlag syncClaudeAiPlugins
syncClaudeAiSkills syntaxHighlightingDisabled taskOutputMaxChars teammateDefaultModel teammateMode
terminalProgressBarEnabled terminalTitleFromRename theme timeFormat timeZone tui ultracode
useAutoModeDuringPlan verbose viewMode vimInsertModeRemaps voice voiceEnabled wheelScrollAccelerationEnabled
workflowKeywordTriggerEnabled workflowSizeGuideline worktree wslInheritsWindowsSettings
""".split())

PERMISSION_KEYS = {"allow", "ask", "deny", "additionalDirectories", "defaultMode", "disableBypassPermissionsMode",
                   "disableAutoMode", "blockReadsOutsideWorkingDirectories", "blockWritesOutsideWorkingDirectories"}
PERMISSION_MODES = {"default", "manual", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions"}
USER_ONLY_MODES = {"auto", "bypassPermissions"}  # no effect from project or local settings

# Canonical tool names from the tools reference, plus Cd (the /cd command's rules)
# and legacy MultiEdit, which permission rules still accept.
TOOLS = set("""
Agent Artifact AskUserQuestion Bash Cd CronCreate CronDelete CronList Edit EndConversation EnterPlanMode
EnterWorktree ExitPlanMode ExitWorktree Glob Grep LSP ListAgents ListMcpResourcesTool Monitor MultiEdit
NotebookEdit PowerShell PushNotification Read ReadMcpResourceTool RemoteTrigger ReportFindings ScheduleWakeup
SendFeedback SendMessage SendUserFile ShareOnboardingGuide Skill SubagentHandback TaskCreate TaskGet TaskList
TaskOutput TaskStop TaskUpdate TodoWrite ToolSearch WaitForMcpServers WebFetch WebSearch Workflow Write
""".split())
NON_MATCHING_PATH_TOOLS = {"Write": "Edit", "NotebookEdit": "Edit", "MultiEdit": "Edit", "Glob": "Read", "Grep": "Read"}

HOOK_EVENTS = set("""
SessionStart Setup UserPromptSubmit UserPromptExpansion PreToolUse PermissionRequest PermissionDenied
PostToolUse PostToolUseFailure PostToolBatch Notification MessageDisplay SubagentStart SubagentStop
TaskCreated TaskCompleted Stop StopFailure TeammateIdle InstructionsLoaded ConfigChange CwdChanged
DirectoryAdded FileChanged WorktreeCreate WorktreeRemove PreCompact PostCompact PreModelSwitch
PostModelSwitch Elicitation ElicitationResult SessionEnd
""".split())
HOOK_REQUIRED = {"command": ["command"], "http": ["url"], "mcp_tool": ["server", "tool"],
                 "prompt": ["prompt"], "agent": ["prompt"]}
SHELL_WORDS = {"cd", "echo", "exit", "test", "[", "true", "false", "export", "source", ".", "set", "exec",
               "if", "then", "fi", "else", "for", "do", "done", "while", "env", "printf", "read", "cat"}
SCRIPT_EXT = re.compile(r"\.(py|sh|bash|js|mjs|cjs|ts|tsx|ps1|rb|pl|cmd|bat)$", re.I)

PLUGIN_KEYS = {"$schema", "name", "displayName", "version", "description", "author", "homepage", "repository",
               "license", "keywords", "metadata", "icon", "documentationUrl", "supportUrl", "privacyPolicyUrl",
               "termsOfServiceUrl", "defaultEnabled", "dependencies", "settings", "userConfig", "types",
               "channels", "skills", "commands", "agents", "hooks", "mcpServers", "lspServers", "outputStyles",
               "workflows", "experimental"}
PLUGIN_PATH_KEYS = ("skills", "commands", "agents", "hooks", "mcpServers", "lspServers", "outputStyles",
                    "workflows", "types")
RESERVED_PLUGIN = re.compile(r"^(claude|anthropic|anthropics|cc-plugin)-|^(claude|anthropic|anthropics|claude-code|claude-mods)$"
                             r"|official[-_. ]*(claude|anthropic)|(claude|anthropic)[-_. ]*official", re.I)
MARKET_KEYS = {"$schema", "name", "owner", "plugins", "description", "version", "metadata",
               "forceRemoveDeletedPlugins", "allowCrossMarketplaceDependenciesOn", "renames"}
SOURCE_REQUIRED = {"github": ["repo"], "url": ["url"], "git-subdir": ["url", "path"], "npm": ["package"],
                   "archive": ["url"], "command": ["command"]}
ID_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

NPX_LIKE = {"npx", "bunx", "pnpx"}
DOCKER_LIKE = {"docker", "podman"}
DOCKER_VALUE_FLAGS = set("""
-e --env -v --volume --name -p --publish --network --net --entrypoint --mount -w --workdir -u --user --env-file
-l --label --platform --add-host --cap-add --cap-drop --device --dns --hostname -h --memory -m --cpus --restart
--pull --tmpfs --ulimit --log-driver --log-opt --security-opt --ipc --pid --gpus --runtime --shm-size
""".split())
EXACT_VERSION = re.compile(r"^v?\d+\.\d+\.\d+([-+][\w.]+)?$")
SHELL_WRAPPERS = {"sh", "bash", "zsh", "dash", "ksh", "pwsh", "powershell"}
SHELL_C_FLAGS = {"-c", "-lc", "-ic", "-command"}  # compared lower-cased, so -Command too


def npm_pinned(spec):
    name_ver = spec[1:] if spec.startswith("@") else spec
    return "@" in name_ver and bool(EXACT_VERSION.match(name_ver.rsplit("@", 1)[1]))


def py_pinned(spec):
    """A Python requirement pinned to one version (pkg==1.2.3), or an npm-style pkg@1.2.3."""
    return bool("==" in spec and EXACT_VERSION.match(spec.split("==", 1)[1].split(";", 1)[0].strip())) or npm_pinned(spec)


def split_inner(text):
    """The commands in a shell string a wrapper runs (cmd /c, sh -c, pwsh -Command), as word lists."""
    out = []
    for seg in re.split(r"\|\||&&|[|;&]", text):
        try:
            words = shlex.split(seg.replace("\\", "/"), posix=True)
        except ValueError:
            words = seg.split()
        while words and re.match(r"^\w+=", words[0]):
            words.pop(0)
        if words:
            out.append(words)
    return out


def package_spec(args, flags):
    """The package specs a runner downloads: values of the package flags, else the first positional word."""
    specs, i = [], 0
    while i < len(args):
        a = args[i]
        if a in flags:
            if i + 1 < len(args):
                specs.append(args[i + 1])
            i += 2
            continue
        hit = next((f for f in flags if a.startswith(f + "=")), None)
        if hit:
            specs.append(a.split("=", 1)[1])
            i += 1
            continue
        if a.startswith("-"):
            i += 1
            continue
        return specs or [a]
    return specs


def unpinned(program, args, candidate=False, depth=0):
    """'npx pkg' style text when a launcher runs a package or image not pinned to one version, else None.
    Wrappers (cmd /c, sh/bash/pwsh -c) are unwrapped and the command inside is checked. In a candidate a
    docker image needs an @sha256 digest (a tag can be moved) and docker compose always fails."""
    base = re.sub(r"\.(cmd|exe|bat|ps1)$", "", os.path.basename(str(program).replace("\\", "/")).lower())
    args = [str(a) for a in args]
    if depth > 4:
        return None
    low = [a.lower() for a in args]
    inner = None
    if base == "cmd":
        k = next((i for i, a in enumerate(low) if a in ("/c", "/k", "/s/c", "/d/c")), None)
        if k is not None:
            inner = " ".join(args[k + 1:])
    elif base in SHELL_WRAPPERS:
        k = next((i for i, a in enumerate(low) if a in SHELL_C_FLAGS), None)
        if k is not None:
            inner = " ".join(args[k + 1:])
    if inner is not None:
        for words in split_inner(inner):
            text = unpinned(words[0], words[1:], candidate, depth + 1)
            if text:
                return text
        return None
    if base == "env":
        rest = [a for a in args if not re.match(r"^\w+=", a) and not a.startswith("-")]
        return unpinned(rest[0], rest[1:], candidate, depth + 1) if rest else None
    # Runners that are a subcommand of another tool, rewritten to the plain runner form
    if base == "npm" and low[:1] in (["exec"], ["x"]):
        base, args = "npx", args[1:]
    elif base in ("pnpm", "yarn") and low[:1] == ["dlx"]:
        base, args = "%s dlx" % base, args[1:]
    elif base == "bun" and low[:1] == ["x"]:
        base, args = "bunx", args[1:]
    elif base == "uv" and low[:2] == ["tool", "run"]:
        base, args = "uvx", args[2:]
    elif base == "pipx" and low[:1] == ["run"]:
        base, args = "pipx run", args[1:]
    elif base == "uv" and low[:1] == ["run"]:
        withs = [w for i, a in enumerate(args) for w in
                 ([args[i + 1]] if a == "--with" and i + 1 < len(args) else [a.split("=", 1)[1]] if a.startswith("--with=") else [])]
        bad = [w for w in withs if not all(py_pinned(x.strip()) for x in w.split(",") if x.strip())]
        return "uv run --with %s" % bad[0] if bad else None
    if base in NPX_LIKE or base in ("pnpm dlx", "yarn dlx"):
        specs = package_spec(args, ("-p", "--package"))
        bad = [s for s in specs if not npm_pinned(s)]
        return "%s %s" % (base, bad[0]) if bad else None
    if base in ("uvx", "pipx run"):
        specs = package_spec(args, ("--from", "--spec", "--with"))
        bad = [s for s in specs if not py_pinned(s)]
        return "%s %s" % (base, bad[0]) if bad else None
    if base == "docker-compose" or (base in DOCKER_LIKE and low[:1] == ["compose"]):
        return "%s (images set in a compose file)" % (base if base == "docker-compose" else base + " compose") if candidate else None
    if base in DOCKER_LIKE and low[:1] in (["run"], ["pull"], ["create"]):
        i = 1
        while i < len(args):
            a = args[i]
            if a.startswith("-"):
                i += 2 if (a in DOCKER_VALUE_FLAGS and "=" not in a) else 1
                continue
            if "@sha256:" in a:
                return None
            last = a.rsplit("/", 1)[-1]
            tag = last.split(":", 1)[1] if ":" in last else ""
            if tag and tag != "latest" and not candidate:
                return None
            return "%s %s%s" % (base, a, " (a tag can be moved; a candidate needs an @sha256 digest)" if candidate and tag and tag != "latest" else "")
        return None
    return None


SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{6,}|ghp_[A-Za-z0-9]{10,}|github_pat_\w{10,}|xox[abp]-[\w-]{10,}|AKIA[0-9A-Z]{16}"
                    r"|Bearer\s+[A-Za-z0-9._-]{8,})")
SECRET_NAME = re.compile(r"(token|secret|password|passwd|api[_-]?key|authorization)", re.I)


class Config:
    def __init__(self, args):
        self.args = args
        self.candidate = bool(args.candidate)
        self.root = os.path.abspath(os.path.expanduser(args.candidate or args.root))
        default = os.path.abspath(os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude"))
        self.is_global = not self.candidate and self.root == default
        self.workspace = None
        if not self.candidate and not self.is_global and os.path.basename(self.root) == ".claude":
            self.workspace = os.path.dirname(self.root)
        self.excludes = [os.path.abspath(os.path.expanduser(x)) for x in args.exclude or []]
        self.findings, self.checked, self.needs, self.skipped = [], [], set(), []
        self.texts = {}
        self.done = set()  # config files already checked, so a file a manifest also names is checked once
        self.cmd_check, self.cmd_label = "I7", "Hook"

    # Output helpers --------------------------------------------------------

    def show(self, path):
        real = os.path.abspath(path)
        base = self.workspace or self.root
        if self.candidate or self.workspace:
            if real.startswith(base + os.sep):
                return os.path.relpath(real, base).replace(os.sep, "/")
        if self.is_global and real.startswith(self.root + os.sep):
            label = "~/.claude" if self.root == os.path.abspath(os.path.expanduser("~/.claude")) else self.root.replace(os.sep, "/")
            return label + "/" + os.path.relpath(real, self.root).replace(os.sep, "/")
        return real.replace(os.sep, "/")

    def line_of(self, path, needle):
        text = self.texts.get(path, "")
        i = text.find(needle) if needle else -1
        return None if i < 0 else text.count("\n", 0, i) + 1

    def find(self, check, path, message, needle=None, kind="defect"):
        self.findings.append({"check": check, "type": kind, "file": self.show(path),
                              "line": self.line_of(path, needle), "message": message})

    def load(self, path, check):
        try:
            with open(path, encoding="utf-8-sig") as f:
                text = f.read()
        except OSError as e:
            self.find(check, path, "Cannot read the file: %s" % e)
            return None
        self.texts[path] = text
        self.checked.append(self.show(path))
        try:
            return json.loads(text)
        except ValueError as e:
            self.findings.append({"check": check, "type": "defect", "file": self.show(path),
                                  "line": getattr(e, "lineno", None), "message": "Not valid JSON: %s" % e})
            return None

    # I5 and I6: settings files and permission rules ------------------------

    def settings(self, path, scope):
        data = self.load(path, "I5")
        if data is None:
            return
        if not isinstance(data, dict):
            self.find("I5", path, "A settings file holds one JSON object.")
            return
        for key in data:
            if key not in SETTINGS_KEYS:
                self.find("I5", path, "Unknown settings key '%s' (not in the settings reference); a typo is ignored "
                          "silently." % key, '"%s"' % key, "suggestion")
        perms = data.get("permissions")
        if perms is not None:
            if not isinstance(perms, dict):
                self.find("I5", path, "'permissions' must be an object.", '"permissions"')
            else:
                for key in perms:
                    if key not in PERMISSION_KEYS:
                        self.find("I5", path, "Unknown permissions key '%s'." % key, '"%s"' % key, "suggestion")
                mode = perms.get("defaultMode")
                if mode is not None and mode not in PERMISSION_MODES:
                    self.find("I5", path, "permissions.defaultMode '%s' is not a permission mode (%s)."
                              % (mode, ", ".join(sorted(PERMISSION_MODES))), '"defaultMode"')
                elif mode in USER_ONLY_MODES and scope != "user":
                    self.find("I5", path, "permissions.defaultMode '%s' has no effect from %s settings; set it in "
                              "~/.claude/settings.json or pass --permission-mode." % (mode, scope), '"defaultMode"')
                for kind in ("allow", "ask", "deny"):
                    rules = perms.get(kind)
                    if rules is None:
                        continue
                    if not isinstance(rules, list) or not all(isinstance(r, str) for r in rules):
                        self.find("I6", path, "permissions.%s must be a list of rule strings." % kind, '"%s"' % kind)
                        continue
                    for rule in rules:
                        self.rule(path, kind, rule)
        base = self.workspace if scope != "user" else None
        proot = self.root if self.candidate else None  # a candidate's own paths resolve inside it
        if "hooks" in data:
            self.hooks(path, data["hooks"], plugin_root=proot, project_root=base)
        for key in ("statusLine", "subagentStatusLine"):
            sl = data.get(key)
            if isinstance(sl, dict) and isinstance(sl.get("command"), str):
                self.run_as("I5", key, self.command, path, sl["command"], None, proot, base)
        self.enabled_plugins(path, data)

    def run_as(self, check, label, fn, *args):
        """Run a command check under another check ID and label (status lines, LSP and MCP servers)."""
        saved = self.cmd_check, self.cmd_label
        self.cmd_check, self.cmd_label = check, label
        try:
            fn(*args)
        finally:
            self.cmd_check, self.cmd_label = saved

    def first_time(self, path):
        key = os.path.normcase(os.path.realpath(path))
        if key in self.done:
            return False
        self.done.add(key)
        return True

    def pin(self, path, program, args, needle, what, check=None):
        text = unpinned(program, args, self.candidate)
        if not text:
            return
        check = check or self.cmd_check
        if self.candidate:
            self.find(check, path, "%s runs '%s' without one exact version, so the code that runs "
                      "can change after review; a candidate cannot be pinned without editing it." % (what, text), needle)
        else:
            self.find(check, path, "%s runs '%s' without one exact version; pin it so the code "
                      "that runs does not change unnoticed." % (what, text), needle, "suggestion")

    def rule(self, path, kind, rule):
        needle = json.dumps(rule)
        m = re.match(r"^([^()\s]+)(?:\((.*)\))?$", rule.strip(), re.S)
        if not m or rule != rule.strip():
            self.find("I6", path, "Rule '%s' is not in the form Tool or Tool(specifier)." % rule, needle)
            return
        tool, spec = m.group(1), m.group(2)
        if tool.startswith("mcp__"):
            if spec is not None:
                self.find("I6", path, "Claude Code skips an mcp__ rule with parentheses: '%s'. Name the tool as "
                          "mcp__<server>__<tool>." % rule, needle)
            elif kind == "allow" and re.match(r"^mcp__[^_]*[*?]", tool):
                self.find("I6", path, "An allow rule needs a literal mcp__<server>__ prefix before a wildcard; "
                          "'%s' is skipped." % rule, needle)
            return
        if any(c in tool for c in "*?"):
            if kind == "allow":
                self.find("I6", path, "Allow rules accept tool-name wildcards only after mcp__<server>__; '%s' is "
                          "skipped and approves nothing." % rule, needle)
            return
        if tool not in TOOLS:
            self.find("I6", path, "'%s' is not a built-in tool name in the tools reference; the rule matches "
                      "nothing unless the name is new." % tool, needle, "suggestion")
            return
        if spec is None:
            return
        if tool in NON_MATCHING_PATH_TOOLS and spec.strip() not in ("*", ""):
            self.find("I6", path, "'%s' never matches: file permissions are checked against %s(path) rules. "
                      "Write %s(%s) instead." % (rule, NON_MATCHING_PATH_TOOLS[tool], NON_MATCHING_PATH_TOOLS[tool], spec), needle)
        if tool in ("Bash", "PowerShell"):
            if ":*" in spec and not spec.endswith(":*"):
                self.find("I6", path, "':*' works only at the end of a pattern; in '%s' the colon is literal." % rule, needle)
            words = spec.split()
            if kind == "allow" and len(words) >= 3 and words[1] == "*" and words[0] != "*":
                self.find("I6", path, "Allow rule '%s' has a * before the subcommand, so it allows every %s "
                          "subcommand; put the * after the subcommand." % (rule, words[0]), needle)
        if tool == "WebFetch" and spec and not spec.startswith("domain:"):
            self.find("I6", path, "WebFetch rules take the form WebFetch(domain:<host>); '%s' matches nothing." % rule, needle)

    def enabled_plugins(self, path, data):
        ep = data.get("enabledPlugins")
        if ep is None:
            return
        if not isinstance(ep, dict):
            self.find("I5", path, "'enabledPlugins' must be an object of \"plugin@marketplace\": true/false.", '"enabledPlugins"')
            return
        known = set((data.get("extraKnownMarketplaces") or {}).keys())
        km = os.path.join(self.root if self.is_global else os.path.expanduser("~/.claude"), "plugins", "known_marketplaces.json")
        try:
            with open(km, encoding="utf-8") as f:
                known |= set(json.load(f).keys())
        except (OSError, ValueError):
            pass
        for pid in ep:
            if "@" not in pid:
                self.find("I5", path, "enabledPlugins entry '%s' is not in the form plugin@marketplace." % pid, json.dumps(pid))
            elif self.is_global and known and pid.rsplit("@", 1)[1] not in known:
                self.find("I5", path, "enabledPlugins entry '%s' names a marketplace that is not added "
                          "(not in known_marketplaces.json or extraKnownMarketplaces)." % pid, json.dumps(pid))

    # I7: hooks --------------------------------------------------------------

    def hooks(self, path, hooks, plugin_root, project_root):
        needle = '"hooks"'
        if not isinstance(hooks, dict):
            self.find("I7", path, "'hooks' must be an object of event names.", needle)
            return
        for event, groups in hooks.items():
            if event not in HOOK_EVENTS:
                self.find("I7", path, "Unknown hook event '%s'; Claude Code skips it." % event, '"%s"' % event)
                continue
            if not isinstance(groups, list):
                self.find("I7", path, "Hook event '%s' must hold a list of matcher groups." % event, '"%s"' % event)
                continue
            for g in groups:
                if not isinstance(g, dict) or not isinstance(g.get("hooks"), list):
                    self.find("I7", path, "A matcher group under '%s' needs a 'hooks' list." % event, '"%s"' % event)
                    continue
                for h in g["hooks"]:
                    self.handler(path, event, h, plugin_root, project_root)

    def handler(self, path, event, h, plugin_root, project_root):
        if not isinstance(h, dict):
            self.find("I7", path, "A hook under '%s' must be an object." % event, '"%s"' % event)
            return
        t = h.get("type")
        if t not in HOOK_REQUIRED:
            self.find("I7", path, "Hook type '%s' under '%s' is not one of %s." % (t, event, ", ".join(sorted(HOOK_REQUIRED))),
                      '"type"')
            return
        for field in HOOK_REQUIRED[t]:
            if not isinstance(h.get(field), str) or not h[field].strip():
                self.find("I7", path, "A '%s' hook under '%s' needs '%s'." % (t, event, field), '"type": "%s"' % t)
        if t == "command" and isinstance(h.get("command"), str):
            self.command(path, h["command"], h.get("args"), plugin_root, project_root)

    def expand(self, text, plugin_root, project_root):
        plugin_root = plugin_root and plugin_root.replace(os.sep, "/")
        project_root = project_root and project_root.replace(os.sep, "/")
        text = re.sub(r"\\(?=[A-Za-z0-9_ .-])", "/", text)  # Windows separators; shlex would drop them
        text = text.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root or "\x00plugin").replace("$CLAUDE_PLUGIN_ROOT", plugin_root or "\x00plugin")
        text = text.replace("${CLAUDE_PROJECT_DIR}", project_root or "\x00project").replace("$CLAUDE_PROJECT_DIR", project_root or "\x00project")
        text = text.replace("${HOME}", os.path.expanduser("~")).replace("$HOME", os.path.expanduser("~"))
        return text

    def command(self, path, command, args, plugin_root, project_root):
        """The programs and bundled scripts a command hook runs must exist."""
        needle = json.dumps(command)[1:30]
        segments = re.split(r"\|\||&&|[|;]", command) if args is None else [command]
        for seg in segments:
            try:
                words = shlex.split(self.expand(seg, plugin_root, project_root), posix=True)
            except ValueError:
                self.find(self.cmd_check, path, "%s command does not parse as a shell command: %s" % (self.cmd_label, command), needle)
                return
            if args is not None:
                words += [self.expand(str(a), plugin_root, project_root) for a in args]
            while words and re.match(r"^\w+=", words[0]):
                words.pop(0)  # VAR=value prefixes
            if not words:
                continue
            program, rest = words[0], words[1:]
            if program not in SHELL_WORDS:
                self.program(path, program, needle)
            self.pin(path, program, rest, needle, self.cmd_label)
            for w in rest:
                if "\x00" in w:
                    continue  # a placeholder this target cannot resolve (no plugin or project root)
                if SCRIPT_EXT.search(w) and ("/" in w or "\\" in w) and not w.startswith("-"):
                    self.file_exists(path, os.path.expanduser(w), needle, "script")

    def program(self, path, program, needle):
        if "\x00" in program:
            return
        if "/" in program or "\\" in program:
            self.file_exists(path, os.path.expanduser(program), needle, "program")
        elif self.candidate:
            self.needs.add(program)
        elif shutil.which(program) is None:
            self.find(self.cmd_check, path, "%s '%s' is not found on PATH on this computer, so it fails." % (self.cmd_label, program), needle)

    def file_exists(self, path, target, needle, what):
        if not os.path.isabs(target):
            return  # relative to the session's working directory; not checkable here
        if self.candidate and not os.path.abspath(target).startswith(self.root + os.sep):
            self.needs.add(target.replace(os.sep, "/"))
            return
        if not os.path.exists(target):
            self.find(self.cmd_check, path, "%s %s does not exist: %s" % (self.cmd_label, what, self.show(target)), needle)

    # I8: plugin and marketplace manifests ------------------------------------

    def plugin(self, manifest):
        root = os.path.dirname(os.path.dirname(manifest))
        data = self.load(manifest, "I8")
        if data is None:
            return
        if not isinstance(data, dict):
            self.find("I8", manifest, "plugin.json holds one JSON object.")
            return
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            self.find("I8", manifest, "plugin.json has no 'name', the one required field.")
        else:
            if re.search(r"[\s@:/\\]", name):
                self.find("I8", manifest, "Plugin name '%s' contains spaces, @, :, or path separators." % name, '"name"')
            elif not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                self.find("I8", manifest, "Plugin name '%s' is not kebab-case." % name, '"name"', "suggestion")
            if RESERVED_PLUGIN.search(name):
                self.find("I8", manifest, "Plugin name '%s' passes as one of Anthropic's own; validation refuses it." % name, '"name"')
        for key in data:
            if key not in PLUGIN_KEYS:
                self.find("I8", manifest, "Unknown plugin.json field '%s'; Claude Code strips it." % key, '"%s"' % key, "suggestion")
        author = data.get("author")
        if author is not None and not (isinstance(author, dict) and isinstance(author.get("name"), str) and author["name"].strip()):
            self.find("I8", manifest, "'author' must be an object with a 'name'.", '"author"')
        hp = data.get("homepage")
        if hp is not None and not (isinstance(hp, str) and re.match(r"^[a-z][a-z0-9+.-]*://\S+$", hp, re.I)):
            self.find("I8", manifest, "'homepage' must parse as a URL, or the plugin fails to load.", '"homepage"')
        exp = data.get("experimental") if isinstance(data.get("experimental"), dict) else {}
        for key in PLUGIN_PATH_KEYS:
            if key in data:
                self.component_paths(manifest, root, key, data[key])
        for key in ("themes", "monitors"):
            if key in exp:
                self.component_paths(manifest, root, "experimental." + key, exp[key])
        if isinstance(data.get("hooks"), dict):
            self.hooks(manifest, data["hooks"], root, self.workspace)
        if isinstance(data.get("mcpServers"), dict):
            self.mcp_servers(manifest, data["mcpServers"], root)
        if isinstance(data.get("lspServers"), dict):
            self.lsp_servers(manifest, data["lspServers"], root)
        lsp = os.path.join(root, ".lsp.json")
        if os.path.isfile(lsp):
            self.lsp_file(lsp, root)
        hooks_file = os.path.join(root, "hooks", "hooks.json")
        if os.path.isfile(hooks_file):
            self.hooks_file(hooks_file, root)
        mcp = os.path.join(root, ".mcp.json")
        if os.path.isfile(mcp):
            self.mcp_file(mcp, root)

    def component_paths(self, manifest, root, key, value):
        items = value if isinstance(value, list) else [value]
        for v in items:
            if not isinstance(v, str):
                continue  # inline config; hooks and mcpServers are checked on their own
            if key == "mcpServers" and v.startswith("https://"):
                continue
            if key == "skills" and v in (".", "./"):
                continue
            if not v.startswith("./"):
                self.find("I8", manifest, "Component path '%s' under '%s' must start with ./" % (v, key), json.dumps(v))
                continue
            if ".." in v.split("/"):
                self.find("I8", manifest, "Component path '%s' contains '..'; validation fails it." % v, json.dumps(v))
                continue
            target = os.path.normpath(os.path.join(root, v))
            if not os.path.exists(target):
                self.find("I8", manifest, "Component path not found: %s" % v, json.dumps(v))
            elif key == "hooks" and target.endswith(".json"):
                self.hooks_file(target, root)
            elif key == "mcpServers" and target.endswith(".json"):
                self.mcp_file(target, root)
            elif key == "lspServers" and target.endswith(".json"):
                self.lsp_file(target, root)

    def lsp_file(self, path, root):
        if not self.first_time(path):
            return
        data = self.load(path, "I9")
        if isinstance(data, dict):
            self.lsp_servers(path, data, root)

    def lsp_servers(self, path, servers, root):
        for name, s in servers.items():
            if not isinstance(s, dict) or not isinstance(s.get("command"), str):
                self.find("I9", path, "LSP server '%s' needs a 'command'." % name, '"%s"' % name)
                continue
            self.run_as("I9", "LSP server '%s'" % name, self.command, path, s["command"], s.get("args") or [], root, self.workspace)

    def frontmatter_hooks(self, path, plugin_root):
        """Hooks a skill or agent declares in its frontmatter run while it is active; check their commands."""
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return
        m = re.match(r"\ufeff?---\s*\r?\n(.*?)\r?\n---", text, re.S)
        if not m or not re.search(r"^\s*hooks\s*:", m.group(1), re.M):
            return
        self.texts[path] = text
        self.checked.append(self.show(path))
        block = m.group(1).split("\n")
        start = next(i for i, l in enumerate(block) if re.match(r"^\s*hooks\s*:", l))
        for line in block[start + 1:]:
            if line.strip() and not line.startswith((" ", "\t", "-")):
                break  # the next top-level frontmatter key
            cm = re.match(r"^\s*-?\s*command\s*:\s*(.+?)\s*$", line)
            if cm:
                cmd = cm.group(1).strip()
                if len(cmd) >= 2 and cmd[0] == cmd[-1] and cmd[0] in "\"'":
                    cmd = cmd[1:-1]
                self.command(path, cmd, None, plugin_root, self.workspace)

    def hooks_file(self, path, root):
        if not self.first_time(path):
            return
        data = self.load(path, "I7")
        if data is None:
            return
        if not isinstance(data, dict):
            self.find("I7", path, "A hooks file holds one JSON object.")
            return
        if "modules" in data:  # a mod: hooks modules written as code
            for m in data["modules"] if isinstance(data["modules"], list) else []:
                target = os.path.normpath(os.path.join(os.path.dirname(path), str(m)))
                if not os.path.isfile(target):
                    self.find("I7", path, "Hooks module not found: %s" % m, json.dumps(m))
        if "hooks" in data:
            self.hooks(path, data["hooks"], root, self.workspace)
        elif "modules" not in data:
            self.find("I7", path, "A hooks file must wrap its events in a top-level 'hooks' key; without it the file "
                      "fails to load.")

    def marketplace(self, path):
        root = os.path.dirname(os.path.dirname(path))
        data = self.load(path, "I8")
        if data is None:
            return
        if not isinstance(data, dict):
            self.find("I8", path, "marketplace.json holds one JSON object.")
            return
        name = data.get("name")
        if not isinstance(name, str) or not ID_NAME.match(name) or ".." in name:
            self.find("I8", path, "Marketplace 'name' is missing or uses characters other than letters, digits, ., _, and -.", '"name"')
        owner = data.get("owner")
        if not (isinstance(owner, dict) and isinstance(owner.get("name"), str) and owner["name"].strip()):
            self.find("I8", path, "Marketplace 'owner' must be an object with a 'name'.", '"owner"')
        for key in data:
            if key not in MARKET_KEYS:
                self.find("I8", path, "Unknown marketplace.json field '%s'; Claude Code ignores it." % key, '"%s"' % key, "suggestion")
        plugins = data.get("plugins")
        if not isinstance(plugins, list):
            self.find("I8", path, "Marketplace 'plugins' must be a list.", '"plugins"')
            return
        seen = set()
        for i, p in enumerate(plugins):
            if not isinstance(p, dict):
                self.find("I8", path, "plugins[%d] must be an object." % i)
                continue
            pname = p.get("name")
            if not isinstance(pname, str) or not ID_NAME.match(pname):
                self.find("I8", path, "plugins[%d] has no valid 'name'." % i)
            elif pname in seen:
                self.find("I8", path, "Duplicate plugin name '%s'." % pname, json.dumps(pname))
            seen.add(pname)
            src = p.get("source")
            where = json.dumps(pname) if isinstance(pname, str) else None
            if isinstance(src, str):
                if src != "." and not src.startswith("./"):
                    self.find("I8", path, "plugins[%d] source '%s' must start with ./" % (i, src), where)
                elif ".." in src.split("/"):
                    self.find("I8", path, "plugins[%d] source '%s' contains '..'." % (i, src), where)
                elif not os.path.isdir(os.path.normpath(os.path.join(root, src))):
                    self.find("I8", path, "plugins[%d] source folder not found: %s" % (i, src), where)
            elif isinstance(src, dict):
                t = src.get("source")
                if t not in SOURCE_REQUIRED:
                    self.find("I8", path, "plugins[%d] source type '%s' is not one of %s." % (i, t, ", ".join(sorted(SOURCE_REQUIRED))), where)
                else:
                    for field in SOURCE_REQUIRED[t]:
                        if not src.get(field):
                            self.find("I8", path, "plugins[%d] '%s' source needs '%s'." % (i, t, field), where)
            else:
                self.find("I8", path, "plugins[%d] has no 'source'." % i, where)

    # I9: MCP servers ----------------------------------------------------------

    def mcp_file(self, path, plugin_root):
        if not self.first_time(path):
            return
        data = self.load(path, "I9")
        if data is None:
            return
        servers = data.get("mcpServers", data) if isinstance(data, dict) else None
        if not isinstance(servers, dict):
            self.find("I9", path, "An MCP config holds an 'mcpServers' object keyed by server name.")
            return
        self.mcp_servers(path, servers, plugin_root)

    def mcp_servers(self, path, servers, plugin_root):
        for name, s in servers.items():
            needle = '"%s"' % name
            if not isinstance(s, dict):
                self.find("I9", path, "MCP server '%s' must be an object." % name, needle)
                continue
            if s.get("command"):
                cmd = self.expand(str(s["command"]), plugin_root, self.workspace)
                self.run_as("I9", "MCP server '%s'" % name, self.program, path, cmd, needle)
                self.pin(path, cmd, s.get("args") or [], needle, "MCP server '%s'" % name, "I9")
            elif s.get("url"):
                url = str(s["url"])
                if not re.match(r"^(https?|wss?)://\S+$", url):
                    self.find("I9", path, "MCP server '%s' url is not an absolute URL: %s" % (name, url), needle)
                elif re.match(r"^(http|ws)://", url) and not re.match(r"^(http|ws)://(localhost|127\.|\[::1\])", url):
                    self.find("I9", path, "MCP server '%s' uses unencrypted %s to a non-loopback host." % (name, url.split(":")[0]),
                              needle, "suggestion")
            else:
                self.find("I9", path, "MCP server '%s' has neither 'command' nor 'url'; Claude Code drops it." % name, needle)
            for block in ("headers", "env"):
                for k, v in (s.get(block) or {}).items() if isinstance(s.get(block), dict) else []:
                    v = str(v)
                    if "${" in v:
                        continue  # a reference, not a literal value
                    if SECRET.search(v) or (SECRET_NAME.search(k) and len(v) >= 8):
                        self.find("I9", path, "MCP server '%s' %s '%s' holds a literal credential; use a ${VAR} reference "
                                  "or userConfig with sensitive: true." % (name, block, k), '"%s"' % k)

    # Run ----------------------------------------------------------------------

    def excluded(self, path):
        real = os.path.abspath(path)
        return any(real == x or real.startswith(x + os.sep) for x in self.excludes)

    def walk(self, base):
        for dirpath, dirnames, filenames in os.walk(base):
            # A candidate's test inputs and scratch folders install with it, so only the user's own are skipped
            dirnames[:] = sorted(d for d in dirnames if d not in (".git", "node_modules", "__pycache__")
                                 and not self.excluded(os.path.join(dirpath, d))
                                 and (self.candidate or (d != "_sandbox" and
                                                         not is_fixture(os.path.relpath(os.path.join(dirpath, d), base)))))
            for f in sorted(filenames):
                yield os.path.join(dirpath, f)

    def run(self):
        if self.candidate:
            base = self.root
            settings = [(p, "candidate") for p in self.walk(base) if os.path.basename(p) in SETTINGS_FILES]
        else:
            settings = [(os.path.join(self.root, n), "user" if self.is_global else ("local" if "local" in n else "project"))
                        for n in SETTINGS_FILES if os.path.isfile(os.path.join(self.root, n))]
            base = self.workspace
        for path, scope in settings:
            self.settings(path, scope)
            if self.candidate:
                self.find("I5", path, "The candidate ships a settings file; installing it would change the user's "
                          "permissions, hooks, or environment.", None, "defect")
        if base:
            manifests = set()
            for p in self.walk(base):
                rel = p.replace(os.sep, "/")
                if rel.endswith("/.claude-plugin/plugin.json"):
                    manifests.add(os.path.dirname(os.path.dirname(p)))
                    self.plugin(p)
                elif rel.endswith("/.claude-plugin/marketplace.json"):
                    self.marketplace(p)
            for p in self.walk(base):
                rel = p.replace(os.sep, "/")
                owner = os.path.dirname(os.path.dirname(p))
                if rel.endswith("/hooks/hooks.json") and owner not in manifests and os.path.basename(os.path.dirname(p)) == "hooks":
                    self.hooks_file(p, owner)  # a plugin without a manifest
                elif os.path.basename(p) == ".mcp.json" and os.path.dirname(p) not in manifests:
                    self.mcp_file(p, os.path.dirname(p) if self.candidate else None)
                elif os.path.basename(p) == ".lsp.json" and os.path.dirname(p) not in manifests:
                    self.lsp_file(p, os.path.dirname(p) if self.candidate else None)
                elif rel.endswith("/SKILL.md") or re.search(r"/agents/[^/]+\.md$", rel):
                    self.frontmatter_hooks(p, plugin_root_of(p, base) if self.candidate else None)
        elif self.is_global:
            for sub in ("skills", "agents"):
                for dirpath, dirnames, filenames in os.walk(os.path.join(self.root, sub)):
                    dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "synced"]
                    for f in filenames:
                        if f == "SKILL.md" or (sub == "agents" and f.endswith(".md")):
                            self.frontmatter_hooks(os.path.join(dirpath, f), None)
        if not self.candidate and not self.workspace:
            self.skipped.append("I8, I9: the global folder holds only installed plugins, which are not audited.")
        return {
            "as_of": self.args.as_of or datetime.date.today().isoformat(),
            "root": self.root.replace(os.sep, "/"),
            "mode": "candidate" if self.candidate else ("global" if self.is_global else "workspace"),
            "checked": self.checked,
            "findings": self.findings,
            "needs": sorted(self.needs),
            "checks_run": ["I5", "I6", "I7"] + ([] if not (self.candidate or self.workspace) else ["I8", "I9"]),
            "skipped_checks": self.skipped,
            "counts": {c: sum(1 for f in self.findings if f["check"] == c) for c in sorted({f["check"] for f in self.findings})},
        }


def plugin_root_of(path, stop):
    """The nearest folder above path that holds .claude-plugin/plugin.json, else the candidate root."""
    d = os.path.dirname(os.path.abspath(path))
    stop = os.path.abspath(stop)
    while d.startswith(stop):
        if os.path.isfile(os.path.join(d, ".claude-plugin", "plugin.json")):
            return d
        if d == stop:
            break
        d = os.path.dirname(d)
    return stop


def is_fixture(rel):
    """A saved test case's input folder (evals/<case>/files), which may be broken or hostile on purpose."""
    parts = os.path.normpath(rel).split(os.sep)
    return len(parts) >= 3 and parts[-1] == "files" and parts[-3] == "evals"


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False))
    sys.exit(2)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Scripted checks of settings, permission rules, hooks, manifests, and MCP configs.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--root", default=os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude",
                        help=".claude folder to check (default: the global folder)")
    target.add_argument("--candidate", help="isolated copy of one third-party tool that skill-finder is vetting")
    parser.add_argument("--exclude", nargs="*", help="folders to leave out (third-party folders a workspace does not edit)")
    parser.add_argument("--as-of", help="date to report as the run date (YYYY-MM-DD)")
    args = parser.parse_args()
    folder = os.path.expanduser(args.candidate or args.root)
    # A workspace without a .claude folder still has manifests and .mcp.json files to check
    workspace_without_tools = (not args.candidate and os.path.basename(os.path.abspath(folder)) == ".claude"
                               and os.path.isdir(os.path.dirname(os.path.abspath(folder))))
    if not os.path.isdir(folder) and not workspace_without_tools:
        fail("folder not found: %s" % folder)
    print(json.dumps(Config(args).run(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

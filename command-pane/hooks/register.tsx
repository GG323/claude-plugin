import { atom, read, update } from 'claude-code'
import type { ConfigRow, EngineInterface, Register } from 'claude-code'

import { registerToday, startToday } from './today'
import { registerCustomize, startCustomize } from './customize'
import { HANDOVER_ALERT_KEY, HANDOVER_DEFAULTS, HANDOVER_LEVELS, HANDOVER_WARN_KEY, registerHandover } from './handover'

// Settings: two userConfig fields of this mod, shown in /config and in the Settings pane
const TECH_KEY = 'command-pane.techLevel'
const APPROVAL_KEY = 'command-pane.approvalLevel'
// Built-in /config row (probed 2026-11-05: default, Proactive, Concise, Explanatory, Learning)
const OUTPUT_STYLE_KEY = 'outputStyle'

const TECH_LEVELS = ['nontechnical', 'some technical', 'developer'] as const
const APPROVAL_LEVELS = ['auto', 'low', 'mid', 'high'] as const

// What each choice adds to the system prompt
const TECH_TEXT: Record<string, string> = {
  nontechnical:
    'The user is not technical. Use plain everyday words, explain any technical term in a few words the first time, and leave out code, file paths, and command output unless the user asks. Describe results by what they mean for the user.',
  'some technical':
    'The user is somewhat technical: comfortable with files, settings, and simple commands, but not a programmer. Keep jargon light and explain uncommon terms; show code or commands only where they help.',
  developer:
    'The user is a developer. Be concise and technical; show code, paths, and commands directly.',
}

const APPROVAL_TEXT: Record<string, string> = {
  auto: 'When an action needs the user\'s approval, state it in one line; for everything else, act and report what you did afterwards in one or two lines.',
  low: 'When you ask the user for approval, state the action in one line.',
  mid: 'When you ask the user for approval, give a short plan first: what will change, in two to four bullets.',
  high: 'When you ask the user for approval, give a full plan first: each step, what it changes, the risks, and how to undo it.',
}

const APPROVAL_NOTE =
  'This sets only how much detail goes with an approval request; it never removes an approval that is otherwise required.'

// The HowToAI recommended setup
const RECOMMENDED = {
  techLevel: 'some technical',
  approvalLevel: 'mid',
  outputStyle: 'Explanatory',
}

// Archive after 7 days is a desktop app setting: no /config row, so a mod cannot set it
const ARCHIVE_NOTE = 'Archive inactive sessions after 7 days: set it in the desktop app Settings.'

// Bumped after every change so the pane redraws with fresh values
const settingsRev = atom({ plugin: 'command-pane', key: 'settingsRev' } as const, 0, { shape: 'rev-1' })

const findRow = (rows: readonly ConfigRow[], key: string) => rows.find(r => r.key === key)

async function setRow($: EngineInterface, key: string, value: string | number | boolean): Promise<string | undefined> {
  try {
    const result = await $.config.set({ key, value })
    return result.deny
  } catch (err) {
    return err instanceof Error ? err.message : String(err)
  }
}

async function applyRecommended($: EngineInterface) {
  const done: string[] = []
  const skipped: string[] = []

  // Output style first: the mod's own rows reload the module when they change
  for (const [key, value, name] of [
    [OUTPUT_STYLE_KEY, RECOMMENDED.outputStyle, 'output style'],
    [TECH_KEY, RECOMMENDED.techLevel, 'technical level'],
    [APPROVAL_KEY, RECOMMENDED.approvalLevel, 'approval detail'],
  ] as const) {
    const deny = await setRow($, key, value)
    if (deny) skipped.push(`${name} (${deny})`)
    else done.push(name)
  }

  await update($, settingsRev, n => n + 1)
  $.ui.toast(
    `Recommended setup: set ${done.join(', ') || 'nothing'}${skipped.length ? `; skipped ${skipped.join('; ')}` : ''}. ${ARCHIVE_NOTE}`,
  )
}

async function choose($: EngineInterface, key: string, value: string) {
  const deny = await setRow($, key, value)
  if (deny) $.ui.toast(`Setting not changed: ${deny}`)
  await update($, settingsRev, n => n + 1)
}

export const register: Register = (on, options) => {
  // Today pane (hooks/today.tsx)
  registerToday(on)

  // The band and the Customize pane (hooks/customize.tsx)
  registerCustomize(on)

  // Handover button colour levels (hooks/handover.tsx)
  registerHandover(on, options)

  const techLevel = String(options.techLevel ?? RECOMMENDED.techLevel)
  const approvalLevel = String(options.approvalLevel ?? RECOMMENDED.approvalLevel)

  // Clear the todo status line an earlier version pinned
  on('session.start', async ($, e, next) => {
    $.ui.status(undefined)
    await startToday($) // Today pane: /today command and last results
    await startCustomize($) // band layout from buttons.json, /buttons command
    void $.store.delete('configProbe') // development probe of an earlier build

    return next(e)
  })

  // System prompt: the user's technical level and approval detail
  on('prompt.compose', async ($, e, next) => {
    const result = await next(e)
    const tech = TECH_TEXT[techLevel]
    const approval = APPROVAL_TEXT[approvalLevel]
    if (!tech && !approval) return result

    const text = ['# User settings (command-pane)', tech, approval && `${approval} ${APPROVAL_NOTE}`]
      .filter(Boolean)
      .join('\n\n')

    return { sections: [...result.sections, { id: 'command-pane:user-settings', text, scope: 'session' }] }
  })

  // The band above the prompt is drawn in hooks/customize.tsx from the user's buttons.json

  // The Settings pane
  on('ui.render', { component: 'Pane', requestId: 'command-pane-settings' }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    await read($, settingsRev) // redraw after a change
    const rows = await $.config.list()
    const value = (key: string, fallback: string) => String(rows.find(r => r.key === key)?.value ?? fallback)
    const tech = value(TECH_KEY, techLevel)
    const approval = value(APPROVAL_KEY, approvalLevel)
    const styleRow = findRow(rows, OUTPUT_STYLE_KEY)
    const hoWarn = value(HANDOVER_WARN_KEY, String(options.handoverWarn ?? HANDOVER_DEFAULTS.warn))
    const hoAlert = value(HANDOVER_ALERT_KEY, String(options.handoverAlert ?? HANDOVER_DEFAULTS.alert))

    const choiceRow = (key: string, prefix: string, levels: readonly string[], current: string) => (
      <Box flexDirection="row" gap={1} flexWrap="wrap">
        {levels.map(level => (
          <Button
            key={`${prefix}-${level}`}
            variant={level === current ? 'primary' : undefined}
            dimColor={level !== current}
            onPress={() => void choose($, key, level)}
          >
            {level}
          </Button>
        ))}
      </Box>
    )

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold>Technical level</Text>
          <Text dimColor>How technical Claude's answers are.</Text>
          {choiceRow(TECH_KEY, 'tech', TECH_LEVELS, tech)}
        </Box>
        <Box flexDirection="column">
          <Text bold>Approval detail</Text>
          <Text dimColor>How much Claude explains before asking for approval.</Text>
          {choiceRow(APPROVAL_KEY, 'approval', APPROVAL_LEVELS, approval)}
        </Box>
        <Box flexDirection="column">
          <Text bold>Handover button</Text>
          <Text dimColor>Context window fill (%) at which the ⇄ Handover button turns yellow, then red.</Text>
          <Text color="warning">Yellow at</Text>
          {choiceRow(HANDOVER_WARN_KEY, 'ho-warn', HANDOVER_LEVELS, hoWarn)}
          <Text color="error">Red at</Text>
          {choiceRow(HANDOVER_ALERT_KEY, 'ho-alert', HANDOVER_LEVELS, hoAlert)}
          {Number(hoAlert) <= Number(hoWarn) && <Text dimColor>Red is at or below yellow, so the button goes straight to red.</Text>}
        </Box>
        <Box flexDirection="column">
          <Text bold>Claude Code</Text>
          <Text dimColor>Output style: {styleRow ? String(styleRow.value) : 'not reachable'}</Text>
          <Text dimColor>{ARCHIVE_NOTE}</Text>
        </Box>
        <Button key="apply-recommended" variant="primary" onPress={() => void applyRecommended($)}>
          Apply recommended
        </Button>
        <Text dimColor>Recommended: some technical, mid approval detail, Explanatory output style.</Text>
      </Box>
    )
  })
}

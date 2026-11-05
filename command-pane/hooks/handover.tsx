import type { EngineInterface, Register } from 'claude-code'

// Handover: one click asks Claude to write a handover and continue in a new session.
// The band button's colour follows the context window's fill:
//   default below the warn level, warning (yellow) from it, error (red) from the alert level.
// Both levels are this mod's userConfig fields (handoverWarn, handoverAlert), shown in
// /config and in the Settings pane.

export const HANDOVER_WARN_KEY = 'command-pane.handoverWarn'
export const HANDOVER_ALERT_KEY = 'command-pane.handoverAlert'
export const HANDOVER_LEVELS = ['30', '40', '50', '60', '70', '80', '90'] as const
export const HANDOVER_DEFAULTS = { warn: '50', alert: '70' }

export const HANDOVER_PROMPT = [
  'Hand this work over to a new session.',
  '',
  '1. Write a handover with these parts:',
  '   - Supporting materials: the files, links, sources, and tools used, with their paths or URLs.',
  '   - Overall: what the work is for and what has been done, in two or three sentences.',
  '   - Tasks done: one bullet per task, with its result.',
  '   - Working documents: for each one, its path, its current state, and what is unfinished.',
  '   - Next steps and open questions.',
  '2. Start a new session with a fresh context (not a full copy of this conversation) and give it the handover as its first message. Tell me the new session\'s name.',
  '3. If you cannot start a session here, show the handover so I can copy it into a new session.',
].join('\n')

let warnAt = Number(HANDOVER_DEFAULTS.warn)
let alertAt = Number(HANDOVER_DEFAULTS.alert)

const pct = (v: unknown, fallback: number) => {
  const n = Number(v)
  return Number.isFinite(n) && n > 0 && n <= 100 ? n : fallback
}

// The context window's fill as a whole percentage, or undefined before the first reply
export async function contextPercent($: EngineInterface): Promise<number | undefined> {
  try {
    return (await $.session.usage()).context.percent
  } catch {
    return undefined
  }
}

// Theme colour for the band button: undefined (default), 'warning' or 'error'
export async function handoverColor($: EngineInterface): Promise<'warning' | 'error' | undefined> {
  const p = await contextPercent($)
  if (p === undefined) return undefined
  if (p >= Math.max(alertAt, warnAt)) return 'error'
  if (p >= warnAt) return 'warning'
  return undefined
}

export async function runHandover($: EngineInterface) {
  const result = await $.prompt.submit({ text: HANDOVER_PROMPT, asUser: true })
  if ('deny' in result && result.deny) $.ui.toast(`Handover not sent: ${String(result.deny)}`)
}

export const registerHandover = (on: Parameters<Register>[0], options: Record<string, unknown>) => {
  warnAt = pct(options.handoverWarn, Number(HANDOVER_DEFAULTS.warn))
  alertAt = pct(options.handoverAlert, Number(HANDOVER_DEFAULTS.alert))

  // The fill changes with each reply: redraw the band so the button's colour follows
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    $.ui.invalidate('ui.render')
    return result
  })
}

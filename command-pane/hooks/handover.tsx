import type { EngineInterface, Register } from 'claude-code'

// Handover: one click runs this plugin's handover skill (skills/handover/SKILL.md), so the
// transcript shows /command-pane:handover instead of a long prompt. The skill has Claude write
// a handover of the latest work and propose a new session with it: a New task card the user
// starts with one click. (A mod-sent turn may only propose a session, not start one.) The new
// session detaches itself first, so this one gets no reports from it. No file is written.
// The band button's colour follows the context window's fill:
//   default below the warn level, warning (yellow) from it, error (red) from the alert level.
// Both levels are this mod's userConfig fields (handoverWarn, handoverAlert), shown in
// /config and in the Settings pane.

export const HANDOVER_WARN_KEY = 'command-pane.handoverWarn'
export const HANDOVER_ALERT_KEY = 'command-pane.handoverAlert'
export const HANDOVER_LEVELS = ['30', '40', '50', '60', '70', '80', '90'] as const
export const HANDOVER_DEFAULTS = { warn: '50', alert: '70' }

const HANDOVER_SKILL = 'command-pane:handover'

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
  // The current Settings values (a change in the Settings pane or /config applies at once);
  // the values from load time when the rows cannot be read
  let warn = warnAt
  let alert = alertAt
  try {
    const rows = await $.config.list()
    warn = pct(rows.find(r => r.key === HANDOVER_WARN_KEY)?.value, warnAt)
    alert = pct(rows.find(r => r.key === HANDOVER_ALERT_KEY)?.value, alertAt)
  } catch {
    // keep the load-time values
  }
  if (p >= Math.max(alert, warn)) return 'error'
  if (p >= warn) return 'warning'
  return undefined
}

export async function runHandover($: EngineInterface) {
  try {
    await $.command.run({ command: HANDOVER_SKILL })
  } catch (err) {
    $.ui.toast(`/${HANDOVER_SKILL} did not run: ${err instanceof Error ? err.message : String(err)}`)
  }
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

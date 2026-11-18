import type { ConfigRow, EngineInterface, Register, SessionMessage } from 'claude-code'
import { homeSync, resolvePaths } from './paths'

import type { Band, Level } from '../types'

const BAND = { plugin: 'effort-optimizer', key: 'band' } as const
const OVERRIDE = { plugin: 'effort-optimizer', key: 'override' } as const
// Fits the footer slot (about 14 cells).
const SHORT = { low: 'Low', medium: 'Medium', high: 'High', xhigh: 'XHigh', max: 'Max' } as const

const LEVELS: readonly Level[] = ['low', 'medium', 'high', 'xhigh', 'max']
const NAMES: Record<Level, string> = { low: 'Low', medium: 'Medium', high: 'High', xhigh: 'Extra high', max: 'Max' }

const APPLIED_MS = 15000
const ACCENT = '#d97757'
const GOOD = '#16a34a'
const BAD = '#dc2626'

type Pick = { level: Level; why: string }

// Module variables reset on a reload; the band and the override live in $.state.
let home = ''
let enabled = true
// Bumped on every prompt, so a slow pick for an older prompt is dropped.
let gen = 0
let nextId = 1
// The level the main chat's last request ran at, before this mod touched it.
let seen: Level | '' = ''
// The level for the rest of the running turn, set by the automatic pick.
let turnLevel: Level | null = null
// The /config row that holds the effort setting, found at session start.
let rowKey = ''
// A /effort run waiting for the turn to end.
// The level the mod puts on requests, and the picker level it saw when it took over.
let hold: { level: Level; base: string } | null = null
let lastEffort = ''
// The prompt waiting for its pick at the turn's first request.
let held: { text: string; mine: number } | null = null

// The /mods switchboard turns this mod off in every chat with switches.json.
// "effort-optimizer:hidden": true in the same file hides the band and the footer label; the mod keeps picking.
const NAME = 'effort-optimizer'
const HIDE_KEY = `${NAME}:hidden`
let off = false
let hidden = false

async function readSwitch($: EngineInterface) {
  let now = false
  let nowHidden = false
  try {
    const path = `${homeSync($)}/.claude/mods/switches.json`
    if (await $.fs.exists(path)) {
      const json = JSON.parse(String(await $.fs.read(path))) as Record<string, unknown>
      now = json[NAME] === false
      nowHidden = json[HIDE_KEY] === true
    }
  } catch {
    now = off
    nowHidden = hidden
  }
  if (now === off && nowHidden === hidden) return
  off = now
  hidden = nowHidden
  if (off) turnLevel = null
  try {
    $.ui.invalidate('ui.render')
  } catch {
    // The next state change redraws anyway.
  }
}

async function log($: EngineInterface, what: string, err: unknown) {
  try {
    const path = `${home}/.claude/mods-logs/effort-optimizer.log`
    const old = (await $.fs.exists(path)) ? String(await $.fs.read(path)) : ''
    const msg = err instanceof Error ? err.message : String(err)
    await $.fs.write(path, `${old.slice(-20_000)}${new Date(await $.clock.now()).toISOString()} ${what}: ${msg}\n`)
  } catch {
    // Nowhere left to report it.
  }
}

async function getBand($: EngineInterface): Promise<Band | null> {
  const { value } = await $.state.get(BAND)
  return value ?? null
}

async function setBand($: EngineInterface, b: Band | null) {
  await $.state.set(BAND, b)
}

// "Extra high", "x-high" and "xhigh" all read as xhigh.
function norm(s: string) {
  const t = s.toLowerCase().replace(/[^a-z]/g, '')
  if (t === 'extrahigh' || t === 'xhigh') return 'xhigh'
  return t
}

function asLevel(v: unknown): Level | '' {
  if (typeof v !== 'string') return ''
  const t = norm(v)
  return (LEVELS as readonly string[]).includes(t) ? (t as Level) : ''
}

function isEffortRow(r: ConfigRow) {
  if (!/effort/i.test(`${r.key} ${r.label}`)) return false
  if (r.kind !== 'choice') return false
  return (r.options ?? []).some(o => norm(o) === 'high')
}

async function findRow($: EngineInterface) {
  const rows = await $.config.list()
  return rows.find(isEffortRow) ?? null
}

// The level the chat runs at now: the last request's, else the setting's.
async function currentLevel($: EngineInterface): Promise<Level | ''> {
  if (seen) return seen
  try {
    const row = await findRow($)
    return row ? asLevel(row.value) : ''
  } catch {
    return ''
  }
}

// Sets the chat's effort setting, or, when no setting takes it, has this mod put the level on every request
// until the person moves the picker. No /effort command is run.
async function applyLevel($: EngineInterface, level: Level) {
  turnLevel = level
  let note = ''
  try {
    const row = await findRow($)
    const option = row?.options?.find(o => norm(o) === level)
    if (row && option && !row.isLocked) {
      const r = await $.config.set({ key: row.key, value: option })
      if (!r.deny) {
        await $.state.set(OVERRIDE, null)
        return ''
      }
      note = r.deny
    } else {
      note = row ? (row.isLocked ? 'the effort setting is locked' : 'the effort setting has no such level') : 'no effort setting found'
    }
  } catch (err) {
    note = err instanceof Error ? err.message : String(err)
  }
  await log($, 'set effort', note)
  hold = { level, base: lastEffort }
  await $.state.set(OVERRIDE, level)
  redraw($)
  return ''
}

function redraw($: EngineInterface) {
  try {
    $.ui.invalidate('ui.render')
  } catch {
    // The next state change redraws anyway.
  }
}

// Plain text: no em or en dashes, never the banned word, one short line.
function cleanWhy(raw: string) {
  const r = raw
    .replace(/\s*[—–]\s*/g, ', ')
    .replace(/\bship(s|ped|ping)?\b/gi, 'publish')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^["'`\s]+|["'`\s.]+$/g, '')
  return r.slice(0, 90)
}

function lastAssistantText(messages: readonly SessionMessage[]) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i]!
    if (m.role === 'assistant' && m.text.trim()) return m.text
  }
  return ''
}

// Ben's framework from the effort levels video: four questions, stop at the first yes.
function pickPrompt(text: string, lastReply: string, now: Level | '') {
  return `You pick the effort level an AI assistant (Claude) should use for one prompt. Effort sets how much time, reading and checking Claude spends, and how many decisions it makes alone. It is not how smart Claude is.

First: if the prompt only approves, answers a question, corrects a detail, or says to go on with earlier work (yes, go, ok, do it, option 2, "use X instead"), answer keep. Changing the level mid-task costs a cache rebuild.

Otherwise ask these questions in this order and stop at the first yes:

1. Is it chat, a simple question, or a quick task the person will go back and forth on? Then low.
   Examples: simple questions and lookups, brainstorming options, quick rewrites (friendlier, shorter), sorting or tagging items, short summaries, rough drafts or outlines, small tweaks to something already made, renaming, one small mechanical edit, running one command.
2. Would a hidden mistake cost money, a client, trust, security or a wrong decision, or does the work need checking that is easy to skip? Then high.
   Examples: checking numbers across sources, open-ended analysis with no set path (why did churn go up), reviewing a contract for risk, fact-checking, going through long documents, security or permission review, building a whole feature end to end and testing it, verifying and testing work made at a lower level, building or fixing a skill.
3. Is the person handing off a long, hard and critical job to run on its own (more than about 30 minutes, many steps), with no time to answer questions? All three must be true. Then xhigh.
   Examples: a full research report from a year of calls and tickets, reviewing a 50 page agreement before signing, an investor pitch deck as the best one shot. Answer max only when the prompt asks for the deepest possible work and says it is critical; otherwise xhigh.
4. Everything else is medium: everyday writing, repurposing content, meeting summaries with decisions and next steps, standard reports in a set format, quick research before a call, a clear, well-specified coding change or bug fix, a refactor across many files, debugging a problem with an unknown cause. If you are not sure, medium.

Rules:
- Effort is not intelligence. A vague or underspecified prompt needs a question, not more effort: do not raise the level for it.
- A task being long does not make it high. Rule-following work stays low or medium.
- Raise freely. Pick a level below the one the chat runs at only when the prompt starts a new, unrelated task; for more of the same work, answer keep.

The chat runs at: ${now || 'unknown'}

Claude's last reply (first 600 characters, for context):
<reply>
${lastReply || '(none, this is the first prompt)'}
</reply>

The new prompt:
<prompt>
${text}
</prompt>

Reply with JSON only: {"level": "low|medium|high|xhigh|max|keep", "why": "the reason in under 12 plain words"}`
}

function parsePick(text: string): Pick | null {
  const m = /\{[\s\S]*\}/.exec(text)
  if (!m) return null
  try {
    const j = JSON.parse(m[0]) as { level?: unknown; why?: unknown }
    const level = asLevel(j.level)
    if (!level) return null
    return { level, why: cleanWhy(typeof j.why === 'string' ? j.why : '') }
  } catch {
    return null
  }
}

// HowToAI: clear cases skip the picker call (it adds about a second to every prompt).
const APPROVAL = /^(y|yes|yep|ok|okay|sure|go|go on|go ahead|do it|continue|proceed|next|thanks|thank you|option \d+|\d+)[\s.!]*$/i

async function pick($: EngineInterface, text: string, now: Level | ''): Promise<Pick | null> {
  // ultrathink: Claude Code runs this turn at xhigh by itself; hold the same level so the two agree.
  if (/\bultrathink\b/i.test(text)) return { level: 'xhigh', why: 'you asked for ultrathink' }
  if (APPROVAL.test(text.trim())) return null
  const messages = await $.session.messages()
  const lastReply = lastAssistantText(messages).slice(0, 600)
  const r = await $.model.complete({
    // HowToAI: Haiku 5.5 is the fastest and cheapest model, meant for high-volume classification like this.
    model: 'claude-haiku-5-5',
    prompt: pickPrompt(text.slice(0, 4000), lastReply, now),
    maxTokens: 120,
    effort: 'low',
    timeoutMs: 20_000,
  })
  if (!r.isAnswered) throw new Error(`pick failed: ${r.reason}`)
  return parsePick(r.text)
}

async function hideLater($: EngineInterface, id: number) {
  await $.clock.sleep(APPLIED_MS)
  const b = await getBand($)
  if (b && b.id === id && b.phase === 'applied') await setBand($, null)
}

async function showApplied($: EngineInterface, p: Pick, from: Level | '', note: string) {
  const id = nextId++
  await setBand($, { phase: 'applied', id, level: p.level, from, why: p.why, note })
  void hideLater($, id).catch(err => log($, 'hide', err))
}

// HowToAI: the mod never asks. It picks before the prompt goes in and sets the level itself,
// so the first request already runs at the right level.
async function autoAdjust($: EngineInterface, text: string, mine: number) {
  const now = await currentLevel($)
  try {
    await $.ui.status('picking effort…')
  } catch {
    // The status line is a nicety.
  }
  try {
    const p = await pick($, text, now)
    if (!p || mine !== gen) return
    if (p.level === now) {
      turnLevel = p.level
      return
    }
    const note = await applyLevel($, p.level)
    await showApplied($, p, now, note)
  } finally {
    try {
      await $.ui.status(undefined)
    } catch {
      // Nothing to clear.
    }
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await resolvePaths($).catch(() => undefined) // HowToAI: resolve the home folder first (paths.ts)
    home = homeSync($)
    await $.command.register({
      name: 'effort-optimizer',
      description: 'Effort Optimizer: sets the effort level for each prompt by itself. off or on',
      argumentHint: '[off|on]',
    })
    enabled = (await $.store.get('enabled')) !== false
    await readSwitch($).catch(() => undefined)
    $.clock.every(3000, () => {
      void readSwitch($).catch(() => undefined)
    })
    void (async () => {
      const row = await findRow($)
      rowKey = row?.key ?? ''
      await log($, 'effort row', row ? `${row.key} = ${String(row.value)} [${(row.options ?? []).join(', ')}]${row.isLocked ? ' locked' : ''}` : 'none found')
    })().catch(err => log($, 'find row', err))
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    if (off || !enabled) return next(e)
    if (e.origin.kind !== 'composer' && e.origin.kind !== 'bridge') return next(e)
    const text = e.text.trim()
    if (!text || text.startsWith('/')) return next(e)
    gen += 1
    turnLevel = null
    const mine = gen
    // A new prompt makes an unanswered offer stale.
    const b = await getBand($).catch(() => null)
    if (b?.phase === 'offer') await setBand($, null).catch(() => undefined)
    // The pick waits for the turn's first request, which carries the level the chat really runs at.
    held = { text, mine }
    return next(e)
  }).catch(($, e, next) => next(e))

  // Every main-chat request: note its level, and put the chosen one on it when the setting could not be changed.
  on('turn.step', async function* ($, e, next) {
    if (off || e.agentId !== undefined || typeof e.effort !== 'string') return yield* next(e)
    lastEffort = e.effort
    // The picker moved (by hand, or /effort landed): the mod lets go.
    if (hold && e.effort !== hold.base) { hold = null; turnLevel = null }
    let value: Level | null = enabled && hold ? hold.level : null
    if (!hold && (await $.state.get(OVERRIDE)).value) {
      await $.state.set(OVERRIDE, null)
      redraw($)
    }
    // What the chat runs at now: the level the mod holds, else the picker's.
    seen = value ?? (asLevel(e.effort) || seen)
    if (held && e.index === 0 && enabled) {
      const h = held
      held = null
      await autoAdjust($, h.text, h.mine).catch(err => log($, 'auto', err))
      value = enabled && hold ? hold.level : null
    }
    const want = turnLevel ?? (enabled ? (value ?? null) : null)
    if (!want || want === e.effort) return yield* next(e)
    void log($, 'request', `${e.effort} -> ${want}`)
    return yield* next({ ...e, effort: want })
  })

  on('command.run', { command: 'effort-optimizer' }, async ($, e) => {
    if (off) return { text: 'Effort Optimizer is off. Turn it on with /mods.' }
    const arg = e.args.trim().toLowerCase()
    if (arg === 'off' || arg === 'on') {
      enabled = arg === 'on'
      await $.store.set('enabled', enabled)
      if (!enabled) {
        turnLevel = null
        await $.state.set(OVERRIDE, null)
        await setBand($, null)
      }
      return { text: enabled ? 'Effort Optimizer is on. It sets the effort level for each prompt by itself.' :'Effort Optimizer is off. Type /effort-optimizer on to turn it back on.' }
    }
    const now = await currentLevel($)
    const { value } = await $.state.get(OVERRIDE)
    return {
      text: [
        `Effort Optimizer is ${enabled ? 'on' : 'off'}. It sets the effort level for each prompt by itself.`,
        `This chat runs at: ${now ? NAMES[now] : 'unknown yet'}${value ? ` (held by the mod: ${NAMES[value]})` : ''}.`,
        `Effort setting: ${rowKey || 'not found, the mod sets the level on each request'}.`,
        'Type /effort-optimizer off or on.',
      ].join('\n'),
    }
  })

  on('ui.press', { plugin: 'effort-optimizer', element: 'switch' }, async ($, e) => {
    const b = await getBand($)
    if (!b || b.phase !== 'offer') return { element: e.element }
    try {
      const note = await applyLevel($, b.level)
      await showApplied($, { level: b.level, why: b.why }, b.from, note)
    } catch (err) {
      await log($, 'switch', err)
      await setBand($, { ...b, note: `Could not switch: ${(err instanceof Error ? err.message : String(err)).slice(0, 100)}` })
    }
    return { element: e.element }
  })

  on('ui.press', { plugin: 'effort-optimizer', element: 'info' }, async ($, e) => {
    const b = await getBand($)
    if (b) await setBand($, { ...b, phase: 'info' })
    return { element: e.element }
  })

  on('ui.press', { plugin: 'effort-optimizer', element: 'info-close' }, async ($, e) => {
    await setBand($, null)
    return { element: e.element }
  })

  on('ui.press', { plugin: 'effort-optimizer', element: 'skip' }, async ($, e) => {
    await setBand($, null)
    return { element: e.element }
  })

  // The app's model menu belongs to the app: it refuses a chat that changes its own effort.
  // So the footer slot beside it names the level the mod really sends.
  on('ui.render', { component: 'SessionMode' }, async ($, e, next) => {
    if (off || hidden || !enabled) return next(e)
    const { value } = await $.state.get(OVERRIDE)
    if (!value) return next(e)
    const label = `Effort ${SHORT[value]}`
    if (e.surface === 'desktop' || e.surface === 'vscode') {
      const { Text } = $.ui.resolve(e)
      return <Text color="#d97757">{label}</Text>
    }
    return next({ ...e, props: { ...e.props, modes: [...e.props.modes, label] } })
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (off || hidden || !enabled || e.props.hasSurvey) return next(e)
    const b = await getBand($)
    if (!b) return next(e)
    const rest = await next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const noop = () => undefined

    if (b.phase === 'applied') {
      return (
        <Box flexDirection="column">
          {rest}
          <Box flexDirection="row" gap={1}>
            <Text wrap="truncate-end">
              <Text color={GOOD}>✓</Text>
              <Text> Effort set to </Text>
              <Text bold>{NAMES[b.level]}</Text>
              {b.from ? <Text dimColor> (was {NAMES[b.from]})</Text> : null}
              {b.why ? <Text dimColor> · {b.why}</Text> : null}
            </Text>
            <Button key="info" label="ⓘ Learn more" variant="secondary" onPress={noop} />
          </Box>
        </Box>
      )
    }

    if (b.phase === 'info') {
      const was = b.from ? NAMES[b.from] : 'your old level'
      return (
        <Box flexDirection="column">
          {rest}
          <Box flexDirection="column">
            <Text>
              <Text color={ACCENT}>ⓘ</Text>
              <Text bold> Claude now works at {NAMES[b.level]} effort</Text>
            </Text>
            <Text dimColor>The mod sets the level on each message before it leaves your computer.</Text>
            <Text dimColor>The effort menu next to the model name still shows {was}. Only you can move that menu: the app does not let a chat change its own menu.</Text>
            <Text dimColor>To check the real level, look for the orange "Effort {SHORT[b.level]}" label at the bottom, or type /effort-optimizer.</Text>
            <Text dimColor>If you move the menu yourself, the mod follows the menu again.</Text>
            <Box flexDirection="row" gap={1}>
              <Button key="info-close" label="Got it" role="dismiss" onPress={noop} />
            </Box>
          </Box>
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        {rest}
        <Box flexDirection="column">
          <Text>
            <Text color={ACCENT}>●</Text>
            <Text bold> This looks like a {NAMES[b.level]} effort task</Text>
            {b.from ? <Text dimColor> (you are on {NAMES[b.from]})</Text> : null}
          </Text>
          {b.why ? <Text dimColor>{b.why}</Text> : null}
          <Box flexDirection="row" gap={1}>
            <Button key="switch" label={`Switch to ${NAMES[b.level]}`} variant="primary" onPress={noop} />
            <Button key="auto" label="Auto-adjust every prompt" variant="secondary" onPress={noop} />
            <Button key="skip" label="Skip" role="dismiss" onPress={noop} />
          </Box>
          {b.note ? <Text color={BAD}>{b.note}</Text> : null}
        </Box>
      </Box>
    )
  })
}

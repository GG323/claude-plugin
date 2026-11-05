import type { EngineInterface, Register } from 'claude-code'

// Today pane: "my tasks today", gathered by the mod itself (no agent turns).
// Which sources show is set per user and per workspace in one settings file:
//   ~/.claude/command-pane/today.json
// { "default": { sources }, "workspaces": { "<folder>": { sources } } }
// The longest workspace folder that contains the session's folder wins, else "default".
// The pane has two views: the task list (folders per source, then per heading)
// and an editor for this workspace's sources and rules, so nobody edits the JSON.

export const TODAY_PANE = 'command-pane-today'
const SETTINGS_REL = '.claude/command-pane/today.json'
const STORE_KEY = 'today.lastResults'
const COLLAPSED_KEY = 'today.collapsed'
const SNOOZED_KEY = 'today.snoozed'

type MarkdownSource = {
  type: 'markdown'
  name?: string
  path: string // relative to the workspace folder, or absolute
  sections?: string[] // headings to include (case-insensitive); all when absent
  skip?: string[] // item prefixes to leave out
  include?: string[] // rule: only items containing one of these words
}
type GmailSource = {
  type: 'gmail'
  name?: string
  server?: string // as /mcp lists it; tried with fallbacks when absent
  query?: string
  max?: number
  include?: string[]
}
type Source = MarkdownSource | GmailSource
type WorkspaceSettings = { sources?: Source[]; refreshMinutes?: number }
type Settings = { default?: WorkspaceSettings; workspaces?: Record<string, WorkspaceSettings> }

type Item = { text: string; detail?: string; href?: string; group?: string }
type SourceResult = { name: string; kind: Source['type']; items: Item[]; error?: string }
type Snapshot = {
  workspace: string // the settings entry used ("default" or a folder)
  settingsPath: string
  results: SourceResult[]
  at: number
  note?: string
}

// The editor's working copy: text fields as typed, parsed on Save
type DraftSource = {
  type: Source['type']
  name: string
  path: string
  sections: string
  skip: string
  include: string
  server: string
  query: string
  max: string
}
type Draft = { key: string; refreshMinutes: string; sources: DraftSource[] }

const DEFAULT_SKIP = ['Done', 'Dropped']
const DEFAULT_GMAIL_QUERY = 'in:inbox is:unread newer_than:2d'
const GMAIL_SERVERS = ['claude.ai Gmail', 'Gmail', 'gmail']

// Module state: lost on reload; snapshot, folders and snoozes come back from $.store
let snapshot: Snapshot | undefined
let loading = false
let timer: { cancel: () => void } | undefined
let view: 'list' | 'settings' = 'list'
let draft: Draft | undefined
let collapsed = new Set<string>()
let snoozed: Record<string, number> = {} // item key -> hidden until (ms)

const norm = (p: string) => p.replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase()
const isAbsolute = (p: string) => /^([a-zA-Z]:)?[\\/]/.test(p)
const join = (dir: string, rel: string) => `${dir.replace(/[\\/]+$/, '')}/${rel}`
const list = (s: string) =>
  s
    .split(',')
    .map(x => x.trim())
    .filter(Boolean)
const errText = (err: unknown) => (err instanceof Error ? err.message : String(err))

async function homeDir($: EngineInterface): Promise<string | undefined> {
  return (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
}

async function settingsPath($: EngineInterface): Promise<string | undefined> {
  const home = await homeDir($)
  return home ? join(home, SETTINGS_REL) : undefined
}

async function loadSettings($: EngineInterface): Promise<{ path?: string; settings?: Settings; error?: string }> {
  const path = await settingsPath($)
  if (!path) return { error: 'No home folder found (USERPROFILE / HOME unset).' }
  if (!(await $.fs.exists(path))) return { path }
  try {
    return { path, settings: JSON.parse(await $.fs.read(path)) as Settings }
  } catch (err) {
    return { path, error: `Settings file is not valid JSON: ${errText(err)}` }
  }
}

// The workspace entry for this session's folder: longest containing folder, else default
function pickWorkspace(settings: Settings, cwd: string): { key: string; folder: string; ws?: WorkspaceSettings } {
  const here = norm(cwd)
  let best: { key: string; len: number } | undefined
  for (const key of Object.keys(settings.workspaces ?? {})) {
    const k = norm(key)
    if ((here === k || here.startsWith(k + '/')) && (!best || k.length > best.len)) best = { key, len: k.length }
  }
  if (best) return { key: best.key, folder: best.key, ws: settings.workspaces?.[best.key] }
  return { key: 'default', folder: cwd, ws: settings.default }
}

// --- Readers -----------------------------------------------------------------

const clean = (s: string) =>
  s
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // links -> text
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .trim()

const cut = (s: string, n = 110) => (s.length > n ? `${s.slice(0, Math.max(1, n - 1))}…` : s)

const included = (src: Source, it: Item) =>
  !src.include?.length ||
  src.include.some(w => `${it.text} ${it.detail ?? ''} ${it.group ?? ''}`.toLowerCase().includes(w.toLowerCase()))

async function readMarkdown($: EngineInterface, src: MarkdownSource, folder: string): Promise<SourceResult> {
  const name = src.name || src.path
  const path = isAbsolute(src.path) ? src.path : join(folder, src.path)
  let text: string
  try {
    text = await $.fs.read(path)
  } catch (err) {
    return { name, kind: 'markdown', items: [], error: `Cannot read ${path}: ${errText(err)}` }
  }
  const want = src.sections?.map(s => s.toLowerCase())
  const skip = src.skip ?? DEFAULT_SKIP
  const items: Item[] = []
  let heading = ''
  let inCode = false
  for (const raw of text.split(/\r?\n/)) {
    if (/^\s*```/.test(raw)) inCode = !inCode
    if (inCode) continue
    const h = /^(#{2,4})\s+(.*)$/.exec(raw)
    if (h) {
      heading = clean(h[2] ?? '')
      continue
    }
    if (!heading || /^(contents|skills and agents)$/i.test(heading)) continue
    if (want && !want.includes(heading.toLowerCase())) continue
    const b = /^[-*]\s+(\[([ xX])\]\s+)?(.*)$/.exec(raw) // top-level bullets only
    if (!b) continue
    if (b[2] && b[2] !== ' ') continue // checked box
    const body = clean(b[3] ?? '')
    if (!body || skip.some(p => body.toLowerCase().startsWith(p.toLowerCase()))) continue
    const first = body.split(/(?<=[.:;])\s/)[0] ?? body
    items.push({ text: cut(first), detail: body, group: heading })
  }
  return { name, kind: 'markdown', items: items.filter(it => included(src, it)) }
}

function blocksText(content: readonly { type: string; text?: string }[]): string {
  return content.map(b => (b.type === 'text' ? (b.text ?? '') : '')).join('\n')
}

type GmailMessage = { subject?: string; sender?: string; snippet?: string; date?: string; viewUrl?: string }
type GmailThread = { id?: string; viewUrl?: string; messages?: GmailMessage[] }

function parseThreads(raw: string, structured: unknown): GmailThread[] | undefined {
  const pick = (v: unknown): GmailThread[] | undefined => {
    if (v && typeof v === 'object' && Array.isArray((v as { threads?: unknown }).threads))
      return (v as { threads: GmailThread[] }).threads
    if (v && typeof v === 'object' && Object.keys(v).length === 0) return [] // {} = no matches
    return undefined
  }
  const s = pick(structured)
  if (s) return s
  try {
    return pick(JSON.parse(raw))
  } catch {
    return undefined
  }
}

async function readGmail($: EngineInterface, src: GmailSource): Promise<SourceResult> {
  const name = src.name || 'Email'
  const args = { query: src.query || DEFAULT_GMAIL_QUERY, pageSize: src.max ?? 10, view: 'THREAD_VIEW_SUMMARY' }
  const servers = src.server ? [src.server] : GMAIL_SERVERS
  let lastError = 'Gmail is not connected in this session.'
  for (const server of servers) {
    try {
      const res = await $.mcp.call(server, 'search_threads', args)
      const raw = blocksText(res.content as { type: string; text?: string }[])
      if (res.isError) {
        lastError = `${server}: ${cut(raw || 'error', 200)}`
        continue
      }
      const threads = parseThreads(raw, res.structuredContent)
      if (!threads) return { name, kind: 'gmail', items: [], error: `Unexpected reply from ${server}: ${cut(raw, 200)}` }
      const items = threads.map(t => {
        const m = t.messages?.[t.messages.length - 1] ?? {}
        const sender = (m.sender ?? '').replace(/<[^>]*>/, '').trim()
        return { text: cut(m.subject || '(no subject)', 90), detail: sender, href: t.viewUrl ?? m.viewUrl }
      })
      return { name, kind: 'gmail', items: items.filter(it => included(src, it)) }
    } catch (err) {
      lastError = `${server}: ${errText(err)}`
    }
  }
  return { name, kind: 'gmail', items: [], error: lastError }
}

// --- Refresh -----------------------------------------------------------------

async function refresh($: EngineInterface) {
  if (loading) return
  loading = true
  $.ui.invalidate('ui.render')
  try {
    const cwd = await $.session.cwd()
    const { path, settings, error } = await loadSettings($)
    if (!settings) {
      snapshot = {
        workspace: 'default',
        settingsPath: path ?? SETTINGS_REL,
        results: [],
        at: await $.clock.now(),
        note: error ?? 'No sources set yet.',
      }
      return
    }
    const { key, folder, ws } = pickWorkspace(settings, cwd)
    const sources = ws?.sources ?? []
    const results = await Promise.all(
      sources.map(src =>
        src.type === 'markdown'
          ? readMarkdown($, src, folder)
          : src.type === 'gmail'
            ? readGmail($, src)
            : Promise.resolve<SourceResult>({
                name: (src as { name?: string }).name ?? 'Unknown',
                kind: 'markdown',
                items: [],
                error: `Unknown source type "${(src as { type?: string }).type}"`,
              }),
      ),
    )
    snapshot = {
      workspace: key,
      settingsPath: path ?? SETTINGS_REL,
      results,
      at: await $.clock.now(),
      note: sources.length ? undefined : `No sources set for ${key === 'default' ? 'this workspace' : key}.`,
    }
    await $.store.set(STORE_KEY, snapshot)
    restartTimer($, ws?.refreshMinutes ?? 15)
  } finally {
    loading = false
    $.ui.invalidate('ui.render')
  }
}

function restartTimer($: EngineInterface, minutes: number) {
  timer?.cancel()
  timer = minutes > 0 ? $.clock.every(minutes * 60_000, () => void refresh($)) : undefined
}

// --- Folders and snoozes -----------------------------------------------------

function toggleFolder($: EngineInterface, id: string) {
  if (collapsed.has(id)) collapsed.delete(id)
  else collapsed.add(id)
  void $.store.set(COLLAPSED_KEY, [...collapsed])
  $.ui.invalidate('ui.render')
}

const itemKey = (r: SourceResult, it: Item) => `${r.name}|${it.text}`

async function snooze($: EngineInterface, key: string) {
  const d = new Date(await $.clock.now())
  d.setHours(24, 0, 0, 0) // next local midnight
  snoozed[key] = d.getTime()
  await $.store.set(SNOOZED_KEY, snoozed)
  $.ui.invalidate('ui.render')
}

async function unsnoozeAll($: EngineInterface) {
  snoozed = {}
  await $.store.set(SNOOZED_KEY, snoozed)
  $.ui.invalidate('ui.render')
}

// --- Settings editor ---------------------------------------------------------

function toDraft(key: string, ws: WorkspaceSettings | undefined): Draft {
  return {
    key,
    refreshMinutes: String(ws?.refreshMinutes ?? 15),
    sources: (ws?.sources ?? []).map(s => ({
      type: s.type,
      name: s.name ?? '',
      path: s.type === 'markdown' ? s.path : '',
      sections: s.type === 'markdown' ? (s.sections ?? []).join(', ') : '',
      skip: s.type === 'markdown' ? (s.skip ?? DEFAULT_SKIP).join(', ') : '',
      include: (s.include ?? []).join(', '),
      server: s.type === 'gmail' ? (s.server ?? '') : '',
      query: s.type === 'gmail' ? (s.query ?? DEFAULT_GMAIL_QUERY) : '',
      max: s.type === 'gmail' ? String(s.max ?? 10) : '',
    })),
  }
}

function fromDraft(d: Draft): WorkspaceSettings {
  const sources: Source[] = d.sources.map(s => {
    const include = list(s.include)
    if (s.type === 'markdown') {
      const src: MarkdownSource = { type: 'markdown', path: s.path.trim() || 'TODO.md' }
      if (s.name.trim()) src.name = s.name.trim()
      if (list(s.sections).length) src.sections = list(s.sections)
      src.skip = list(s.skip)
      if (include.length) src.include = include
      return src
    }
    const src: GmailSource = { type: 'gmail', query: s.query.trim() || DEFAULT_GMAIL_QUERY }
    if (s.name.trim()) src.name = s.name.trim()
    if (s.server.trim()) src.server = s.server.trim()
    const max = parseInt(s.max, 10)
    src.max = Number.isFinite(max) && max > 0 ? Math.min(max, 50) : 10
    if (include.length) src.include = include
    return src
  })
  const minutes = parseInt(d.refreshMinutes, 10)
  return { sources, refreshMinutes: Number.isFinite(minutes) && minutes >= 0 ? minutes : 15 }
}

function blankSource(type: Source['type'], hasTodo: boolean): DraftSource {
  return type === 'markdown'
    ? { type, name: 'TODO', path: hasTodo ? 'TODO.md' : '', sections: '', skip: DEFAULT_SKIP.join(', '), include: '', server: '', query: '', max: '' }
    : { type, name: 'Email', path: '', sections: '', skip: '', include: '', server: '', query: DEFAULT_GMAIL_QUERY, max: '10' }
}

// Opens the editor on this session's entry; a folder with no entry gets a starter
// that is saved as a new entry for the session's folder.
async function startEditing($: EngineInterface) {
  const cwd = await $.session.cwd()
  const { settings } = await loadSettings($)
  const picked = settings ? pickWorkspace(settings, cwd) : undefined
  if (picked && picked.key !== 'default') draft = toDraft(picked.key, picked.ws)
  else {
    const hasTodo = await $.fs.exists(join(cwd, 'TODO.md'))
    draft = toDraft(cwd, undefined)
    if (hasTodo) draft.sources.push(blankSource('markdown', true))
    draft.sources.push(blankSource('gmail', false))
  }
  view = 'settings'
  $.ui.invalidate('ui.render')
}

async function saveDraft($: EngineInterface) {
  if (!draft) return
  const path = await settingsPath($)
  if (!path) return $.ui.toast('No home folder found.')
  const { settings, error } = await loadSettings($)
  if (error && (await $.fs.exists(path))) return $.ui.toast(`Not saved: ${error}`)
  const next: Settings = settings ?? { default: { sources: [] }, workspaces: {} }
  next.workspaces ??= {}
  next.workspaces[draft.key] = fromDraft(draft)
  await $.fs.write(path, JSON.stringify(next, null, 2) + '\n')
  $.ui.toast('Today sources saved.')
  view = 'list'
  draft = undefined
  await refresh($)
}

function editDraft($: EngineInterface, fn: (d: Draft) => void) {
  if (!draft) return
  fn(draft)
  $.ui.invalidate('ui.render')
}

// --- Open --------------------------------------------------------------------

export async function openToday($: EngineInterface) {
  view = 'list'
  await $.ui.open({ id: TODAY_PANE, title: 'Today' })
  void refresh($)
}

// The Today pane on its sources and rules editor (called from the Customize pane)
export async function openTodaySettings($: EngineInterface): Promise<void> {
  await $.ui.open({ id: TODAY_PANE, title: 'Today' })
  await startEditing($)
}

function timeOf(ms: number) {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// --- Hooks -------------------------------------------------------------------

// Called from register.tsx's one session.start hook (a module may hook it once)
export async function startToday($: EngineInterface) {
  await $.command.register({ name: 'today', description: 'Open the Today pane: tasks and email for this workspace' })
  const kept = await $.store.get(STORE_KEY)
  if (kept && typeof kept === 'object') snapshot = kept as Snapshot
  const folders = await $.store.get(COLLAPSED_KEY)
  if (Array.isArray(folders)) collapsed = new Set(folders.filter((f): f is string => typeof f === 'string'))
  const sn = await $.store.get(SNOOZED_KEY)
  if (sn && typeof sn === 'object') {
    const now = await $.clock.now()
    snoozed = Object.fromEntries(
      Object.entries(sn as Record<string, unknown>).filter(
        (kv): kv is [string, number] => typeof kv[1] === 'number' && kv[1] > now,
      ),
    )
  }
}

export const registerToday = (on: Parameters<Register>[0]) => {
  on('command.run', { command: 'today' }, async $ => {
    await openToday($)
    return { text: 'Today pane opened.' }
  })

  on('ui.close', async ($, e, next) => {
    if (e.id === TODAY_PANE) {
      timer?.cancel()
      timer = undefined
      view = 'list'
      draft = undefined
    }
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: TODAY_PANE }, async ($, e) => {
    const t = $.ui.resolve(e)
    const { Box, Text, Button, Link } = t
    // The mobile app draws no Input or Select yet: show values as text there
    const Input = 'Input' in t ? t.Input : undefined
    const Select = 'Select' in t ? t.Select : undefined
    const width = Math.max(20, e.props.bodyColumns - 6) // inside a round border with paddingX 1

    // Folder header: ▾ open / ▸ closed, dim when closed
    const folder = (id: string, label: string, count: number, bold = false) => {
      const open = !collapsed.has(id)
      return (
        <Button key={`f-${id}`} plain onPress={() => toggleFolder($, id)}>
          <Text bold={bold} dimColor={!open}>
            {open ? '▾' : '▸'} {label} <Text dimColor>({count})</Text>
          </Text>
        </Button>
      )
    }

    // ---- Settings view ----
    if (view === 'settings' && draft) {
      const d = draft
      const field = (key: string, label: string, value: string, set: (v: string) => void, placeholder?: string) =>
        Input ? (
          <Input
            key={key}
            label={`${label} `}
            value={value}
            placeholder={placeholder}
            submitLabel="set"
            onInput={(v: string) => set(v)}
            onSubmit={(v: string) => editDraft($, () => set(v))}
          />
        ) : (
          <Text>
            {label}: {value || placeholder}
          </Text>
        )
      const where = d.key.split(/[\\/]/).pop() || d.key
      return (
        <Box flexDirection="column" gap={1}>
          <Text bold>Today sources and rules</Text>
          <Text dimColor>For {where}. Saved to your own settings, not the workspace.</Text>
          <Box flexDirection="column" borderStyle="round" paddingX={1}>
            <Text bold>Refresh</Text>
            {field('ts-refresh', 'Every (minutes, 0 = off)', d.refreshMinutes, v => (d.refreshMinutes = v), '15')}
          </Box>
          {d.sources.map((s, i) => (
            <Box key={`ts-src-${i}`} flexDirection="column" borderStyle="round" paddingX={1}>
              <Box flexDirection="row" gap={1} flexWrap="wrap">
                <Text bold>{s.type === 'gmail' ? '✉ Email' : '☐ Markdown file'}</Text>
                {i > 0 && (
                  <Button key={`ts-up-${i}`} plain onPress={() => editDraft($, dd => dd.sources.splice(i - 1, 0, ...dd.sources.splice(i, 1)))}>
                    ↑
                  </Button>
                )}
                <Button key={`ts-del-${i}`} plain onPress={() => editDraft($, dd => dd.sources.splice(i, 1))}>
                  <Text color="error">✕ Remove</Text>
                </Button>
              </Box>
              {field(`ts-name-${i}`, 'Name', s.name, v => (s.name = v))}
              {s.type === 'markdown' && field(`ts-path-${i}`, 'File', s.path, v => (s.path = v), 'TODO.md')}
              {s.type === 'markdown' &&
                field(`ts-sections-${i}`, 'Only headings', s.sections, v => (s.sections = v), 'all; or comma-separated')}
              {s.type === 'markdown' && field(`ts-skip-${i}`, 'Leave out items starting', s.skip, v => (s.skip = v), 'Done, Dropped')}
              {s.type === 'gmail' && field(`ts-query-${i}`, 'Search', s.query, v => (s.query = v), DEFAULT_GMAIL_QUERY)}
              {s.type === 'gmail' && field(`ts-max-${i}`, 'Up to', s.max, v => (s.max = v), '10')}
              {s.type === 'gmail' && field(`ts-server-${i}`, 'Connector', s.server, v => (s.server = v), 'found by itself')}
              {field(`ts-include-${i}`, 'Only items with', s.include, v => (s.include = v), 'any; or comma-separated words')}
            </Box>
          ))}
          <Box flexDirection="row" gap={1} flexWrap="wrap">
            <Text dimColor>Add:</Text>
            {Select ? (
              <Select
                key="ts-add"
                label=""
                options={[
                  { value: 'none', label: 'Choose a source…' },
                  { value: 'markdown', label: '☐ Markdown file' },
                  { value: 'gmail', label: '✉ Email (Gmail)' },
                ]}
                value="none"
                onSelect={(v: string) => {
                  if (v === 'markdown' || v === 'gmail') editDraft($, dd => dd.sources.push(blankSource(v, false)))
                }}
              />
            ) : (
              [
                <Button key="ts-add-md" plain onPress={() => editDraft($, dd => dd.sources.push(blankSource('markdown', false)))}>
                  ☐ Markdown file
                </Button>,
                <Button key="ts-add-gm" plain onPress={() => editDraft($, dd => dd.sources.push(blankSource('gmail', false)))}>
                  ✉ Email
                </Button>,
              ]
            )}
          </Box>
          <Text dimColor>Jira comes later.</Text>
          <Box flexDirection="row" gap={1}>
            <Button key="ts-save" variant="primary" onPress={() => void saveDraft($)}>
              Save
            </Button>
            <Button
              key="ts-cancel"
              onPress={() => {
                view = 'list'
                draft = undefined
                $.ui.invalidate('ui.render')
              }}
            >
              Cancel
            </Button>
          </Box>
        </Box>
      )
    }

    // ---- Task list view ----
    const s = snapshot
    const now = await $.clock.now()
    const hidden = (r: SourceResult, it: Item) => (snoozed[itemKey(r, it)] ?? 0) > now
    const snoozedCount = Object.values(snoozed).filter(t => t > now).length

    const header = (
      <Box flexDirection="column">
        <Text bold>Today</Text>
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          <Button key="today-refresh" plain onPress={() => void refresh($)}>
            ⟳
          </Button>
          <Text dimColor>
            {loading ? 'Refreshing…' : s ? `Updated ${timeOf(s.at)}` : 'Not loaded'}
            {s && s.workspace !== 'default' ? ` · ${s.workspace.split(/[\\/]/).pop()}` : ''}
          </Text>
          <Button key="today-edit" plain onPress={() => void startEditing($)}>
            <Text dimColor>⚙ Sources</Text>
          </Button>
          {snoozedCount > 0 && (
            <Button key="today-unsnooze" plain onPress={() => void unsnoozeAll($)}>
              <Text dimColor>☾ {snoozedCount} snoozed · show</Text>
            </Button>
          )}
        </Box>
      </Box>
    )

    if (!s) return <Box flexDirection="column">{header}</Box>

    const taskRow = (r: SourceResult, it: Item, key: string) => {
      const k = itemKey(r, it)
      return (
        <Box key={key} flexDirection="row" gap={1}>
          {it.href ? (
            <Box flexDirection="column" flexGrow={1}>
              <Link href={it.href}>{cut(it.text, width - 4)}</Link>
              {it.detail && <Text dimColor>{cut(it.detail, width - 4)}</Text>}
            </Box>
          ) : (
            <Box flexGrow={1}>
              <Button
                key={`${key}-go`}
                plain
                onPress={() =>
                  void $.prompt.fill({ text: `Let's work on this task from ${r.name}: ${it.detail ?? it.text}`, mode: 'replace' })
                }
              >
                ○ {cut(it.text, width - 6)}
              </Button>
            </Box>
          )}
          <Button key={`${key}-snooze`} plain onPress={() => void snooze($, k)}>
            <Text dimColor>☾</Text>
          </Button>
        </Box>
      )
    }

    return (
      <Box flexDirection="column" gap={1}>
        {header}
        {s.note && (
          <Box flexDirection="column" borderStyle="round" paddingX={1}>
            <Text dimColor>{s.note}</Text>
            <Button key="today-starter" variant="primary" onPress={() => void startEditing($)}>
              Choose sources
            </Button>
          </Box>
        )}
        {s.results.map((r, i) => {
          const items = r.items.filter(it => !hidden(r, it))
          const srcId = `${s.workspace}|${r.name}`
          const icon = r.kind === 'gmail' ? '✉' : '☐'
          // Sub-folders by heading, in file order
          const groups: { name: string; items: Item[] }[] = []
          for (const it of items) {
            const g = it.group ?? ''
            const found = groups.find(x => x.name === g)
            if (found) found.items.push(it)
            else groups.push({ name: g, items: [it] })
          }
          return (
            <Box key={`src-${i}`} flexDirection="column" borderStyle="round" paddingX={1}>
              {folder(srcId, `${icon} ${r.name}`, items.length, true)}
              {!collapsed.has(srcId) && r.error && <Text color="error">{cut(r.error, width * 3)}</Text>}
              {!collapsed.has(srcId) && !r.error && items.length === 0 && <Text dimColor>Nothing for today.</Text>}
              {!collapsed.has(srcId) &&
                groups.map((g, gi) => {
                  if (!g.name) return g.items.map((it, j) => taskRow(r, it, `i-${i}-${gi}-${j}`))
                  const gid = `${srcId}|${g.name}`
                  return (
                    <Box key={`g-${i}-${gi}`} flexDirection="column">
                      {folder(gid, g.name, g.items.length)}
                      {!collapsed.has(gid) && (
                        <Box flexDirection="column" paddingLeft={2}>
                          {g.items.map((it, j) => taskRow(r, it, `i-${i}-${gi}-${j}`))}
                        </Box>
                      )}
                    </Box>
                  )
                })}
            </Box>
          )
        })}
      </Box>
    )
  })
}

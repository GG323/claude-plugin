import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { BandGroup, BandItem, BandLayout, BuiltinId, PromptMode } from '../types'
import { openToday, openTodaySettings } from './today'

// The band above the prompt and the Customize pane that sets it.
// Which buttons show, in which folders, is set per user in one file:
//   ~/.claude/command-pane/buttons.json  ({ version: 1, groups: [{ id, name, items }] })
// The group with id 'main' is drawn inline; every other group is a folder in the band.

export const CUSTOMIZE_PANE = 'command-pane-customize'
const LAYOUT_REL = '.claude/command-pane/buttons.json'
const MAIN = 'main'

// Shared with register.tsx (its Settings pane and the star prompt)
export const SETTINGS_PANE = 'command-pane-settings'
export const STAR_PROMPT = 'Build a skill based on our conversation, ask if the process to automate is not clear'

const layoutAtom = atom({ plugin: 'command-pane', key: 'layout' } as const, null, { shape: 'layout-1' })
const bandOpen = atom({ plugin: 'command-pane', key: 'bandOpen' } as const, '', { shape: 'open-1' })
const customizeRev = atom({ plugin: 'command-pane', key: 'customizeRev' } as const, 0, { shape: 'crev-1' })

// --- Defaults ----------------------------------------------------------------

const BUILTINS: Record<BuiltinId, { label: string; icon: string; color?: string; group: string; visible: boolean }> = {
  star: { label: 'Star prompt', icon: '★', color: 'warning', group: MAIN, visible: true },
  settings: { label: 'Settings', icon: '⚙', group: MAIN, visible: true },
  today: { label: 'Today', icon: '☰', color: 'suggestion', group: MAIN, visible: true },
  compact: { label: 'Compact', icon: '⇣', group: 'session', visible: false },
  context: { label: 'Context', icon: '◔', group: 'session', visible: false },
  usage: { label: 'Usage', icon: '◷', group: 'session', visible: false },
}
const BUILTIN_IDS = Object.keys(BUILTINS) as BuiltinId[]

const builtinItem = (id: BuiltinId): BandItem => {
  const b = BUILTINS[id]
  return { id: `builtin-${id}`, kind: 'builtin', builtin: id, label: b.label, icon: b.icon, color: b.color, visible: b.visible }
}

function defaultLayout(): BandLayout {
  return {
    version: 1,
    groups: [
      { id: MAIN, name: 'Main', items: BUILTIN_IDS.filter(id => BUILTINS[id].group === MAIN).map(builtinItem) },
      {
        id: 'prompts',
        name: 'Prompts',
        items: [
          {
            id: 'prompt-refresh',
            kind: 'prompt',
            label: 'Refresh',
            icon: '⟳',
            text: 'Re-ground this session: list the supporting materials, the overall tasks done, a bullet list of each task done, and the latest state of the working documents.',
            mode: 'send',
            visible: true,
          },
        ],
      },
      { id: 'session', name: 'Session', items: BUILTIN_IDS.filter(id => BUILTINS[id].group === 'session').map(builtinItem) },
    ],
  }
}

// Keeps a stored layout usable: a main group first, every built-in present once, ids unique
function normalize(input: unknown): BandLayout {
  const raw = input as Partial<BandLayout> | undefined
  if (!raw || !Array.isArray(raw.groups)) return defaultLayout()
  const seen = new Set<string>()
  const groups: BandGroup[] = []
  for (const g of raw.groups) {
    if (!g || typeof g.id !== 'string' || seen.has(g.id)) continue
    seen.add(g.id)
    const items = (Array.isArray(g.items) ? g.items : []).filter(
      (it): it is BandItem =>
        !!it && typeof it.id === 'string' && !seen.has(it.id) && (it.kind === 'prompt' || (it.kind === 'builtin' && !!it.builtin && it.builtin in BUILTINS)) && !!seen.add(it.id),
    )
    groups.push({ id: g.id, name: String(g.name ?? g.id), items })
  }
  if (!groups.some(g => g.id === MAIN)) groups.unshift({ id: MAIN, name: 'Main', items: [] })
  const main = groups.find(g => g.id === MAIN)!
  groups.splice(groups.indexOf(main), 1)
  groups.unshift(main)
  for (const id of BUILTIN_IDS) {
    if (!groups.some(g => g.items.some(it => it.builtin === id))) {
      const home = groups.find(g => g.id === BUILTINS[id].group) ?? main
      home.items.push({ ...builtinItem(id), visible: false })
    }
  }
  return { version: 1, groups }
}

// --- Load and save -----------------------------------------------------------

async function layoutPath($: EngineInterface) {
  const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
  return home ? `${home.replace(/\\/g, '/')}/${LAYOUT_REL}` : undefined
}

async function loadLayout($: EngineInterface): Promise<BandLayout> {
  const path = await layoutPath($)
  try {
    if (path && (await $.fs.exists(path))) return normalize(JSON.parse(await $.fs.read(path)))
  } catch (err) {
    $.ui.toast(`buttons.json could not be read, using the default buttons: ${err instanceof Error ? err.message : String(err)}`)
  }
  return defaultLayout()
}

async function current($: EngineInterface): Promise<BandLayout> {
  return (await read($, layoutAtom)) ?? (await loadLayout($))
}

// Applies a change to the layout, redraws the band and the pane, and saves the file
async function change($: EngineInterface, fn: (layout: BandLayout) => void) {
  const next = structuredClone(await current($)) as BandLayout
  fn(next)
  const fixed = normalize(next)
  await update($, layoutAtom, () => fixed)
  const path = await layoutPath($)
  if (!path) return $.ui.toast('No home folder found; the buttons are kept for this session only.')
  try {
    await $.fs.write(path, JSON.stringify(fixed, null, 2) + '\n')
  } catch (err) {
    $.ui.toast(`Buttons not saved: ${err instanceof Error ? err.message : String(err)}`)
  }
}

const findItem = (layout: BandLayout, id: string) => {
  for (const g of layout.groups) {
    const i = g.items.findIndex(it => it.id === id)
    if (i >= 0) return { group: g, index: i, item: g.items[i]! }
  }
  return undefined
}

const move = <T,>(list: T[], from: number, to: number) => {
  if (to < 0 || to >= list.length) return
  const [x] = list.splice(from, 1)
  list.splice(to, 0, x!)
}

const newId = (prefix: string) => `${prefix}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`

// --- Pressing a button -------------------------------------------------------

async function runPrompt($: EngineInterface, item: BandItem) {
  const text = (item.text ?? '').trim()
  if (!text) return $.ui.toast(`"${item.label}" has no prompt text yet.`)
  if (item.mode !== 'send') return void $.prompt.fill({ text, mode: 'replace' })
  if (text.startsWith('/')) {
    const [name = '', ...rest] = text.slice(1).split(/\s+/)
    try {
      await $.command.run({ command: name, args: rest.join(' ') })
    } catch (err) {
      $.ui.toast(`/${name} did not run: ${err instanceof Error ? err.message : String(err)}`)
    }
    return
  }
  const result = await $.prompt.submit({ text, asUser: true })
  if ('deny' in result && result.deny) $.ui.toast(`Prompt not sent: ${String(result.deny)}`)
}

async function runCommand($: EngineInterface, command: string) {
  try {
    await $.command.run({ command })
  } catch (err) {
    $.ui.toast(`/${command} did not run: ${err instanceof Error ? err.message : String(err)}`)
  }
}

// One literal call per built-in: the validator wants every $ call spelled out where it runs
function press($: EngineInterface, item: BandItem) {
  if (item.kind !== 'builtin') return void runPrompt($, item)
  switch (item.builtin) {
    case 'star': return void $.prompt.fill({ text: STAR_PROMPT, mode: 'replace' })
    case 'settings': return void $.ui.open({ id: SETTINGS_PANE, title: 'Settings' })
    case 'today': return void openToday($)
    case 'compact': return void runCommand($, 'compact')
    case 'context': return void runCommand($, 'context')
    case 'usage': return void runCommand($, 'usage')
  }
}

export async function openCustomize($: EngineInterface) {
  await $.ui.open({ id: CUSTOMIZE_PANE, title: 'Customize buttons' })
}

// --- The prompt form (module variables: typing does not redraw) --------------

type Draft = { editing?: string; label: string; icon: string; text: string; mode: PromptMode; color: string; group: string }
const emptyDraft = (): Draft => ({ label: '', icon: '◆', text: '', mode: 'fill', color: '', group: 'prompts' })
let draft: Draft = emptyDraft()
let formSeq = 0 // part of each field's key, so a new form draws fresh fields
let newGroupName = ''

async function resetForm($: EngineInterface, next: Draft = emptyDraft()) {
  draft = next
  formSeq += 1
  await update($, customizeRev, n => n + 1)
}

async function saveDraft($: EngineInterface) {
  const d = draft
  if (!d.label.trim() && !d.icon.trim()) return $.ui.toast('Give the button a name or an icon.')
  if (!d.text.trim()) return $.ui.toast('Write the prompt the button puts in the chat box.')
  await change($, layout => {
    const group = layout.groups.find(g => g.id === d.group) ?? layout.groups[0]!
    const fields = { label: d.label.trim(), icon: d.icon.trim(), text: d.text, mode: d.mode, color: d.color || undefined }
    const found = d.editing ? findItem(layout, d.editing) : undefined
    if (found) {
      Object.assign(found.item, fields)
      if (found.group.id !== group.id) {
        found.group.items.splice(found.index, 1)
        group.items.push(found.item)
      }
    } else group.items.push({ id: newId('prompt'), kind: 'prompt', visible: true, ...fields })
  })
  $.ui.toast(d.editing ? 'Prompt button saved.' : 'Prompt button added.')
  await resetForm($)
}

// --- Hooks -------------------------------------------------------------------

// Called from register.tsx's one session.start hook
export async function startCustomize($: EngineInterface) {
  await $.command.register({ name: 'buttons', description: 'Customize the command-pane buttons above the prompt' })
  await update($, layoutAtom, () => null) // re-read the file: it may have changed in another session
  const layout = await loadLayout($)
  await update($, layoutAtom, () => layout)
}

const COLORS = ['', 'warning', 'suggestion', 'success', 'error', 'claude', 'remember', 'permission'] as const

export const registerCustomize = (on: Parameters<Register>[0]) => {
  on('command.run', { command: 'buttons' }, async $ => {
    await openCustomize($)
    return { text: 'Customize pane opened.' }
  })

  // The band above the prompt: main buttons inline, folders that open in place, then ✎
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const layout = await current($)
    const open = await read($, bandOpen)

    const itemButton = (item: BandItem) => (
      <Box key={`band-${item.id}`} flexDirection="row" gap={1}>
        <Button key={`band-btn-${item.id}`} plain onPress={() => press($, item)}>
          <Text color={item.color || undefined}>{item.icon || '◆'}</Text>
        </Button>
        {item.label && <Text dimColor>{item.label}</Text>}
      </Box>
    )

    const parts = layout.groups.map(group => {
      const items = group.items.filter(it => it.visible)
      if (items.length === 0) return null
      if (group.id === MAIN) return <Box key="band-main" flexDirection="row" gap={2}>{items.map(itemButton)}</Box>
      const isOpen = open === group.id
      return (
        <Box key={`band-group-${group.id}`} flexDirection="row" gap={1}>
          <Button
            key={`band-folder-${group.id}`}
            plain
            dimColor={!isOpen}
            onPress={() => void update($, bandOpen, now => (now === group.id ? '' : group.id))}
          >
            {`${isOpen ? '▾' : '▸'} ${group.name}`}
          </Button>
          {isOpen && (
            <Box flexDirection="row" gap={2} borderStyle="round" paddingX={1}>
              {items.map(itemButton)}
            </Box>
          )}
        </Box>
      )
    })

    return (
      <Box flexDirection="row" gap={2} flexWrap="wrap" alignItems="center">
        {parts}
        <Button key="band-customize" plain dimColor onPress={() => void openCustomize($)}>
          ✎
        </Button>
      </Box>
    )
  })

  // The Customize pane
  on('ui.render', { component: 'Pane', requestId: CUSTOMIZE_PANE }, async ($, e) => {
    const t = $.ui.resolve(e)
    const { Box, Text, Button } = t
    // The mobile app draws no Input or Select yet: those parts show a note there
    const Input = 'Input' in t ? t.Input : undefined
    const Select = 'Select' in t ? t.Select : undefined
    await read($, customizeRev)
    const layout = await current($)
    const groupOptions = layout.groups.map(g => ({ value: g.id, label: g.name }))
    if (!layout.groups.some(g => g.id === draft.group)) draft.group = layout.groups.find(g => g.id !== MAIN)?.id ?? MAIN

    const itemRow = (group: BandGroup, item: BandItem, index: number) => (
      <Box key={`cz-item-${item.id}`} flexDirection="row" gap={1} flexWrap="wrap" alignItems="center">
        <Text color={item.color || undefined} dimColor={!item.visible}>
          {item.icon || '◆'}
        </Text>
        <Text dimColor={!item.visible}>{item.label || '(no name)'}</Text>
        <Button
          key={`cz-vis-${item.id}`}
          dimColor={!item.visible}
          onPress={() => void change($, l => { const f = findItem(l, item.id); if (f) f.item.visible = !f.item.visible })}
        >
          {item.visible ? 'Shown' : 'Hidden'}
        </Button>
        <Button key={`cz-up-${item.id}`} plain dimColor onPress={() => void change($, l => { const f = findItem(l, item.id); if (f) move(f.group.items, f.index, f.index - 1) })}>
          ↑
        </Button>
        <Button key={`cz-down-${item.id}`} plain dimColor onPress={() => void change($, l => { const f = findItem(l, item.id); if (f) move(f.group.items, f.index, f.index + 1) })}>
          ↓
        </Button>
        {Select && layout.groups.length > 1 && (
          <Select
            key={`cz-move-${item.id}`}
            label="in"
            options={groupOptions}
            value={group.id}
            onSelect={(to: string) =>
              void change($, l => {
                const f = findItem(l, item.id)
                const target = l.groups.find(g => g.id === to)
                if (!f || !target || target === f.group) return
                f.group.items.splice(f.index, 1)
                target.items.push(f.item)
              })
            }
          />
        )}
        {item.kind === 'prompt' && (
          <Button
            key={`cz-edit-${item.id}`}
            plain
            dimColor
            onPress={() =>
              void resetForm($, {
                editing: item.id,
                label: item.label,
                icon: item.icon,
                text: item.text ?? '',
                mode: item.mode ?? 'fill',
                color: item.color ?? '',
                group: group.id,
              })
            }
          >
            Edit
          </Button>
        )}
        {item.kind === 'prompt' && (
          <Button key={`cz-del-${item.id}`} plain dimColor onPress={() => void change($, l => { const f = findItem(l, item.id); if (f) f.group.items.splice(f.index, 1) })}>
            Delete
          </Button>
        )}
      </Box>
    )

    const groupBox = (group: BandGroup, gi: number) => (
      <Box key={`cz-group-${group.id}`} flexDirection="column" borderStyle="round" paddingX={1}>
        <Box flexDirection="row" gap={1} flexWrap="wrap" alignItems="center">
          <Text bold>{group.id === MAIN ? `${group.name} (always shown in the band)` : `▸ ${group.name} (folder)`}</Text>
          {group.id !== MAIN && (
            <Button key={`cz-gup-${group.id}`} plain dimColor onPress={() => void change($, l => move(l.groups, gi, Math.max(1, gi - 1)))}>
              ↑
            </Button>
          )}
          {group.id !== MAIN && (
            <Button key={`cz-gdown-${group.id}`} plain dimColor onPress={() => void change($, l => move(l.groups, gi, gi + 1))}>
              ↓
            </Button>
          )}
          {group.id !== MAIN && (
            <Button
              key={`cz-gdel-${group.id}`}
              plain
              dimColor
              onPress={() =>
                void change($, l => {
                  const i = l.groups.findIndex(g => g.id === group.id)
                  if (i <= 0) return
                  const [gone] = l.groups.splice(i, 1)
                  l.groups[0]!.items.push(...gone!.items.map(it => ({ ...it, visible: false })))
                })
              }
            >
              Delete folder
            </Button>
          )}
        </Box>
        {Input && <Input
          key={`cz-gname-${group.id}-${formSeq}`}
          label="Name"
          value={group.name}
          submitLabel="rename"
          onSubmit={(name: string) => void (name.trim() && change($, l => { const g = l.groups.find(x => x.id === group.id); if (g) g.name = name.trim() }))}
        />}
        {group.items.length === 0 && <Text dimColor>Empty folder.</Text>}
        {group.items.map((item, i) => itemRow(group, item, i))}
      </Box>
    )

    const editing = draft.editing ? findItem(layout, draft.editing)?.item : undefined

    return (
      <Box flexDirection="column" gap={1}>
        <Text dimColor>Choose which buttons show above the prompt, group them in folders, and add your own prompts. Saved for you in ~/{LAYOUT_REL}.</Text>

        <Text bold>Buttons and folders</Text>
        {layout.groups.map(groupBox)}

        {Input && Select ? (
          <Box flexDirection="column" gap={1}>
        <Box flexDirection="row" gap={1} flexWrap="wrap" alignItems="center">
          <Input
            key={`cz-newgroup-${formSeq}`}
            label="New folder"
            placeholder="name, then Enter"
            submitLabel="add"
            onInput={(v: string) => { newGroupName = v }}
            onSubmit={(name: string) => {
              const n = (name || newGroupName).trim()
              if (!n) return
              newGroupName = ''
              void change($, l => { l.groups.push({ id: newId('group'), name: n, items: [] }) }).then(() => resetForm($, draft))
            }}
          />
        </Box>

        <Text bold>{editing ? `Edit prompt button: ${editing.label}` : 'Add a prompt button'}</Text>
        <Box flexDirection="column" gap={1} borderStyle="round" paddingX={1}>
          <Input key={`cz-f-label-${formSeq}`} label="Name" value={draft.label} placeholder="Review" onInput={(v: string) => { draft.label = v }} onSubmit={(v: string) => { draft.label = v }} />
          <Input key={`cz-f-icon-${formSeq}`} label="Icon" value={draft.icon} placeholder="one character, such as ◆ ✓ ✉" onInput={(v: string) => { draft.icon = v }} onSubmit={(v: string) => { draft.icon = v }} />
          <Input
            key={`cz-f-text-${formSeq}`}
            label="Prompt"
            rows={4}
            value={draft.text}
            placeholder="What the button puts in the chat box. Start with / to run a slash command."
            onInput={(v: string) => { draft.text = v }}
            onSubmit={(v: string) => { draft.text = v }}
          />
          <Select
            key={`cz-f-mode-${formSeq}`}
            label="When pressed"
            value={draft.mode}
            options={[
              { value: 'fill', label: 'Put it in the chat box to edit and send' },
              { value: 'send', label: 'Send it at once' },
            ]}
            onSelect={(v: string) => { draft.mode = v === 'send' ? 'send' : 'fill' }}
          />
          <Select
            key={`cz-f-color-${formSeq}`}
            label="Icon colour"
            value={draft.color}
            options={COLORS.map(c => ({ value: c, label: c || 'default' }))}
            onSelect={(v: string) => { draft.color = v }}
          />
          <Select key={`cz-f-group-${formSeq}`} label="Folder" value={draft.group} options={groupOptions} onSelect={(v: string) => { draft.group = v }} />
          <Box flexDirection="row" gap={1}>
            <Button key="cz-f-save" variant="primary" onPress={() => void saveDraft($)}>
              {editing ? 'Save' : 'Add button'}
            </Button>
            {editing && (
              <Button key="cz-f-cancel" onPress={() => void resetForm($)}>
                Cancel
              </Button>
            )}
          </Box>
        </Box>

          </Box>
        ) : (
          <Text dimColor>Adding folders and prompt buttons needs the desktop app or the terminal.</Text>
        )}

        <Text bold>Today</Text>
        <Box flexDirection="row" gap={1}>
          <Button key="cz-today" onPress={() => void openTodaySettings($)}>
            Today sources and rules
          </Button>
        </Box>

        <Box flexDirection="row" gap={1}>
          <Button
            key="cz-reset"
            dimColor
            onPress={() => void change($, l => { l.groups = defaultLayout().groups }).then(() => resetForm($))}
          >
            Reset to the default buttons
          </Button>
        </Box>
      </Box>
    )
  })
}

import type { EngineInterface } from 'claude-code'

// HowToAI change: where this mod's files live (the home folder that holds .claude/).
// The original code cut $.plugin.root at "/.claude/", which fails when the plugin runs in
// place from a folder outside ~/.claude (a directory marketplace). At session start the home
// folder is resolved from, in order:
//   1. USERPROFILE, then HOME
//   2. the paths saved last time in this mod's $.store ("paths", never shown to the user)
//   3. $.plugin.root cut at "/.claude/"
// The first candidate that holds a .claude folder wins and is saved to $.store.
// Until then, and if none qualifies, homeSync() falls back to 3, then to the plugin folder
// itself, as the original code did.
// Each mod calls resolvePaths($) first in its session.start handler (one handler per event is allowed).
// The master copy is token-saving-mods/_shared/paths.ts; each mod ships its own copy in hooks/.

type Paths = { home: string; from: string; at: number }

let resolved: Paths | null = null

const clean = (p: string) =>
  p
    .replace(/\\/g, '/')
    .replace(/^\/([a-zA-Z])\//, (_, d: string) => `${d.toUpperCase()}:/`)
    .replace(/\/+$/, '')

function fromRoot($: EngineInterface) {
  const root = clean($.plugin.root)
  const at = root.indexOf('/.claude/')
  return at > 0 ? root.slice(0, at) : ''
}

/** The home folder (holds .claude/), forward slashes, no trailing slash. */
export function homeSync($: EngineInterface): string {
  return resolved?.home || fromRoot($) || clean($.plugin.root)
}

async function hasClaude($: EngineInterface, home: string) {
  try {
    return await $.fs.exists(`${home}/.claude`)
  } catch {
    return false
  }
}

async function stored($: EngineInterface): Promise<string | undefined> {
  const v = (await $.store.get('paths').catch(() => undefined)) as Partial<Paths> | undefined
  return v && typeof v.home === 'string' ? v.home : undefined
}

export async function resolvePaths($: EngineInterface): Promise<Paths | null> {
  const candidates: [string, () => Promise<string | undefined>][] = [
    ['USERPROFILE', () => $.env.get('USERPROFILE')],
    ['HOME', () => $.env.get('HOME')],
    ['store', () => stored($)],
    ['plugin root', async () => fromRoot($)],
  ]
  for (const [from, get] of candidates) {
    const raw = await get().catch(() => undefined)
    if (typeof raw !== 'string' || !raw) continue
    const home = clean(raw)
    if (!(await hasClaude($, home))) continue
    const changed = resolved?.home !== home
    resolved = { home, from, at: await $.clock.now() }
    if (changed || (await stored($)) !== home) await $.store.set('paths', resolved).catch(() => undefined)
    return resolved
  }
  return null
}

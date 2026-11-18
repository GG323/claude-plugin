import type { EngineInterface } from 'claude-code'

import { openInBrowser, startDetached, waitFor } from './browser'

// The Design studio button: opens skill-design's design studio, a local web app
// (skill-design/scripts/design_studio.py serve) that keeps designs in ~/.claude/howtoai/designs.db.
// A running studio writes ~/.claude/howtoai/design-studio.json = { url, port, pid, started }.
// Press: if that studio answers /api/health, it opens in the user's default browser (browser.tsx).
// Otherwise the mod starts it detached and opens it once healthy; only if that fails is Claude asked.

const RUNTIME_REL = '.claude/howtoai/design-studio.json'
// The studio script inside the howtoai plugin, and where it is found on this machine
const SCRIPT_IN_PLUGIN = 'skills/skill-design/scripts/design_studio.py'
const SCRIPT_IN_SKILLS = '.claude/skills/skill-design/scripts/design_studio.py'
const PLUGIN_CACHE_REL = '.claude/plugins/cache/howtoai-mods/howtoai'

async function homeDir($: EngineInterface) {
  const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
  return home ? home.replace(/\\/g, '/') : undefined
}

// The running studio's URL when it answers its health check, else undefined
async function healthyUrl($: EngineInterface): Promise<string | undefined> {
  const home = await homeDir($)
  if (!home) return undefined
  const path = `${home}/${RUNTIME_REL}`
  try {
    if (!(await $.fs.exists(path))) return undefined
    const runtime = JSON.parse(await $.fs.read(path)) as { url?: unknown }
    const url = typeof runtime.url === 'string' ? runtime.url : ''
    if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+\/$/.test(url)) return undefined
    const res = await $.http.fetch(`${url}api/health`)
    if (!res.ok) return undefined
    const health = JSON.parse(res.text) as { ok?: unknown; app?: unknown }
    return health.ok === true && health.app === 'howtoai-design-studio' ? url : undefined
  } catch {
    return undefined // no file, unreadable, or nothing listening
  }
}

const versionKey = (v: string) => v.split('.').map(n => Number(n) || 0)
const newer = (a: string, b: string) => {
  const x = versionKey(a)
  const y = versionKey(b)
  for (let i = 0; i < Math.max(x.length, y.length); i++) if ((x[i] ?? 0) !== (y[i] ?? 0)) return (x[i] ?? 0) > (y[i] ?? 0)
  return false
}

// The studio script's full path: the user's linked skills folder first, then the newest installed howtoai plugin
async function findScript($: EngineInterface): Promise<string | undefined> {
  const home = await homeDir($)
  if (!home) return undefined
  const linked = `${home}/${SCRIPT_IN_SKILLS}`
  try {
    if (await $.fs.exists(linked)) return linked
  } catch {
    // not readable: try the plugin cache
  }
  try {
    const versions = (await $.fs.list(`${home}/${PLUGIN_CACHE_REL}`)).filter(d => d.kind === 'dir').map(d => d.name)
    versions.sort((a, b) => (newer(a, b) ? -1 : newer(b, a) ? 1 : 0))
    for (const v of versions) {
      const path = `${home}/${PLUGIN_CACHE_REL}/${v}/${SCRIPT_IN_PLUGIN}`
      if (await $.fs.exists(path)) return path
    }
  } catch {
    // no plugin cache
  }
  return undefined
}

async function askToStart($: EngineInterface) {
  const script = await findScript($)
  const where = script
    ? `The script is \`${script}\` (\`${SCRIPT_IN_PLUGIN}\` in the howtoai plugin).`
    : `Find the script \`${SCRIPT_IN_PLUGIN}\` in the installed howtoai plugin (or \`~/${SCRIPT_IN_SKILLS}\`).`
  const text = [
    'Please open the HowToAI design studio (the command-pane Design studio button could not start it).',
    `${where} Start it in the background with \`py -3 "<script>" serve\` (\`python3\` instead of \`py -3\` outside Windows); if a studio is already running it prints its URL and exits.`,
    `Then read the URL from the command's output or from \`~/${RUNTIME_REL}\`, and open it in my default browser.`,
    'Do not change any designs, and tell me in one line when it is open.',
  ].join('\n')
  const res = await $.prompt.submit({ text, asUser: true })
  if ('deny' in res && res.deny) $.ui.toast(`Not sent: ${String(res.deny)}`)
}

// The button's action (called by name from customize.tsx's press switch): open the running
// studio in the default browser; else start it detached, wait for it, and open it; only if
// that fails is Claude asked to start it.
export async function openDesignStudio($: EngineInterface) {
  let url = await healthyUrl($)
  if (!url) {
    const script = await findScript($)
    $.ui.toast('Starting the design studio…')
    const started = !!script && (await startDetached($, 'py', ['-3', script, 'serve']))
    if (started) await waitFor($, async () => !!(url = await healthyUrl($)), 30_000)
    if (!url) return void askToStart($)
  }
  if (!(await openInBrowser($, url))) $.ui.toast(`Could not open the browser. The design studio is at ${url}`)
}

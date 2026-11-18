import type { EngineInterface } from 'claude-code'

// Opening a URL in the user's own default browser (Chrome, Edge, ...) and starting a
// local server that outlives the mod, both through $.process.run with no Claude turn.
// - Windows: rundll32 url.dll,FileProtocolHandler <url> hands the URL to the default browser
//   and returns at once. A server is started with PowerShell's Start-Process, which detaches
//   it (no inherited handles), so it keeps running after the mod reloads.
// - macOS `open`, Linux `xdg-open` for URLs; starting a server there returns false (callers fall back).

async function isWindows($: EngineInterface) {
  return (await $.env.get('OS')) === 'Windows_NT'
}

export async function openInBrowser($: EngineInterface, url: string): Promise<boolean> {
  try {
    const win = await isWindows($)
    const mac = !win && (await $.env.get('HOME'))?.startsWith('/Users/')
    const argv = win ? ['rundll32', 'url.dll,FileProtocolHandler', url] : [mac ? 'open' : 'xdg-open', url]
    const { exitCode } = await $.process.run(argv, { timeoutMs: 10_000 })
    return exitCode === 0
  } catch {
    return false
  }
}

const psQuote = (s: string) => `'${s.replace(/'/g, "''")}'`

// Starts exe with args in cwd, hidden and detached; env is set for the child only.
export async function startDetached(
  $: EngineInterface,
  exe: string,
  args: string[],
  opts: { cwd?: string; env?: Record<string, string>; logFile?: string } = {},
): Promise<boolean> {
  if (!(await isWindows($))) return false
  const parts = [
    ...Object.entries(opts.env ?? {}).map(([k, v]) => `$env:${k}=${psQuote(v)};`),
    'Start-Process -WindowStyle Hidden',
    `-FilePath ${psQuote(exe)}`,
    args.length ? `-ArgumentList ${args.map(a => psQuote(a.includes(' ') ? `"${a}"` : a)).join(',')}` : '',
    opts.cwd ? `-WorkingDirectory ${psQuote(opts.cwd)}` : '',
    opts.logFile ? `-RedirectStandardOutput ${psQuote(opts.logFile)} -RedirectStandardError ${psQuote(opts.logFile + '.err')}` : '',
  ]
  try {
    const { exitCode } = await $.process.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', parts.filter(Boolean).join(' ')], {
      timeoutMs: 20_000,
    })
    return exitCode === 0
  } catch {
    return false
  }
}

// Polls until check() is true or the time runs out
export async function waitFor($: EngineInterface, check: () => Promise<boolean>, timeoutMs: number, stepMs = 1500) {
  const end = (await $.clock.now()) + timeoutMs
  while ((await $.clock.now()) < end) {
    if (await check()) return true
    await $.clock.sleep(stepMs)
  }
  return check()
}

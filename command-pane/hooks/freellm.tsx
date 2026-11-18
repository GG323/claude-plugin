import type { EngineInterface } from 'claude-code'

import { openInBrowser, startDetached, waitFor } from './browser'

// The FreeLLMAPI button: opens the dashboard of a local FreeLLMAPI router
// (https://github.com/tashfeenahmed/freellmapi) in the user's default browser, with no
// Claude turn and no pane. A server install serves the dashboard and the API (/v1) on :3001.
// Press: dashboard answers -> open it. Else start ~/freellmapi/server (node dist/index.js)
// detached, wait for it (it boots in about 30 s), then open it. Only if that fails is
// Claude asked to start it.

const DASHBOARD_URL = 'http://localhost:3001/'
const INSTALL_REL = 'freellmapi'

async function running($: EngineInterface) {
  try {
    return (await $.http.fetch(DASHBOARD_URL)).ok
  } catch {
    return false // nothing listening
  }
}

async function askToStart($: EngineInterface) {
  const text = [
    'Please start my local FreeLLMAPI router (the command-pane FreeLLMAPI button could not start it).',
    'It is a server install, usually in `~/freellmapi`. Start it in the background from its `server` folder with `NODE_ENV=production node dist/index.js`, logging to `~/freellmapi/server.log`; if there is no `dist` yet, run `npm run build` in `~/freellmapi` first.',
    `Then check that ${DASHBOARD_URL} answers and open it in my default browser. Change no keys or settings.`,
  ].join('\n')
  const res = await $.prompt.submit({ text, asUser: true })
  if ('deny' in res && res.deny) $.ui.toast(`Not sent: ${String(res.deny)}`)
}

async function startServer($: EngineInterface) {
  const home = ((await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) ?? '').replace(/\\/g, '/')
  if (!home) return false
  const dir = `${home}/${INSTALL_REL}/server`
  try {
    if (!(await $.fs.exists(`${dir}/dist/index.js`))) return false
  } catch {
    return false
  }
  return startDetached($, 'node', ['dist/index.js'], {
    cwd: dir,
    env: { NODE_ENV: 'production' },
    logFile: `${home}/${INSTALL_REL}/server.log`,
  })
}

// The button's action (called by name from customize.tsx's press switch)
export async function openFreeLlm($: EngineInterface) {
  if (!(await running($))) {
    $.ui.toast('Starting FreeLLMAPI…')
    if (!(await startServer($)) || !(await waitFor($, () => running($), 90_000))) return void askToStart($)
  }
  if (!(await openInBrowser($, DASHBOARD_URL))) $.ui.toast(`Could not open the browser. FreeLLMAPI is at ${DASHBOARD_URL}`)
}

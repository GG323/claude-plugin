// Bumped after every settings change so the Settings pane redraws
export type SettingsRev = number

// The band's buttons, set per user in ~/.claude/command-pane/buttons.json
export type BuiltinId = 'star' | 'settings' | 'today' | 'handover' | 'compact' | 'context' | 'usage'
export type PromptMode = 'fill' | 'send'
export type BandItem = {
  id: string
  kind: 'builtin' | 'prompt'
  builtin?: BuiltinId // kind 'builtin'
  label: string
  icon: string
  color?: string // a theme colour name, such as warning or suggestion
  text?: string // kind 'prompt': what goes in the prompt box (a leading / runs a slash command)
  mode?: PromptMode // kind 'prompt': fill the box, or send at once
  visible: boolean
}
export type BandGroup = {
  id: string // 'main' is drawn inline; any other is a folder in the band
  name: string
  items: BandItem[]
}
export type BandLayout = { version: 1; groups: BandGroup[] }

declare module 'claude-code' {
  interface PluginState {
    'command-pane': {
      settingsRev: Shaped<SettingsRev>
      layout: Shaped<BandLayout | null> // null until loaded at session start
      bandOpen: Shaped<string> // the folder open in the band, '' for none
      customizeRev: Shaped<number> // bumped to redraw the Customize pane's form
    }
  }
}

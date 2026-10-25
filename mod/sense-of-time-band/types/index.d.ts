export type Band = {
  day: string
  block: number
  start: string
  messages: number
  since: string
}

declare module 'claude-code' {
  interface PluginState {
    'sense-of-time-band': { band: Band | null; isHidden: boolean }
  }
}

import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Band } from '../types'

// Reads the sense-of-time hook's event log (timestamps only) and shows which
// block of today's work this chat is in. A block is a run of messages with no
// gap of 30 minutes or more, the same rule the hook uses.

const band = atom({ plugin: 'sense-of-time-band', key: 'band' } as const, null)
const isHidden = atom({ plugin: 'sense-of-time-band', key: 'isHidden' } as const, false)

const GAP_MS = 30 * 60 * 1000
const DAYS = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']

const hhmm = (t: number) => {
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const ago = (ms: number) => {
  const m = Math.floor(ms / 60000)
  if (m < 1) return 'baru saja'
  if (m < 60) return `${m}m`
  return `${Math.floor(m / 60)}j ${m % 60}m`
}

async function refresh($: any) {
  const home = (await $.env.get('HOME')) ?? (await $.env.get('USERPROFILE'))
  if (!home) return
  const path = `${home}/.sense-of-time/events.jsonl`
  if (!(await $.fs.exists(path))) return

  const sid = await $.session.id()
  const now = await $.clock.now()
  const dayKey = new Date(now).toDateString()
  const times: number[] = (await $.fs.read(path))
    .split('\n')
    .filter(Boolean)
    .map((line: string) => {
      try {
        return JSON.parse(line)
      } catch {
        return null
      }
    })
    .filter((e: any) => e && e.session_id === sid)
    .map((e: any) => new Date(e.ts).getTime())
    .filter((t: number) => new Date(t).toDateString() === dayKey)
    .sort((a: number, b: number) => a - b)

  if (times.length === 0) {
    await update($, band, () => null)
    return
  }

  const blocks: number[][] = []
  for (const t of times) {
    const last = blocks[blocks.length - 1]
    if (last && t - last[last.length - 1] < GAP_MS) last.push(t)
    else blocks.push([t])
  }
  const cur = blocks[blocks.length - 1]
  const today = new Date(now)
  const next: Band = {
    day: `${DAYS[today.getDay()]} ${today.getDate()}/${today.getMonth() + 1}`,
    block: blocks.length,
    start: hhmm(cur[0]),
    messages: cur.length,
    since: ago(now - cur[cur.length - 1]),
  }
  await update($, band, () => next)
}

export const register: Register = on => {
  let tick: { cancel(): void } | undefined

  on('session.start', async ($, e, next) => {
    await refresh($)
    tick?.cancel()
    tick = $.clock.every(30000, () => refresh($))
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    const result = await next(e)
    // The Python hook appends the event during submit; read it a moment later.
    $.clock.after(1500, () => refresh($))
    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const b = await read($, band)
    if (e.props.hasSurvey || b === null || (await read($, isHidden))) {
      return next(e)
    }
    const { Box, Button, Text } = $.ui.resolve(e)
    return (
      <Box>
        <Text dimColor>
          {b.day} · blok {b.block} hari ini · mulai {b.start} · {b.messages} pesan · jeda {b.since}{' '}
        </Text>
        <Button key="hide" label="Sembunyikan" onPress={() => update($, isHidden, () => true)} />
      </Box>
    )
  })
}

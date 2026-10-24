# sense-of-time

A spike that gives Claude Code a sense of time with its user: what time it is,
how long you were away, and how deep the current session is. It stores only
timestamps, never message content.

This is the test build. It runs as a Claude Code `UserPromptSubmit` hook on your
own machine. It does not work in claude.ai chat or in Claude Code cloud sessions.

## Install

Requirements: Python 3.11+ on your PATH, Claude Code on Windows, macOS or Linux.

1. Clone this repo somewhere permanent, for example `~/sense-of-time`.
2. Open `~/.claude/settings.json` and add the hook. Use the absolute path to
   your clone, with forward slashes:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python",
            "args": ["/absolute/path/to/sense-of-time/sot_hook.py"],
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

   If `settings.json` already has other keys, add `hooks` next to them. If it
   already has a `hooks` block, add `UserPromptSubmit` inside it.

3. Start a new Claude Code session (hooks load at session start) and send any
   prompt. Then check that an event was recorded:

```bash
cat ~/.sense-of-time/events.jsonl
```

4. Ask Claude what time it is. It should answer from the hook context without
   calling any tool.

## What it does

Before every prompt, the hook appends one event and injects one line of context
such as:

```
[sense-of-time] It is Friday 22:25 (+07:00), late night. The user's previous
message was 12h 38m ago. This session: turn 2, 14m. Guidance: tone concise,
depth light. The user is resuming this conversation after 12h 38m, last active
Friday morning; a one-sentence opener acknowledging the gap is appropriate, once.
```

Rules in the test build. The hook states the situation; Claude writes the
opener in its own words.

Gap since your previous message, in any chat:

| Gap | Opener |
| --- | --- |
| under 30 min | none, "continuing" |
| 30 min to 1 h | a light greeting phrase |
| 1 to 6 h | brief welcome back, ready to continue |
| 3 h or more, past midnight since, no sleep | greeting, and a check whether you want to continue |
| 6 h or more, no sleep | one sentence bridging then to now: how long and how many messages the earlier block ran, what time it is now, where things left off; no greeting ceremony |
| a night's sleep: 3 h or more spanning 03:00, or 6 h or more past midnight | greeting and a short recap of where things left off, with the earlier block's length as a pointer |

"New day" follows you, not the calendar: 21:00 to 02:00 straight through is one
day; sleeping 02:00 to 06:00, or 22:00 to 03:00, starts a new one.

Continuous activity, across chats, with no break over 30 min (each once):

| Active for | Message |
| --- | --- |
| over 3 h | it has been 3 hours, still want to continue? |
| over 6 h | short recap of the day's progress and a reminder to rest |
| over 10 h | another reminder to rest |

Clock, first message in the window that day:

| Time | Message |
| --- | --- |
| start between 04:00 and 06:00, nothing since midnight | greeting noting the very early hour |
| 00:00 to 02:00 | reminder that it is past midnight |
| 02:00 to 04:00 | reminder that morning is near |

Late night (22:00 to 03:00) also sets tone concise and depth light.
Thresholds live at the top of `sot_hook.py`.

## What is stored

One JSON line per prompt in `~/.sense-of-time/events.jsonl`:

```json
{"ts": "2026-10-23T22:29:32+07:00", "session_id": "e936...", "char_count": 38, "tier": 0}
```

No prompt text, ever. Events older than 90 days are ignored. Delete the file to
forget everything.

## Test

```bash
python sot_hook.py --selftest
```

## Uninstall

Remove the `UserPromptSubmit` block from `settings.json` and delete
`~/.sense-of-time/`.

## Feedback we need

Note the moments, with the time, where:

- Claude should have acknowledged the gap or the hour and did not.
- Claude mentioned time and it felt unnecessary or annoying.
- The opener wording felt off.

Those moments decide the thresholds for the next version.

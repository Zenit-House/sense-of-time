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

Rules in the test build:

| Situation | Behaviour |
| --- | --- |
| Gap under 30 min | Silent, "continuing" |
| Gap 30 min to 12 h, same day | Silent |
| Gap that crosses midnight, or 12 h to 7 days | One-sentence opener |
| Gap over 7 days | Opener plus a short recap |
| Late night (22:00 to 03:00) | Tone concise, depth light, nothing said |
| Session over 2.5 h and (late night or messages shrinking) | One sentence offering to save progress, once per session |

Thresholds live at the top of `sot_hook.py`.

## What is stored

One JSON line per prompt in `~/.sense-of-time/events.jsonl`:

```json
{"ts": "2026-10-23T22:29:32+07:00", "session_id": "e936...", "char_count": 38, "fatigue": false}
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

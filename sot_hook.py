#!/usr/bin/env python3
"""sense-of-time spike: Claude Code UserPromptSubmit hook.

Stores timestamps only (no message content), computes Now + Absence + Session,
and returns one line of context for the model. Never blocks a prompt: on any
error it prints nothing and exits 0.

Usage:   registered as a hook (reads hook JSON on stdin)
Test:    python sot_hook.py --selftest
"""
import json
import os
import statistics
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(os.environ.get("SOT_DIR", Path.home() / ".sense-of-time"))
EVENTS = DATA_DIR / "events.jsonl"
SESSION_GAP = timedelta(minutes=30)
RETENTION = timedelta(days=90)

DAYPARTS = [(3, 5, "pre_dawn"), (5, 10, "morning"), (10, 15, "midday"),
            (15, 18, "afternoon"), (18, 22, "evening")]


def daypart(hour):
    for lo, hi, name in DAYPARTS:
        if lo <= hour < hi:
            return name
    return "late_night"


def bucket(gap):
    if gap is None:
        return "first"
    if gap < timedelta(minutes=30):
        return "continuing"
    if gap < timedelta(hours=12):
        return "hours"
    if gap < timedelta(days=7):
        return "days"
    return "long"


def fmt_gap(td):
    s = int(td.total_seconds())
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m = s // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def trend(values, up, down):
    """Median of last 5 vs the 5 before. Needs 10 values, else unknown."""
    if len(values) < 10:
        return "unknown"
    a = statistics.median(values[-5:])
    b = statistics.median(values[-10:-5])
    if b == 0:
        return "stable"
    r = a / b
    return up if r > 1.25 else down if r < 0.8 else ("steady" if up == "slowing" else "stable")


def load_events(now):
    if not EVENTS.exists():
        return []
    out = []
    for line in EVENTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        e["_ts"] = datetime.fromisoformat(e["ts"])
        if now - e["_ts"] <= RETENTION:
            out.append(e)
    return out


def compute(events, now, session_id, char_count):
    prev = events[-1] if events else None
    gap = (now - prev["_ts"]) if prev else None
    b = bucket(gap)

    # Session: trailing run with the same session_id and gaps under 30 min.
    sess = []
    cursor = now
    for e in reversed(events):
        if e["session_id"] != session_id or cursor - e["_ts"] >= SESSION_GAP:
            break
        sess.append(e)
        cursor = e["_ts"]
    sess.reverse()
    turns = len(sess) + 1
    duration = (now - sess[0]["_ts"]) if sess else timedelta(0)
    times = [e["_ts"] for e in sess] + [now]
    reply_gaps = [(times[i] - times[i - 1]).total_seconds() for i in range(1, len(times))]
    tempo = trend(reply_gaps, "slowing", "speeding")
    lengths = [e["char_count"] for e in sess] + [char_count]
    length_trend = trend(lengths, "growing", "shrinking")

    dp = daypart(now.hour)
    weekday = now.strftime("%A")
    is_weekend = now.weekday() >= 5
    fatigue = duration > timedelta(hours=2.5) and (dp == "late_night" or length_trend == "shrinking")
    fatigue_said = any(e.get("fatigue") for e in sess)

    tone, depth = ["direct"] if (dp == "morning" and not is_weekend) else [], "normal"
    if dp == "late_night":
        tone, depth = ["concise"], "light"
    if turns > 30 and length_trend == "shrinking":
        depth = "light"

    mention = None
    new_day = prev is not None and prev["_ts"].astimezone(now.tzinfo).date() != now.date()
    if b in ("days", "long") or (b == "hours" and new_day):
        last = prev["_ts"].astimezone(now.tzinfo)
        where = "resuming this conversation" if prev["session_id"] == session_id else "starting a new session"
        mention = (f"The user is {where} after {fmt_gap(gap)}, last active {last.strftime('%A')} "
                   f"{daypart(last.hour).replace('_', ' ')}; a one-sentence opener acknowledging the gap"
                   f"{' and a short recap of where things left off' if b == 'long' else ''} is appropriate, once.")
    elif fatigue and not fatigue_said:
        mention = (f"This session has run {fmt_gap(duration)}"
                   f"{' late at night' if dp == 'late_night' else ''}; "
                   "one sentence offering to save progress is appropriate, once.")

    parts = [f"It is {weekday} {now.strftime('%H:%M')} ({now.strftime('%z')[:3]}:{now.strftime('%z')[3:]}), {dp.replace('_', ' ')}."]
    if b == "first":
        parts.append("No earlier activity is recorded.")
    elif b == "continuing":
        parts.append("The conversation is continuing; no opener is needed.")
    else:
        parts.append(f"The user's previous message was {fmt_gap(gap)} ago.")
    sess_txt = f"This session: turn {turns}, {fmt_gap(duration)}"
    if tempo != "unknown":
        sess_txt += f", tempo {tempo}"
    if length_trend != "unknown":
        sess_txt += f", messages {length_trend}"
    parts.append(sess_txt + ".")
    parts.append(f"Guidance: tone {', '.join(tone) or 'neutral'}, depth {depth}.")
    parts.append(mention or "Time context shapes tone only and is not mentioned unless the user asks.")

    state = {"daypart": dp, "bucket": b, "turns": turns, "tempo": tempo,
             "length_trend": length_trend, "fatigue": bool(fatigue), "should_mention": mention is not None}
    return state, "[sense-of-time] " + " ".join(parts)


def main():
    data = json.load(sys.stdin)
    now = datetime.now().astimezone()
    events = load_events(now)
    session_id = data.get("session_id", "")
    char_count = len(data.get("prompt", ""))
    state, summary = compute(events, now, session_id, char_count)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    event = {"ts": now.isoformat(timespec="seconds"), "session_id": session_id,
             "char_count": char_count, "fatigue": state["fatigue"]}
    with EVENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": summary}}))


def selftest():
    tz = datetime.now().astimezone().tzinfo
    base = datetime(2026, 10, 23, 21, 34, tzinfo=tz)  # Friday evening
    ev = lambda dt, sid="s1", n=100, fat=False: {"ts": dt.isoformat(), "_ts": dt, "session_id": sid, "char_count": n, "fatigue": fat}

    assert daypart(2) == "late_night" and daypart(3) == "pre_dawn" and daypart(21) == "evening"
    assert bucket(None) == "first" and bucket(timedelta(minutes=29)) == "continuing"
    assert bucket(timedelta(hours=12)) == "days" and bucket(timedelta(days=7)) == "long"
    assert fmt_gap(timedelta(hours=12, minutes=38)) == "12h 38m"

    st, s = compute([], base, "s1", 10)
    assert st["bucket"] == "first" and st["turns"] == 1 and "Friday" in s and "evening" in s

    st, s = compute([ev(base - timedelta(minutes=5))], base, "s1", 10)
    assert st["bucket"] == "continuing" and st["turns"] == 2 and "no opener" in s

    st, s = compute([ev(base - timedelta(minutes=5), sid="other")], base, "s1", 10)
    assert st["turns"] == 1, "different session_id must not join the session"

    st, s = compute([ev(base - timedelta(days=9), sid="old")], base, "s1", 10)
    assert st["bucket"] == "long" and st["should_mention"] and "recap" in s and "new session" in s

    # Next day, same conversation -> opener, resuming; different session -> opener, new session.
    st, s = compute([ev(base - timedelta(hours=14))], base, "s1", 10)
    assert st["bucket"] == "days" and st["should_mention"] and "resuming" in s and "recap" not in s
    st, s = compute([ev(base - timedelta(hours=14), sid="old")], base, "s1", 10)
    assert st["should_mention"] and "new session" in s
    # Short gap that crosses midnight -> opener; same-day 5h gap -> silent.
    morning = datetime(2026, 10, 24, 7, 0, tzinfo=tz)
    st, s = compute([ev(morning - timedelta(hours=8))], morning, "s1", 10)
    assert st["bucket"] == "hours" and st["should_mention"] and "Friday late night" in s
    st, s = compute([ev(base - timedelta(hours=5))], base, "s1", 10)
    assert st["bucket"] == "hours" and not st["should_mention"]

    # Long late-night session with shrinking messages -> fatigue mention, once.
    night = datetime(2026, 10, 23, 23, 50, tzinfo=tz)
    evs = [ev(night - timedelta(minutes=(10 - i) * 20), n=300 if i < 5 else 50) for i in range(10)]
    st, s = compute(evs, night, "s1", 40)
    assert st["fatigue"] and st["should_mention"] and "save progress" in s
    evs[-1]["fatigue"] = True
    st, s = compute(evs, night, "s1", 40)
    assert st["fatigue"] and not st["should_mention"], "fatigue mention must fire once per session"

    # End to end through main() in a temp dir.
    global DATA_DIR, EVENTS
    with tempfile.TemporaryDirectory() as d:
        DATA_DIR, EVENTS = Path(d), Path(d) / "events.jsonl"
        import io
        sys.stdin = io.StringIO(json.dumps({"session_id": "x", "prompt": "hello"}))
        main()
        line = json.loads(EVENTS.read_text().strip())
        assert line["char_count"] == 5 and "prompt" not in line and "hello" not in str(line)
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        try:
            main()
        except Exception as e:  # never block the user's prompt
            print(f"sense-of-time: {e}", file=sys.stderr)

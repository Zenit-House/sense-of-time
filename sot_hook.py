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
STRETCH_TIERS = (10, 6, 3)  # hours of continuous activity, each mentioned once
WAKE_HOUR = 3  # a gap of 3 h+ that spans this hour counts as a night's sleep
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


def split_blocks(times):
    """Sorted datetimes -> runs with no gap of SESSION_GAP or more (the same rule the band mod uses)."""
    blocks = []
    for t in sorted(times):
        if blocks and t - blocks[-1][-1] < SESSION_GAP:
            blocks[-1].append(t)
        else:
            blocks.append([t])
    return blocks


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
    tz = now.tzinfo
    prev = events[-1] if events else None
    gap = (now - prev["_ts"]) if prev else None
    b = bucket(gap)

    def trailing(keep):
        """Trailing run of events, newest first, with every gap under 30 min."""
        run, cursor = [], now
        for e in reversed(events):
            if cursor - e["_ts"] >= SESSION_GAP or not keep(e):
                break
            run.append(e)
            cursor = e["_ts"]
        run.reverse()
        return run

    sess = trailing(lambda e: e["session_id"] == session_id)  # this chat
    stretch = trailing(lambda e: True)  # any chat: "no break over 30 min"
    turns = len(sess) + 1
    duration = (now - sess[0]["_ts"]) if sess else timedelta(0)
    stretch_dur = (now - stretch[0]["_ts"]) if stretch else timedelta(0)
    times = [e["_ts"] for e in sess] + [now]
    reply_gaps = [(times[i] - times[i - 1]).total_seconds() for i in range(1, len(times))]
    tempo = trend(reply_gaps, "slowing", "speeding")
    lengths = [e["char_count"] for e in sess] + [char_count]
    length_trend = trend(lengths, "growing", "shrinking")

    dp = daypart(now.hour)
    weekday = now.strftime("%A")
    is_weekend = now.weekday() >= 5

    tone, depth = ["direct"] if (dp == "morning" and not is_weekend) else [], "normal"
    if dp == "late_night":
        tone, depth = ["concise"], "light"
    if turns > 30 and length_trend == "shrinking":
        depth = "light"

    notes = []
    marker = lambda t: f"It is {t.astimezone(tz).strftime('%A %H:%M')}"
    # This chat's own absence: the user may have just been busy in another chat, yet this project went untouched for days.
    chat_ev = [e for e in events if e["session_id"] == session_id]
    chat_note = None
    if chat_ev and prev["session_id"] != session_id and now - chat_ev[-1]["_ts"] >= timedelta(hours=6):
        clast = chat_ev[-1]["_ts"]
        cday, cursor = [chat_ev[-1]], clast
        for e in reversed(chat_ev[:-1]):
            if cursor - e["_ts"] >= timedelta(hours=6):
                break
            cday.append(e)
            cursor = e["_ts"]
        chat_note = (f"This conversation itself was last touched {fmt_gap(now - clast)} ago, "
                     f"{clast.astimezone(tz).strftime('%A')} {daypart(clast.astimezone(tz).hour).replace('_', ' ')}, "
                     f"while the user was last active {fmt_gap(gap)} ago in another chat. Greet from their overall activity, "
                     f"then add a short recap of this conversation's last session only, between the markers "
                     f"'{marker(cursor)}' and '{marker(clast)}' ({len(cday)} messages): what got done and what was left "
                     "unresolved, ignoring everything before it.")
    # Absence: what kind of opener the gap since the previous message calls for.
    if prev and b != "continuing":
        last = prev["_ts"].astimezone(tz)
        hrs = gap.total_seconds() / 3600
        # "New day" means they slept: a gap of 3 h+ that spans WAKE_HOUR, whatever the calendar says.
        wake = now.replace(hour=WAKE_HOUR, minute=0, second=0, microsecond=0)
        if wake > now:
            wake -= timedelta(days=1)
        crossed_midnight = last.date() != now.date()
        new_day = (hrs >= 3 and last < wake) or (crossed_midnight and hrs >= 6)
        where = ("resuming this conversation" if prev["session_id"] == session_id
                 else "back in this conversation from another chat" if chat_ev else "starting a new chat")
        back = (f"The user is {where} after {fmt_gap(gap)}, last active {last.strftime('%A')} "
                f"{daypart(last.hour).replace('_', ' ')}")
        # The work they left: the previous day = events back from prev with no sleep-length gap (6 h+).
        day, cursor = [prev], prev["_ts"]
        for e in reversed(events[:-1]):
            if cursor - e["_ts"] >= timedelta(hours=6):
                break
            day.append(e)
            cursor = e["_ts"]
        # Only this chat's part of that day can be recapped: its hook lines are the time markers in the transcript.
        mine = [e for e in day if e["session_id"] == session_id]
        if chat_note:
            recap = "then the recap of this conversation described below"
        elif mine:
            window = (f"between the markers '{marker(mine[-1]['_ts'])}' and '{marker(mine[0]['_ts'])}' "
                      f"in this conversation ({len(mine)} messages)")
            recap = (f"then recap only what happened {window}: what got done and what was left unresolved, "
                     "and ignore everything before that window")
        else:
            recap = ("this chat has no history of that work, so do not invent a recap; offer to pick up "
                     "from where they left off if they point you at it")
        # shortcut: a prompt of 40+ characters counts as a task, tune if greeting-only messages misfire
        close = ("Their message already carries a task: close the opener with a short 'let's continue' and go straight to it."
                 if char_count >= 40 else "Their message is short: close the opener by asking what to pick up first.")
        greet = f"Open with a {dp.replace('_', ' ')} greeting in the user's language and register"
        if new_day:
            notes.append(f"{back}, on a new day. {greet}, two or three sentences: name the gap, {recap}. {close}")
        elif crossed_midnight and hrs >= 3:
            notes.append(f"{back}, past midnight since. {greet}, then a check whether they want to continue. {close}")
        elif hrs >= 6:
            notes.append(f"{back}; it is now {dp.replace('_', ' ')}. One sentence bridging then to now"
                         + (f", pointing at the last unresolved thing {window}" if mine and not chat_note else "")
                         + f", with no greeting ceremony. {close}")
        elif hrs >= 1:
            notes.append(back + ". Open with one full sentence of welcome back that names the break and offers to pick up "
                         "(like 'back from the break? let's pick it up'), in the user's register, worded differently from "
                         "every earlier opener in this conversation.")
        else:
            notes.append(back + ". Open with one short, light greeting sentence that acknowledges the pause and moves on "
                         "(like 'short break done? let's continue'), in the user's register, worded differently from "
                         "every earlier opener in this conversation.")
    if chat_note:
        notes.append(chat_note)
    # A new block of this chat today (first message, or a gap of 30 min+): a visible chapter, numbered within the day.
    chat = [e["_ts"] for e in events if e["session_id"] == session_id]
    todays = [t for t in chat if t.astimezone(tz).date() == now.date()]
    if chat and (not todays or now - todays[-1] >= SESSION_GAP):
        title = f"{now.strftime('%A %H:%M')} · block {len(split_blocks(todays)) + 1}"
        notes.append(f"This message starts a new block of today's work in this chat. Before answering, mark a chapter titled "
                     f"'{title}' if a chapter tool exists; otherwise open the reply with the line '── {title} ──'.")
    # Stretch: continuous activity across chats, each tier mentioned once.
    tier = next((t for t in STRETCH_TIERS if stretch_dur > timedelta(hours=t)), 0)
    tier_said = max((e.get("tier", 0) for e in stretch), default=0)
    if tier > tier_said:
        notes.append(f"The user has been active for {fmt_gap(stretch_dur)} with no break over 30 min" + {
            3: "; one sentence noting it has been over 3 hours and asking whether they want to continue is appropriate, once.",
            6: "; a short recap of the progress so far and a reminder to rest is appropriate, once.",
            10: "; another reminder to rest is appropriate, once."}[tier])
    # Clock: first message in a sensitive window today.
    today = [e["_ts"].astimezone(tz).hour for e in events if e["_ts"].astimezone(tz).date() == now.date()]
    hhmm = now.strftime("%H:%M")
    if not stretch and 4 <= now.hour < 6 and not today:
        notes.append(f"The user is starting at {hhmm} with no activity since midnight; a greeting noting the very early hour is appropriate.")
    if now.hour < 2 and not any(h < 2 for h in today):
        notes.append(f"It is {hhmm}, the user's first message past midnight; a reminder that it is past midnight is appropriate, once.")
    if 2 <= now.hour < 4 and not any(2 <= h < 4 for h in today):
        notes.append(f"It is {hhmm}, the user's first message in the small hours; a reminder that morning is near is appropriate, once.")

    parts = [f"It is {weekday} {hhmm} ({now.strftime('%z')[:3]}:{now.strftime('%z')[3:]}), {dp.replace('_', ' ')}."]
    if b == "first":
        parts.append("No earlier activity is recorded.")
    elif b == "continuing" and not chat_note:
        parts.append("The conversation is continuing; no opener is needed.")
    sess_txt = f"This session: turn {turns}, {fmt_gap(duration)}"
    if tempo != "unknown":
        sess_txt += f", tempo {tempo}"
    if length_trend != "unknown":
        sess_txt += f", messages {length_trend}"
    parts.append(sess_txt + ".")
    parts.append(f"Guidance: tone {', '.join(tone) or 'neutral'}, depth {depth}.")
    parts.append(" ".join(notes) + " The opener is the reply's own first paragraph: one line, then a blank line, then the answer; never at the end."
                 if notes else "Time context shapes tone only and is not mentioned unless the user asks.")

    state = {"daypart": dp, "bucket": b, "turns": turns, "tempo": tempo, "length_trend": length_trend,
             "tier": tier, "notes": len(notes), "should_mention": bool(notes)}
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
             "char_count": char_count, "tier": state["tier"]}
    with EVENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": summary}}))


def today():
    """Print today's blocks of work, per chat: the map the band mod draws, on demand."""
    now = datetime.now().astimezone()
    by_chat = {}
    for e in load_events(now):
        if e["_ts"].astimezone(now.tzinfo).date() == now.date():
            by_chat.setdefault(e["session_id"], []).append(e["_ts"])
    rows = sorted((blk[0], blk[-1], len(blk), sid[:8]) for sid, ts in by_chat.items() for blk in split_blocks(ts))
    print(now.strftime("%A %Y-%m-%d"))
    for a, z, n, sid in rows:
        print(f"  {a.astimezone(now.tzinfo):%H:%M}-{z.astimezone(now.tzinfo):%H:%M}  {n:>3} messages  chat {sid}")


def selftest():
    tz = datetime.now().astimezone().tzinfo
    base = datetime(2026, 10, 23, 21, 34, tzinfo=tz)  # Friday evening
    at = lambda h, m=0, day=23: datetime(2026, 10, day, h, m, tzinfo=tz)
    ev = lambda dt, sid="s1", n=100, tier=0: {"ts": dt.isoformat(), "_ts": dt, "session_id": sid, "char_count": n, "tier": tier}

    assert daypart(2) == "late_night" and daypart(3) == "pre_dawn" and daypart(21) == "evening"
    assert bucket(None) == "first" and bucket(timedelta(minutes=29)) == "continuing"
    assert fmt_gap(timedelta(hours=12, minutes=38)) == "12h 38m"
    assert [len(b) for b in split_blocks([at(9), at(9, 5), at(9, 40), at(13)])] == [2, 1, 1]
    # Per-chat absence: this chat last touched days ago, the user busy elsewhere 20 min ago -> greet + recap this chat.
    old = [ev(at(21, day=16)), ev(at(22, day=16)), ev(at(13, day=17))]  # 13:00 next day is a separate later session
    st, s = compute(old + [ev(base - timedelta(minutes=20), sid="other")], base, "s1", 10)
    assert "last touched 6d 8h ago" in s and "20m ago in another chat" in s and "no opener is needed" not in s
    assert "'It is Saturday 13:00' and 'It is Saturday 13:00' (1 messages)" in s
    st, s = compute(old + [ev(base - timedelta(hours=8), sid="other")], base, "s1", 10)
    assert "back in this conversation from another chat" in s and "last touched" in s and "no history" not in s
    st, s = compute([ev(base - timedelta(hours=2)), ev(base - timedelta(minutes=20), sid="other")], base, "s1", 10)
    assert "last touched" not in s, "a 2 h old chat needs no recap"
    # Chapter: a 30 min+ gap in this chat starts block 2 of today; a continuing message does not.
    st, s = compute([ev(at(9)), ev(at(9, 5))], at(9, 40), "s1", 10)
    assert "mark a chapter titled 'Friday 09:40 · block 2'" in s
    st, s = compute([ev(at(9)), ev(at(9, 5))], at(9, 20), "s1", 10)
    assert "chapter" not in s
    st, s = compute([ev(at(9), sid="other")], at(9, 40), "s1", 10)
    assert "chapter" not in s, "a brand-new chat gets no chapter on its first message"

    st, s = compute([], base, "s1", 10)
    assert st["bucket"] == "first" and st["turns"] == 1 and "Friday" in s and not st["should_mention"]
    st, s = compute([ev(base - timedelta(minutes=20))], base, "s1", 10)
    assert st["turns"] == 2 and "no opener" in s and not st["should_mention"]
    st, s = compute([ev(base - timedelta(minutes=5), sid="other")], base, "s1", 10)
    assert st["turns"] == 1, "different session_id must not join the session"

    # Absence tiers, same day.
    one = lambda gap, **kw: compute([ev(base - gap, **kw)], base, "s1", 10)
    st, s = one(timedelta(minutes=40));  assert st["notes"] == 2 and "light greeting" in s and "resuming" in s and "block 2" in s
    assert "own first paragraph" in s and "worded differently" in s
    st, s = one(timedelta(hours=2));     assert "welcome back" in s
    st, s = one(timedelta(hours=7));     assert "bridging then to now" in s and "(1 messages)" in s
    # The recap window is the previous day's work in this chat, named by the hook's own transcript markers.
    morning = [ev(at(9)), ev(at(9, 20)), ev(at(9, 45)), ev(at(11)), ev(at(11, 30), sid="other")]
    st, s = compute(morning, base, "s1", 10)
    assert "'It is Friday 09:00' and 'It is Friday 11:00' (4 messages)" in s and "now evening" in s
    st, s = compute(morning, base, "s9", 10)
    assert "between the markers" not in s and "bridging" in s, "another chat gets no pointer into this transcript"
    st, s = one(timedelta(hours=2), sid="old"); assert "new chat" in s
    # Day-after openers: greeting by daypart, recap window, and a close that depends on the message.
    st, s = compute([ev(at(22))], at(9, day=24), "s1", 10)
    assert "morning greeting" in s and "between the markers 'It is Friday 22:00' and 'It is Friday 22:00'" in s and "asking what to pick up" in s
    st, s = compute([ev(at(22))], at(9, day=24), "s1", 120)
    assert "let's continue" in s
    st, s = compute([ev(at(22), sid="old")], at(9, day=24), "s1", 10)
    assert "do not invent a recap" in s
    # Absence tiers across midnight (now 02:00 Saturday, also first message in the small hours).
    two_am = at(2, day=24)
    st, s = compute([ev(at(0, 30, day=24))], two_am, "s1", 10)
    assert "welcome back" in s and "morning is near" in s and st["notes"] == 3
    st, s = compute([ev(at(22))], two_am, "s1", 10)
    assert "check whether they want to continue" in s and "morning is near" in s
    st, s = compute([ev(at(19))], two_am, "s1", 10)
    assert "new day" in s and "recap" in s
    # Sleep gaps are a new day whatever the calendar says: 01:09 -> 12:42, 02:00 -> 06:00, 22:00 -> 03:00.
    for last_dt, now_dt in [(at(1, 9, day=24), at(12, 42, day=24)), (at(2, day=24), at(6, day=24)), (at(22), at(3, day=24))]:
        st, s = compute([ev(last_dt)], now_dt, "s1", 10)
        assert "new day" in s and "recap" in s, (last_dt, now_dt)
    # 22:00 -> 01:30 crossed midnight but no sleep: check whether they want to continue.
    st, s = compute([ev(at(22))], at(1, 30, day=24), "s1", 10)
    assert "check whether they want to continue" in s and "new day" not in s
    st, s = compute([ev(at(19), tier=0), ev(at(2, 10, day=24))], at(2, 30, day=24), "s1", 10)
    assert "morning is near" not in s, "small-hours reminder fires once per night"

    # Stretch tiers: continuous activity across two chats, each tier once.
    evs = [ev(base - timedelta(minutes=(10 - i) * 20), sid="a" if i < 5 else "s1") for i in range(10)]
    st, s = compute(evs, base, "s1", 10)
    assert st["tier"] == 3 and "over 3 hours" in s and st["turns"] == 6
    for e in evs: e["tier"] = 3
    st, s = compute(evs, base, "s1", 10)
    assert st["tier"] == 3 and not st["should_mention"], "tier 3 must be mentioned once"
    evs = [ev(base - timedelta(minutes=(20 - i) * 20), tier=3) for i in range(20)]
    st, s = compute(evs, base, "s1", 10)
    assert st["tier"] == 6 and "reminder to rest" in s and "recap" in s
    evs = [ev(base - timedelta(minutes=(32 - i) * 20), tier=6) for i in range(32)]
    st, s = compute(evs, base, "s1", 10)
    assert st["tier"] == 10 and "another reminder to rest" in s

    # Clock: very early start, past midnight.
    st, s = compute([ev(at(21))], at(5, day=24), "s1", 10)
    assert "very early hour" in s and "new day" in s
    st, s = compute([ev(at(0, 30, day=24))], at(5, day=24), "s1", 10)
    assert "very early hour" not in s, "no early greeting after activity since midnight"
    st, s = compute([ev(at(23, 50))], at(0, 5, day=24), "s1", 10)
    assert st["notes"] == 2 and "past midnight" in s and "block 1" in s  # the midnight reminder plus the new day's first block
    st, s = compute([ev(at(23, 50)), ev(at(0, 5, day=24))], at(0, 20, day=24), "s1", 10)
    assert not st["should_mention"], "midnight reminder fires once"

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
    elif "--today" in sys.argv:
        today()
    else:
        try:
            main()
        except Exception as e:  # never block the user's prompt
            print(f"sense-of-time: {e}", file=sys.stderr)

#!/usr/bin/env python3
"""Collect usage statistics from Claude Code session logs (~/.claude/projects/*/*.jsonl).

Outputs a JSON summary to stdout: sessions, activity by day/hour/weekday,
skill invocations, tool usage, models, first user prompts, session sizes.
Claude then interprets this JSON and builds the HTML report.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")

def parse_ts(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

def main():
    days_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    cutoff = datetime.now().astimezone() - timedelta(days=days_limit)

    sessions = []
    skill_calls = Counter()
    tool_calls = Counter()
    models = Counter()
    hours = Counter()
    weekdays = Counter()
    days = Counter()
    projects = Counter()
    first_prompts = []
    lang_ru = 0
    lang_en = 0
    subagent_sessions = 0
    total_user_msgs = 0
    total_asst_msgs = 0
    seen_msgs = set()  # the log repeats one API message once per content block - count each message id once
    tok_model = defaultdict(lambda: Counter())   # model -> requests/input/output/cache_read/cache_write/thinking
    tok_day = defaultdict(lambda: Counter())     # YYYY-MM-DD -> same counters
    tok_effort = defaultdict(lambda: Counter())  # effort level -> requests/output/new_input/cache_read
    tok_effort_model = Counter()                 # "model|effort" -> requests
    tok_side = Counter()                         # main vs subagent (sidechain) tokens
    effort_cmds = Counter()                      # /effort <level> commands issued

    def add_usage(d, msg, ts, sess, sub):
        u = msg.get("usage"); mdl = msg.get("model")
        if not isinstance(u, dict) or (ts is not None and ts < cutoff):
            return
        o = u.get("output_tokens", 0) or 0
        i_ = u.get("input_tokens", 0) or 0
        cr = u.get("cache_read_input_tokens", 0) or 0
        cw = u.get("cache_creation_input_tokens", 0) or 0
        th = (u.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0
        eff = d.get("effort") or d.get("perTurnEffort") or "unknown"
        dkey = ts.astimezone().strftime("%Y-%m-%d") if ts else "unknown"
        for c in (tok_model[mdl or "unknown"], tok_day[dkey]):
            c["requests"] += 1; c["input"] += i_; c["output"] += o
            c["cache_read"] += cr; c["cache_write"] += cw; c["thinking"] += th
        e = tok_effort[eff]
        e["requests"] += 1; e["output"] += o; e["new_input"] += i_ + cw; e["cache_read"] += cr
        tok_effort_model[f"{mdl or 'unknown'}|{eff}"] += 1
        tok_side["subagent" if (sub or d.get("isSidechain")) else "main"] += o + i_ + cw
        if sess is not None:
            sess["tok_out"] += o; sess["tok_in"] += i_ + cw; sess["tok_cache_read"] += cr

    for proj in os.listdir(PROJECTS_DIR):
        pdir = os.path.join(PROJECTS_DIR, proj)
        if not os.path.isdir(pdir):
            continue
        for fn in os.listdir(pdir):
            if not fn.endswith(".jsonl"):
                continue
            path = os.path.join(pdir, fn)
            size = os.path.getsize(path)
            sess = {
                "project": proj,
                "size": size,
                "start": None,
                "end": None,
                "user_msgs": 0,
                "asst_msgs": 0,
                "skills": [],
                "first_prompt": None,
                "has_subagent": False,
                "tok_out": 0, "tok_in": 0, "tok_cache_read": 0,
            }
            try:
                with open(path, "r", errors="replace") as fh:
                    for line in fh:
                        try:
                            d = json.loads(line)
                        except Exception:
                            continue
                        ts = parse_ts(d.get("timestamp", "")) if d.get("timestamp") else None
                        if ts:
                            if sess["start"] is None or ts < sess["start"]:
                                sess["start"] = ts
                            if sess["end"] is None or ts > sess["end"]:
                                sess["end"] = ts
                        t = d.get("type")
                        if t == "user" and not d.get("isMeta") and not d.get("isSidechain"):
                            msg = d.get("message", {})
                            content = msg.get("content")
                            text = None
                            if isinstance(content, str):
                                text = content
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "text":
                                        text = c.get("text")
                                        break
                            if text and not text.startswith("<"):
                                sess["user_msgs"] += 1
                                if sess["first_prompt"] is None:
                                    sess["first_prompt"] = text[:200]
                                if re.search(r"[а-яА-ЯёЁ]", text):
                                    nonlocal_ru = 1
                                    globals()  # no-op
                                    sess.setdefault("ru", 0)
                                    sess["ru"] = sess.get("ru", 0) + 1
                                else:
                                    sess["en"] = sess.get("en", 0) + 1
                            # skill/command invocations
                            if text and "<command-name>" in text:
                                m = re.search(r"<command-name>/?([\w-]+)</command-name>", text)
                                if m:
                                    sess["skills"].append(m.group(1))
                                    if m.group(1) == "effort":
                                        a = re.search(r"<command-args>\s*([\w-]+)\s*</command-args>", text)
                                        if a:
                                            effort_cmds[a.group(1)] += 1
                        elif t == "assistant":
                            msg = d.get("message", {})
                            mdl = msg.get("model")
                            mid = msg.get("id")
                            first = mid is None or mid not in seen_msgs
                            if mid is not None:
                                seen_msgs.add(mid)
                            if mdl and first:
                                models[mdl] += 1
                            if first:
                                add_usage(d, msg, ts, sess, False)
                            content = msg.get("content", [])
                            if isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "tool_use":
                                        name = c.get("name", "")
                                        tool_calls[name] += 1
                                        if name == "Skill":
                                            sk = (c.get("input") or {}).get("skill")
                                            if sk:
                                                sess["skills"].append(sk)
                                        if name in ("Agent", "Task"):
                                            sess["has_subagent"] = True
                            if first and not d.get("isSidechain"):
                                sess["asst_msgs"] += 1
            except Exception:
                continue

            if sess["start"] is None or sess["start"] < cutoff:
                # still count old sessions in totals but skip detailed activity
                pass
            if sess["user_msgs"] == 0 and not sess["skills"]:
                continue  # empty session

            sessions.append(sess)

    # subagent logs live in <project>/<session>/subagents/*.jsonl - tokens only, not sessions
    for proj in os.listdir(PROJECTS_DIR):
        pdir = os.path.join(PROJECTS_DIR, proj)
        if not os.path.isdir(pdir):
            continue
        for sd in os.listdir(pdir):
            subdir = os.path.join(pdir, sd, "subagents")
            if not os.path.isdir(subdir):
                continue
            for fn in os.listdir(subdir):
                if not fn.endswith(".jsonl"):
                    continue
                try:
                    with open(os.path.join(subdir, fn), "r", errors="replace") as fh:
                        for line in fh:
                            try:
                                d = json.loads(line)
                            except Exception:
                                continue
                            if d.get("type") != "assistant":
                                continue
                            msg = d.get("message", {})
                            mid = msg.get("id")
                            if mid is not None:
                                if mid in seen_msgs:
                                    continue
                                seen_msgs.add(mid)
                            add_usage(d, msg, parse_ts(d.get("timestamp", "")) if d.get("timestamp") else None, None, True)
                except Exception:
                    continue

    # aggregate
    out_sessions = []
    for s in sessions:
        if s["start"]:
            local = s["start"].astimezone()
            hours[local.hour] += 1
            weekdays[local.strftime("%a")] += 1
            days[local.strftime("%Y-%m-%d")] += 1
        projects[s["project"]] += 1
        for sk in s["skills"]:
            skill_calls[sk] += 1
        if s["has_subagent"]:
            subagent_sessions += 1
        total_user_msgs += s["user_msgs"]
        total_asst_msgs += s["asst_msgs"]
        lang_ru += s.get("ru", 0)
        lang_en += s.get("en", 0)
        dur = None
        if s["start"] and s["end"]:
            dur = round((s["end"] - s["start"]).total_seconds() / 60, 1)
        out_sessions.append({
            "project": s["project"].split("-")[-1] or s["project"],
            "date": s["start"].astimezone().strftime("%Y-%m-%d %H:%M") if s["start"] else None,
            "duration_min": dur,
            "user_msgs": s["user_msgs"],
            "size_kb": round(s["size"] / 1024),
            "skills": s["skills"],
            "first_prompt": s["first_prompt"],
            "tokens_out": s["tok_out"],
            "tokens_new_in": s["tok_in"],
            "tokens_cache_read": s["tok_cache_read"],
        })

    out_sessions.sort(key=lambda x: x["date"] or "", reverse=True)

    weeks = Counter()
    for k, v in days.items():
        day_dt = datetime.strptime(k, "%Y-%m-%d")
        monday = (day_dt - timedelta(days=day_dt.weekday())).strftime("%Y-%m-%d")
        weeks[monday] += v

    def rollup(c):
        tot_in = c["input"] + c["cache_read"] + c["cache_write"]
        return {**dict(c), "cache_hit_rate": round(c["cache_read"] / tot_in, 3) if tot_in else None}
    all_tok = Counter()
    for c in tok_model.values():
        all_tok.update(c)
    tok_weeks = defaultdict(lambda: Counter())
    for k, c in tok_day.items():
        if k == "unknown":
            continue
        day_dt = datetime.strptime(k, "%Y-%m-%d")
        tok_weeks[(day_dt - timedelta(days=day_dt.weekday())).strftime("%Y-%m-%d")].update(c)
    heavy = sorted(out_sessions, key=lambda x: x["tokens_out"] + x["tokens_new_in"], reverse=True)[:10]

    result = {
        "generated": datetime.now().astimezone().isoformat(),
        "total_sessions": len(sessions),
        "total_user_msgs": total_user_msgs,
        "total_asst_msgs": total_asst_msgs,
        "lang_msgs": {"ru": lang_ru, "en": lang_en},
        "subagent_sessions": subagent_sessions,
        "projects": dict(projects),
        "skill_calls": dict(skill_calls.most_common()),
        "tool_calls": dict(tool_calls.most_common(30)),
        "models": dict(models),
        "activity_by_hour": {str(h): hours.get(h, 0) for h in range(24)},
        "activity_by_weekday": {d: weekdays.get(d, 0) for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]},
        "activity_by_day": dict(sorted(days.items())),
        "activity_by_week": dict(sorted(weeks.items())),
        "tokens": {
            "note": "unique API messages only, main sessions + subagent logs; new_input = input + cache_write; cache_hit_rate = cache_read / all input",
            "total": rollup(all_tok),
            "by_model": {m: rollup(c) for m, c in sorted(tok_model.items(), key=lambda x: -x[1]["output"])},
            "by_day": {k: {"requests": c["requests"], "output": c["output"], "new_input": c["input"] + c["cache_write"], "cache_read": c["cache_read"]} for k, c in sorted(tok_day.items())},
            "by_week": {k: {"requests": c["requests"], "output": c["output"], "new_input": c["input"] + c["cache_write"], "cache_read": c["cache_read"]} for k, c in sorted(tok_weeks.items())},
            "by_effort": {e: dict(c) for e, c in sorted(tok_effort.items(), key=lambda x: -x[1]["requests"])},
            "model_x_effort_requests": dict(tok_effort_model.most_common()),
            "effort_commands": dict(effort_cmds),
            "main_vs_subagent_tokens": dict(tok_side),
            "heaviest_sessions": [{k: h[k] for k in ("date", "duration_min", "tokens_out", "tokens_new_in", "tokens_cache_read", "first_prompt")} for h in heavy],
        },
        "recent_sessions": out_sessions[:60],
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()

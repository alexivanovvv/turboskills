---
name: usage-insights
description: Analyze how you use Claude Code - sessions, skills, tools, models, rhythm, automation, long-running sessions - and produce a minimal HTML report with insights and concrete recommendations that opens in the browser. Use when you say "analyze how I use Claude Code", "usage insights", "audit my sessions and skills", "which skills do I never use", or /usage-insights.
---

# Usage Insights

Reads your local Claude Code session logs (`~/.claude/projects/*/*.jsonl`), installed skills and scheduled jobs, and turns them into a one-file HTML report: what you do, how you work, what to automate, what to clean up. Nothing leaves your machine.

Write the report in the language you and the user speak.

## Steps

1. **Collect stats** (about 10 seconds):
   ```bash
   python3 ~/.claude/skills/usage-insights/collect_stats.py 90 > /tmp/usage_stats.json
   ```
   Argument = window in days (default 90). The JSON has: session count, user/assistant messages, activity by day/week/hour/weekday, skill calls, top tools, models, language split, **token analytics** (`tokens`: by model, day, week, effort level, main vs subagents, heaviest sessions), share of sessions with subagents, and the most recent sessions (date, duration, size, skills, first 200 chars of the first prompt).
   Logs older than your retention setting are gone, so the real period may be shorter than the window - say so in the report.

2. **Extra context** (cheap, no deep reading):
   - `ls ~/.claude/skills | wc -l` and compare with skills actually called in the stats - find "dead" skills. Note that skills run by scheduled jobs or invoked through natural language may be undercounted.
   - Scheduled jobs: `ls ~/Library/LaunchAgents` on macOS (or `crontab -l`, systemd timers) - count them, spot jobs that run Claude unattended.
   - `du -sh ~/.claude/projects` - size of session logs.
   - Your memory index (`MEMORY.md` or similar), if you keep one - which automations already exist.

3. **Interpret** (you, not the script). Derive from the JSON:
   - **Usage profile:** volume, rhythm (hours / weekdays), median session length, language, share of unattended sessions (first prompts that look scripted, e.g. "You are running a daily task..."), share with subagents.
   - **Task types:** cluster the first prompts by hand (scheduled jobs, infrastructure/skills, content, coding, knowledge base, one-off questions...) into a percentage bar chart. Mark it as approximate.
   - **Agent tools:** top tool calls with human labels (Bash = terminal, Agent = subagents...) and what dominates and why.
   - **Skills:** top used vs installed; dead skills; skills that repeated ad-hoc prompts ask for.
   - **Token analytics** (`tokens`): total output / new input (input + cache write) / cache read / thinking tokens, cache hit rate, tokens per week (trend), main vs subagent share (subagent logs live in `<session>/subagents/*.jsonl` and are included), 5-10 heaviest sessions with what they were about. Counts are unique API messages (the log repeats a message once per content block - the script already dedupes). Output tokens are the cost driver, cache reads are cheap - don't add them up as one number. Don't invent prices; if the user wants money, ask for their plan or current price list.
   - **Model usage** (`tokens.by_model`): requests and output tokens per model and share of each; which cheap-model work (small models are often used by subagents) vs big-model work; whether routine tasks could move to a smaller model.
   - **Effort usage** (`tokens.by_effort`, `model_x_effort_requests`, `effort_commands`): share of requests per effort level (low / medium / high / xhigh; requests without the field = models without effort, e.g. small ones, or older logs), model x effort matrix, how often `/effort` was changed, output tokens per request at each level. Flag mismatches: high effort on trivial work, medium on hard work, an effort changed once and forgotten.
   - **Month dynamics:** sessions per week (aggregate `activity_by_day`), trend and what drives it.
   - **Automation in numbers:** number of scheduled jobs, unattended sessions and their time, blind spots (no summary of results, no failure monitoring).
   - **System health:** size of `~/.claude/projects`, ballast skills, very long sessions (e.g. over 3 hours - context bloat), abandoned sessions (<1 min, one message), model mix (all on the biggest model? cheap model unused?).
   - **New skill candidates:** 3-4 ideas, each backed by "you already did this by hand on <date>".
   - **Your habits vs best practices:** two columns - observed pattern (no judgement) and a practice that strengthens it. No generic advice.
   - **Economy & efficiency** (`efficiency` + `tokens.requests_by_side_and_model`): a dedicated section with a table "goal / what to do / why (data)". Goals: save tokens and stretch plan limits, fewer mistakes, fewer interruptions, no dropped runs, better effort fit, smaller baseline context. Map signals to concrete fixes:
     - avg `context_per_request` high, many `compactions`, `sessions_over_24h` -> one task per session, `/clear` after finishing, a short worklog to resume from;
     - large share of subagent requests on the top model -> `CLAUDE_CODE_SUBAGENT_MODEL` env in settings.json, explicit `model: haiku` for search/sorting subagents, `claude -p --model ...` for scheduled jobs;
     - `oversized_tool_results_by_tool` (Read, screenshots) -> `offset/limit`, `grep`, page text instead of screenshots, downscale images;
     - `tool_errors_by_tool` / `tool_error_kinds` -> name the top error classes and the rule that prevents each (shell quirks in CLAUDE.md, API connectors instead of browser, a skill for repeated browser flows); note that `grep` with no match also exits 1;
     - `interrupts`, `user_rejections`, `turn_duration_min.over_10min` -> plan mode for big tasks, permission allowlist for safe commands;
     - `api_errors` / `rate_limit_errors` -> keep the machine awake during long runs, spread heavy work;
     - `short_abandoned_sessions` + number of installed skills/plugins/MCP servers -> trim the baseline loaded into every session (`/context`);
     - if the oldest log is ~30 days old, `cleanupPeriodDays` is at its default: say so and suggest raising it so history accumulates.
     Every row cites the number it rests on. No dollar estimates unless prices are verified.
   - **Recommendations (5-8):** concrete "do X", not "consider X".

4. **HTML report.** Start from `report-template.html` (same folder): one file, system font, thin lines, no shadows/gradients, one accent color via CSS variables, interactive charts (no libraries), Light / Auto / Dark switch in the top-right corner (Auto = `prefers-color-scheme`, manual choice saved in `localStorage`). Header must have two chips: generation date/time and data period (days, sessions). Sections: title -> big numbers -> activity bars -> tokens / models / effort -> top skills -> insights -> numbered recommendations.
   - **Interactive charts.** The template ships a tiny renderer (no libraries): write `<div class="chart" data-kind="..." data-items='JSON'></div>` and the script draws it. Kinds: `cols` (vertical columns - hours, weekdays, weeks, context buckets; `data-every="3"` thins x-labels, `data-partial="1"` hatches the last, incomplete period, `data-ramp="1"` steps opacity for ordered buckets), `stack` (horizontal two-series bars, e.g. main session vs subagents per model; `data-series='["a","b"]'`), `part` (one 100% bar, e.g. effort levels; each item `[label, value, shade 0-1]`, shade 0 = gray for "no data"), `hbar` (ranked horizontal bars, e.g. tool errors). Optional `data-unit`, `data-note`. Every mark has a hover tooltip; the spec is commented in the template.
   - Keep the validated palette from the template (`--c1` / `--c2` / `--gray`, separate light and dark values). If you change colors, re-validate them (light and dark) for colorblind separation and contrast; ordered data (effort, context size) = one hue in steps, never a rainbow.
   - Render and look before handing over, e.g. headless Chrome: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1000,6000 --screenshot=/tmp/report.png file://<report>` - check label collisions, overflow, dark theme.
   - Save to `~/.claude/skills/usage-insights/reports/YYYY-MM-DD-usage-report.html`, then open it (`open` on macOS, `xdg-open` on Linux, `start` on Windows).

## Rules

- Never read whole session transcripts - only the 200-character first prompts for clustering. Sessions may contain private data.
- Insights come from the data only; never invent numbers.
- Recommendations are concrete and actionable.
- Don't commit the `reports/` folder anywhere: it describes your private work.

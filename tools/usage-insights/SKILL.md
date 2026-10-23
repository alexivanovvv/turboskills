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
   - **Recommendations (5-8):** concrete "do X", not "consider X".

4. **HTML report.** Start from `report-template.html` (same folder): one file, system font, thin lines, no shadows/gradients, one accent color via CSS variables, pure-CSS bar charts, Light / Auto / Dark switch in the top-right corner (Auto = `prefers-color-scheme`, manual choice saved in `localStorage`). Header must have two chips: generation date/time and data period (days, sessions). Sections: title -> big numbers -> activity bars -> tokens / models / effort -> top skills -> insights -> numbered recommendations.
   - Save to `~/.claude/skills/usage-insights/reports/YYYY-MM-DD-usage-report.html`, then open it (`open` on macOS, `xdg-open` on Linux, `start` on Windows).

## Rules

- Never read whole session transcripts - only the 200-character first prompts for clustering. Sessions may contain private data.
- Insights come from the data only; never invent numbers.
- Recommendations are concrete and actionable.
- Don't commit the `reports/` folder anywhere: it describes your private work.

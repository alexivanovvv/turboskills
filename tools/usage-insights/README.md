# usage-insights

Find out how you really use Claude Code. Reads your local session logs and builds a minimal one-file HTML report: activity rhythm, task types, tools, token usage (output / cache / thinking, per model, week and effort level, main vs subagents), model mix, effort-level usage, an economy & efficiency section (context size per request, compactions, tool errors, interruptions, oversized tool output, subagent model mix -> concrete fixes to save tokens and plan limits), skills (including the ones you never use), scheduled automation, system health, new-skill candidates and 5-8 concrete recommendations. Charts are interactive (hover tooltips, light / dark, colorblind-checked palette) and need no libraries.

- Data stays local: `collect_stats.py` only reads `~/.claude/projects/*/*.jsonl` and prints counters plus the first 200 characters of each recent first prompt.
- Python 3 standard library only.
- Light / Auto / Dark theme, pure CSS charts, no external requests.

Install: `cp -r tools/usage-insights ~/.claude/skills/` then run `/usage-insights`.

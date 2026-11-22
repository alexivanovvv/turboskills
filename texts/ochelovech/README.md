# ochelovech

Humanize AI-sounding Russian and English text with targeted point edits: removes bureaucratese, ChatGPT clichés, empty lead-ins, "not just X, but Y", triads, extra dashes and bold, and chat paste junk — and leaves everything else word for word, so the author still recognizes their text. Numbers, names, dates, conditions and negations are kept and checked by scripts.

Fork of [Vladimir-Human/humanizer-ru](https://github.com/Vladimir-Human/humanizer-ru) (MIT) with English support (patterns from [blader/humanizer](https://github.com/blader/humanizer), MIT).

## Install

```bash
npx skills add alexivanovvv/turboskills -g --skill ochelovech
```

Or copy this folder into `~/.claude/skills/` (Claude Code) or `~/.agents/skills/` (Codex).

## Use

Paste text and say «очеловечь» / "humanize". Findings only: «проверь, что выдаёт ИИ, но не правь».

## Contents

- `SKILL.md` — agent instructions
- `references/` — before/after examples and pattern boundaries (RU + EN)
- `scripts/` — `clean_paste.py`, `apply_edits.py`, `edit_budget.py`, `check_facts.py` (Python standard library only)

Tests, the blind comparison stand and full history up to 5.1.0: [alexivanovvv/ochelovech](https://github.com/alexivanovvv/ochelovech) (frozen).

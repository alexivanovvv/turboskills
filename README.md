# turboskills

Skills to boost your authentic work with AI — beautifully and to the point.

A collection of [Claude Code](https://claude.ai/code) skills (slash commands) for coaches, educators, creators, and knowledge workers.

---

## What's a skill?

A skill is a folder you drop into `~/.claude/skills/`. Claude Code picks it up automatically and makes it available as a `/skill-name` command in any conversation.

Each skill contains:
- `SKILL.md` — instructions for the Claude agent
- supporting files (templates, scripts, configs)

---

## Skills

### create/

Skills for creating content and presentations.

| Skill | What it does |
|-------|-------------|
| [`slides-generator`](create/slides-generator/) | Turn a Markdown file into a self-contained HTML slide deck — dark minimal style, animated SVG art, 50 geometric motifs, keyboard nav, speaker notes, autoplay |

---

## Install any skill

```bash
# Install a single skill
cp -r create/slides-generator ~/.claude/skills/

# Or clone the whole repo and symlink
git clone https://github.com/alexivanovvv/turboskills ~/.claude/turboskills
ln -s ~/.claude/turboskills/create/slides-generator ~/.claude/skills/slides-generator
```

Then in Claude Code:

```
/slides-generator path/to/content.md
```

---

## Contributing

PRs welcome. Each skill should be:
- Self-contained (one folder, no external dependencies to install at runtime)
- Generic enough to work for any user, not just the author
- Documented with a `README.md` inside the skill folder

---

Made by [@alexivanovvv](https://github.com/alexivanovvv) · [@ppprompt](https://t.me/ppprompt)

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

### story/

Skills for writing authentic personal stories — from deep transformation narratives to social media posts.

| Skill | What it does |
|-------|-------------|
| [`story-heros-journey`](story/story-heros-journey/) | Write a personal transformation story using the Hero's Journey arc (6 stages from ordinary world to return with the gift). For case studies, longreads, deep reflections. |
| [`story-preodolenie`](story/story-preodolenie/) | Write a story of overcoming challenges — 5 flexible elements (Point A → Obstacles → Motivation → Resources → Point B) with 4 composition patterns. For blogs, portfolios, pitches. |
| [`story-authentic-social`](story/story-authentic-social/) | Write an authentic story for social media and marketing — 6-step hook structure (Hook → Why → Trust → Story → Result → Hook back). For posts, reels, stories, videos. |

---

## Install any skill

```bash
# Install a single skill
cp -r create/slides-generator ~/.claude/skills/
cp -r story/story-heros-journey ~/.claude/skills/
cp -r story/story-preodolenie ~/.claude/skills/
cp -r story/story-authentic-social ~/.claude/skills/

# Or clone the whole repo and symlink skills
git clone https://github.com/alexivanovvv/turboskills ~/.claude/turboskills
ln -s ~/.claude/turboskills/create/slides-generator ~/.claude/skills/slides-generator
ln -s ~/.claude/turboskills/story/story-heros-journey ~/.claude/skills/story-heros-journey
ln -s ~/.claude/turboskills/story/story-preodolenie ~/.claude/skills/story-preodolenie
ln -s ~/.claude/turboskills/story/story-authentic-social ~/.claude/skills/story-authentic-social
```

Then in Claude Code:

```
/slides-generator path/to/content.md
/story-heros-journey
/story-preodolenie
/story-authentic-social
```

---

## Contributing

PRs welcome. Each skill should be:
- Self-contained (one folder, no external dependencies to install at runtime)
- Generic enough to work for any user, not just the author
- Documented with a `README.md` inside the skill folder

---

Made by [@alexivanovvv](https://github.com/alexivanovvv) · [@ppprompt](https://t.me/ppprompt)

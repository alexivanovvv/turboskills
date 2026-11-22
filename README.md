# turboskills

**English** · [Русский](README.ru.md)

Skills to boost your authentic work with AI — beautifully and to the point.

A collection of [Agent Skills](https://agentskills.io) for coaches, educators, creators and knowledge workers. They work in Claude Code, Codex, Cursor and any other agent that supports the `SKILL.md` format. Most skills answer in Russian by default.

## What's a skill?

A skill is a folder with a `SKILL.md` file (instructions for the agent) and optional supporting files: references, scripts, templates. The agent reads the skill's short description and loads the full instructions only when your request matches it.

## Skills

### texts/ — editing your texts

| Skill | What it does |
|-------|-------------|
| [`sokrati`](texts/sokrati/) | Shorten or tighten your text without losing your voice: cut to a target size ("-30%", "2x shorter") or just remove filler, using the "Write, cut" editing method. Keeps versions v0.1/v0.2… in the same file with a one-line changelog. Personal settings (voice file, typography, where to open the result) go into a local `LOCAL.md`, which is not committed. |
| [`ochelovech`](texts/ochelovech/) | Humanize AI-sounding Russian and English text with targeted point edits: removes bureaucratese, ChatGPT clichés, paste junk, extra dashes and bold, keeps the rest word for word, then checks that numbers, names, dates and negations survived. Fork of [Vladimir-Human/humanizer-ru](https://github.com/Vladimir-Human/humanizer-ru) (MIT); tests and the comparison stand live in the frozen [ochelovech](https://github.com/alexivanovvv/ochelovech) repo. |

### slides/ — presentations

| Skill | What it does |
|-------|-------------|
| [`slides-generator`](slides/slides-generator/) | Turn a Markdown file into a self-contained HTML slide deck: dark minimal style, animated SVG art on every slide (134 motifs + 25 icons), 6 themes, presenter view, keyboard navigation, speaker notes, autoplay, settings page. |

### story/ — personal stories

| Skill | What it does |
|-------|-------------|
| [`story-heros-journey`](story/story-heros-journey/) | A personal transformation story along the Hero's Journey arc (6 stages from the ordinary world to the return with the gift). For case studies, longreads, deep reflections. |
| [`story-preodolenie`](story/story-preodolenie/) | A story of overcoming: 5 flexible elements (Point A → Obstacles → Motivation → Resources → Point B) and 4 composition patterns. For blogs, portfolios, pitches. |
| [`story-authentic-social`](story/story-authentic-social/) | An authentic story for social media and marketing with a 6-step hook structure (Hook → Why → Trust → Story → Result → Hook back). For posts, reels, stories, videos. |

### marketing/ — selling courses and services

| Skill | What it does |
|-------|-------------|
| [`marketing-ladder`](marketing/marketing-ladder/) | Ben Hunt's Ladder of Awareness for a course or service (rungs 0-5 + after purchase): diagnoses where your audience is, audits existing marketing, builds messages, offers and CTAs per rung, writes the texts, plans a launch with dates and transition metrics. |
| [`marketing-cialdini`](marketing/marketing-cialdini/) | Audit, create or strengthen a landing page, post, email, webinar or sales DM with Robert Cialdini's 7 principles of influence: 0-3 profile per principle, red flags for fake or broken levers, prioritized before/after rewrites. Honest levers only. |

### tools/ — everyday utilities

| Skill | What it does |
|-------|-------------|
| [`disk-space-analyzer`](tools/disk-space-analyzer/) | Find what's eating your disk and clean it safely: disk map and bar charts right in the terminal, a ranked cleanup plan with safety levels, before → after result. macOS and Windows. Based on [WhiteMinds/disk-space-analyzer-skill](https://github.com/WhiteMinds/disk-space-analyzer-skill) (MIT). |
| [`usage-insights`](tools/usage-insights/) | See how you really use Claude Code: reads your local session logs and builds a one-file HTML report — rhythm, task types, tools, unused skills, automation, system health, recommendations. Data stays on your machine. Claude Code only. |

## Install

**Any agent** (Claude Code, Codex, Cursor and others) via [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add alexivanovvv/turboskills -g                 # pick skills interactively
npx skills add alexivanovvv/turboskills -g --skill sokrati # one skill
```

**Manually** — copy a skill folder into your agent's skills folder:

```bash
git clone https://github.com/alexivanovvv/turboskills ~/turboskills

# Claude Code
cp -r ~/turboskills/texts/sokrati ~/.claude/skills/

# Codex
cp -r ~/turboskills/texts/sokrati ~/.agents/skills/
```

Want updates with `git pull`? Use a symlink instead of a copy:

```bash
ln -s ~/turboskills/texts/sokrati ~/.claude/skills/sokrati
```

## Use

Just ask in your own words — the agent picks the right skill from its description. Or call it directly:

- Claude Code: `/sokrati`, `/slides-generator path/to/content.md`, `/marketing-cialdini audit ./landing/index.html`
- Codex: `$sokrati`, `$slides-generator path/to/content.md`

## Contributing

PRs welcome. Each skill should be:

- one folder with a `SKILL.md` (`name` matches the folder, `description` up to 1024 characters with trigger phrases);
- self-contained: scripts use paths relative to the skill folder, no runtime installs;
- generic: works for any user, personal settings go into an ignored `LOCAL.md`;
- optionally: `README.md` for people and `agents/openai.yaml` for the Codex UI.

## License

[MIT](LICENSE). Skills based on other projects keep their original licenses inside their folders.

Made by [@alexivanovvv](https://github.com/alexivanovvv) · [@ppprompt](https://t.me/ppprompt)

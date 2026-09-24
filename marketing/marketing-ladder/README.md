# marketing-ladder – Claude Code skill

A [Claude Code](https://claude.ai/code) skill that analyzes a course, coaching program or any service through **Ben Hunt's Ladder of Awareness** and builds the path from "I don't have a problem" to purchase, repeat sale and referral.

The skill works in **Russian** by default and answers in the user's language.

---

## What it does

- **Diagnoses** where your audience is on the ladder (by channel and segment), how saturated your market is, and where people drop off
- **Builds the ladder** for your product: for every rung (0-5 by Hunt + 6 "after purchase"), it covers the inner monologue, the message, formats, proof, the offer and a CTA to the next rung, plus the signal that someone moved up and the metric to watch
- **Writes the texts**: hooks, ready-to-publish drafts and bridges between rungs. It doesn't depend on any other skill
- **Audits existing marketing**: it maps your posts, landing page and emails to rungs, finds empty rungs, message/audience mismatches and broken CTAs, then rewrites the weak spots
- **Plans a launch or evergreen sales**: a week-by-week calendar with real dates, honest deadlines, a content mix per rung, and transition metrics
- **Never invents facts**: missing prices, cases and testimonials become `[placeholders]` and a list of questions

## Modes

| Mode | When |
|---|---|
| `auto` (default) | The skill picks the mode from your request and materials |
| `build` | You have a product and no marketing yet |
| `audit` | You have a landing page, posts, a funnel or metrics |
| `rung N` | You need depth on one rung, e.g. "what to say to a cold audience" |
| `quick` | You want a one-screen map, with no drafts and no file |

## Output

- The **chat** gets a short version: the diagnosis, a ladder table and your top 3 actions
- The **file** gets the full document. It is saved only when the workspace has a sensible place for it: a path you name, the product's own folder, an existing marketing folder, or the root of a project/notes workspace. It follows the workspace's naming rules (`AGENTS.md` / `CLAUDE.md`) when there are any. If there's no good place, the full document goes to chat instead

---

## Install

```bash
cp -r marketing-ladder ~/.claude/skills/
```

No dependencies.

## Usage

```
/marketing-ladder my 6-week course for managers on burnout, 40k RUB, launching March 1
/marketing-ladder audit <paste landing text or give a file path>
/marketing-ladder rung 0 what should I post for people who don't think they have a problem
```

Or just ask in plain words: "разбери мой курс по лестнице Ханта", "построй шаги запуска", "почему не покупают".

---

## Structure

```
marketing-ladder/
├── SKILL.md                     # process, modes, rules, output format
├── README.md
├── agents/openai.yaml           # metadata for Codex / other agents
└── references/
    ├── ladder.md                # the model: origin, rules, deep playbook per rung
    ├── diagnostics.md           # finding the audience's rung, audit checklist, gaps, metrics
    ├── product-types.md         # 1:1, cohort course, B2B, evergreen, community
    ├── launch-plan.md           # launch and evergreen timelines, calendar template
    ├── copy-bank.md             # hooks, text skeletons, CTAs, bridges, anti-clichés
    └── output-template.md       # full document template
```

## Sources

- Ben Hunt, *Convert!: Designing Web Sites to Increase Traffic and Conversion*, Wiley, 2011
- Eugene Schwartz, *Breakthrough Advertising*, 1966 (levels of awareness, market sophistication)

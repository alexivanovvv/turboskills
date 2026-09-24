# marketing-cialdini – Claude Code skill

A [Claude Code](https://claude.ai/code) skill that audits, writes and strengthens marketing for a course, coaching, consulting or any service using **Robert Cialdini's 7 principles of influence**: reciprocity, commitment & consistency, social proof, authority, liking, scarcity and unity.

The skill works in **Russian** by default and answers in the user's language.

---

## What it does

- **Audits** a landing page, post, email, webinar script or sales DM. Each principle gets a 0-3 score, and the result is a 7-score profile rather than a single average. The audit checks where each principle sits on the reader's path, flags manipulative or broken levers, and lists prioritized fixes with before/after rewrites
- **Creates** copy from scratch in which every block carries a principle at the right point, plus 2-3 first-screen variants built on different principles
- **Enhances** existing copy by weaving in the 3-5 missing principles with the highest impact while keeping the author's voice and structure
- **Works with or without context.** It can start from a file, URL, project folder or pasted text, or from a one-line product description
- **Honest levers only**: no fake scarcity, no invented testimonials. Missing facts become `[placeholders]` plus a "what to collect" list
- **Self-contained.** It doesn't depend on any other skill

## Modes

| Mode | When |
|---|---|
| `auto` (default) | The skill picks the mode from your request and materials |
| `audit` | You have copy and want to know why it doesn't convert |
| `create` | You need a new landing page, post, email chain, webinar script or offer |
| `enhance` | You have copy and want the missing principles added without a rewrite |
| `quick` | You want a one-screen profile and top fixes, with no file |

You can also focus on one principle: `/marketing-cialdini audit social proof ...`

## Output

- The **chat** gets a short version: the 7-principle profile, red flags and your top 3 fixes
- The **file** gets the full document: fact bank, profile, red flags, block-by-block breakdown, fixes, text and a "what to collect" list. It is saved next to the audited material or in the project's marketing folder, and only when the workspace has a sensible place for it. Otherwise the full document goes to chat
- The source material is **never edited** unless you ask

---

## Install

```bash
cp -r marketing-cialdini ~/.claude/skills/
```

No dependencies.

## Usage

```
/marketing-cialdini audit ./landing/index.html
/marketing-cialdini create sales email for my 6-week burnout course for managers, starts Jan 15
/marketing-cialdini enhance <paste your post>
/marketing-cialdini quick https://example.com
```

Or just ask in plain words: "проверь лендинг по Чалдини", "добавь социальное доказательство", "почему текст не продает".

---

## Structure

```
marketing-cialdini/
├── SKILL.md                     # process, modes, rules, output format
├── README.md
├── agents/openai.yaml           # metadata for Codex / other agents
└── references/
    ├── principles.md            # the 7 principles: research, what amplifies them, how to apply, red flags
    ├── audit.md                 # procedure, 0-3 scale, checklists, red flags, prioritization, reader path
    ├── assets.md                # principles by asset (landing, post, email, webinar, DM, checkout, onboarding) and product type
    ├── copy-bank.md             # formulas and examples per principle, first-screen variants, anti-clichés
    └── output-template.md       # full document template
```

## Sources

- Robert B. Cialdini, *Influence: The Psychology of Persuasion*, 1984; *Influence, New and Expanded*, 2021
- Robert B. Cialdini, *Pre-Suasion*, 2016
- Goldstein, Martin, Cialdini, *Yes! 50 Scientifically Proven Ways to Be Persuasive*, 2008

# slides-generator — Claude Code skill

A [Claude Code](https://claude.ai/code) skill that turns a Markdown file into a self-contained, single-file HTML slide deck.

**Dark minimal style** · animated SVG art · 50 geometric motifs · keyboard navigation · speaker notes · autoplay

![Slide example](https://i.imgur.com/placeholder.png)

---

## What it does

- Reads a `.md` file with session content
- Assigns a layout and animated SVG illustration to every slide based on meaning
- Outputs one `.html` file — no build step, no dependencies, open in any browser
- Also saves a clean `.md` copy of the slides and updates a `slides-index.html` navigator

---

## Install

Copy the skill folder into your Claude Code skills directory:

```bash
cp -r slides-generator ~/.claude/skills/
```

Or clone just this folder:

```bash
git clone https://github.com/your-username/slides-generator ~/.claude/skills/slides-generator
```

No `npm install`, no Python packages. Works offline (fonts load from Google Fonts — include fallbacks for offline use).

---

## Usage

In any Claude Code conversation:

```
/slides-generator path/to/content.md
/slides-generator path/to/content.md --ratio 16:9
```

The skill generates slides alongside your source file:

```
2024-06-11 - Slides My Session/
  My Session — Slides Content.html   ← open this in a browser
  My Session — Slides Content.md     ← clean markdown copy
```

---

## Content format

A flat Markdown file, one section per slide. Use `---` to separate slides:

```markdown
# Session Title
Brand Name · Date · Author

---

## Slide Title

- Bullet point one
- Bullet point two with **bold**

---

## Another Slide

- Item
```

The skill infers layout from content: text-heavy → left/right 50/50; grids/steps → full-width with numcards; dividers → section headers. See `SKILL.md` for the full component library.

---

## Navigation (keyboard)

| Key | Action |
|-----|--------|
| `→` / `Space` | Next slide |
| `←` | Previous slide |
| `N` | Toggle speaker notes |
| `F` | Fullscreen |
| `AUTOPLAY ›` button | Auto-advance every 20 s |
| `FAST PLAY ››` button | Auto-advance every 7 s |

---

## Customising the template

`template.html` is the single source of truth. It contains:

- CSS custom properties (`:root`) for colors, fonts, spacing
- 50 `<symbol>` SVG motifs — add your own in the same `420×560` canvas style
- JS for navigation, autoplay, speaker notes, fullscreen

**Color palette** — 6 accent variables, all configurable:
```css
--green: #4ade80   /* primary accent */
--amber: #fbbf24   /* secondary accent */
--blue:  #38bdf8
--violet:#c084fc
--pink:  #f472b6
--orange:#fb923c
```

**Fonts** — three Google Fonts families with full Cyrillic support:
- `Unbounded` — display headings (h1, section titles)
- `Manrope` — subheadings (h2, kickers)
- `Golos Text` — body text

Change the `@import` line and `:root` font variables to use different fonts.

---

## Components

Full reference in `SKILL.md`. Quick overview:

| Component | Use |
|-----------|-----|
| `h2 + ul` | Standard bullet slide (50/50 with art) |
| `.slide.wide` | Full-width slide, no art |
| `.pgrid.row4` | 4-column numcard grid |
| `.cards.g5` | 5-column numcard row |
| `.hexring` | 6 items on a ring with animated center |
| `.arc` | Two-column comparison (Bad/Good) |
| `.bq` | Block quote — italic Lora + left border |
| `.sec-title` | Section divider slide |
| `.qa-big` | Q&A closing slide |

---

## Files

| File | Purpose |
|------|---------|
| `template.html` | CSS + JS + SVG library + `<!-- SLIDES_PLACEHOLDER -->` |
| `SKILL.md` | Instructions for the Claude agent |
| `VISUALIZATIONS.md` | SVG motif catalogue — which motif fits which meaning |
| `ROADMAP.md` | Ideas for future improvements |

---

## License

MIT

# English text: markers, examples and limits

Numbers match the table in SKILL.md: the signs are the same, the English markers differ.
Examples show the move, not wording to copy. The rules from SKILL.md hold for English too:
edit, don't rewrite; keep every fact, hedge and negation; add nothing.

Markers and several examples are adapted from [blader/humanizer](https://github.com/blader/humanizer)
(MIT, Siqi Chen), which is based on Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).

## Paste debris (step 1)

Delete silently: «Certainly! Here's…», «Sure! Here is a…», «Great question!», «You're absolutely
right!», «I hope this helps», «Let me know if you'd like me to expand», «Would you like…»,
«Want me to…?», «Should I continue?».

## 1. Empty lead-ins

Markers: «It is important to note that», «It's worth mentioning», «In today's fast-paced world»,
«Let's dive in», «Let's break this down», «Here's what you need to know», «Without further ado»,
«The real question is», «At its core», «What really matters is», «Fundamentally».

Before: «It is important to note that the data shows a decline.»
After: «The data shows a decline.»

Before: «Let's dive into how caching works in Next.js. Here's what you need to know.»
After: cut both sentences and start with the first real claim from the source.

Limit: a warning before a risky step («Important: back up the database first») carries meaning.

## 2. False contrast

Markers: «It's not just X, it's Y», «Not only… but also», «It's not merely a song, it's a statement»,
clipped tailing negations: «…, no guessing», «…, no wasted motion».

Before: «It's not merely a dashboard, it's a compass for decisions.»
After: «The dashboard shows the main metrics in one place.» (or the metrics, if the source names them)

Before: «The options come from the selected item, no guessing.»
After: «The options come from the selected item, so the user doesn't have to guess.»

Limit: a real distinction that fixes a reader's error: «We're disabling the export, not the whole API».

## 3. Inflated significance

Markers: «plays a pivotal / crucial / key / vital role», «a testament to», «stands as a reminder»,
«marks a turning point», «sets the stage for», «evolving landscape», «indelible mark»,
«deeply rooted», «game-changer», «takes X to the next level». Notability puffing: «featured in
leading media outlets», «an active social media presence».

Before: «The institute was established in 1989, marking a pivotal moment in the evolution of regional statistics.»
After: «The institute was established in 1989.»

## 4. Bureaucratese and copula avoidance

Markers: «serves as», «stands as», «functions as», «boasts», «features» (for «has»), «in order to»,
«due to the fact that», «at this point in time», «in the event that», «has the ability to»,
«utilize», «facilitate», «leverage».

Before: «Gallery 825 serves as the exhibition space. The gallery boasts over 3,000 square feet.»
After: «Gallery 825 is the exhibition space. The gallery has over 3,000 square feet.»

Before: «The system has the ability to process requests in order to reduce delays.»
After: «The system can process requests to reduce delays.»

Limit: «leverage» in finance, «utilize» in a quoted spec. Don't change risk into fact: «may
reduce» stays «may reduce».

## 5. Loanword calques

In English this is the AI vocabulary, see E4 below.

## 6. Significance tails (-ing clauses)

Markers: «…, highlighting / underscoring / emphasizing…», «…, reflecting…», «…, symbolizing…»,
«…, ensuring…», «…, fostering…», «…, showcasing…», «…, contributing to…».

Before: «The temple is painted blue, green and gold, symbolizing the bluebonnets and the Gulf, reflecting the community's deep connection to the land.»
After: «The temple is painted blue, green and gold, colors meant to evoke the bluebonnets and the Gulf.»
(keep the tail's fact; drop the tail's significance)

## 7. Anonymous authorities

Markers: «Experts argue», «Studies show», «Industry reports suggest», «Observers have noted»,
«Many believe», «several sources» (when one is cited).

Before: «Experts believe it plays a crucial role in the regional ecosystem.»
After: name the source if the text has one; otherwise «It may matter for the regional ecosystem.»
or cut. Never invent a source.

## 8. Rule of three

Before: «Attendees can expect innovation, inspiration, and industry insights.»
After: keep only what the source backs: «There will be talks and panels.»

Limit: a list of real names, tools, steps or prohibitions is data, not a triad.

## 9. Moral endings and aphorisms

Markers: «In conclusion», «Ultimately», «At the end of the day», «The future looks bright»,
«Exciting times lie ahead», «This represents a major step in the right direction»,
aphorism formulas: «X is the language of Y», «X becomes a trap», «X is not a tool but a mirror»,
«the currency of», «the architecture of».

Before: «Symmetry is the language of trust.»
After: «Symmetric layouts feel more predictable to users.» (if the text says so)

End on the last fact, action or contact. Real plans from the source stay.

## 10. Staged questions

Markers: «Why does this matter? Because…», «The result? …», «The secret? …», «Honestly? …»,
«Look, …», «Here's the thing: …», «Real talk:».

Before: «Is it worth the price? Honestly? It depends on how often you'll use it.»
After: «Whether it's worth the price depends on how often you'll use it.»

Limit: «honestly» or «look» mid-sentence is ordinary speech; the tell is the standalone opener.

## 11. Metatext

Markers: «In this article, we will explore», «As mentioned above», «In other words» followed by a
restatement, «Now let's look at».

## 12. Empty generalizations and false ranges

Markers: «various aspects», «a range of benefits», «from startups to enterprises»,
«from the Big Bang to the cosmic web», «Despite these challenges, X continues to thrive»,
formulaic «Challenges and future prospects» sections.

Before: «Despite these challenges, Korattur continues to thrive as an integral part of Chennai's growth.»
After: keep the challenges the source names («It has recurring traffic congestion and water shortages.») and cut the send-off.

## 13. Connectives everywhere

Markers: «Additionally», «Moreover», «Furthermore», «Notably», «It's also worth noting» at the
start of paragraphs. One «however» is fine.

## 14. Metronome rhythm and staccato

Even mid-length sentences; runs of clipped fragments for drama: «It had no preference for symmetry.
No aesthetic prior. No nostalgia. The old rules were gone.»; subjectless fragments: «No config
file needed.»

Fix: vary length; merge a run of fragments into one sentence with the facts. One short emphatic
sentence is fine.

## 15. Template formatting

Bold in every line, inline-header lists («**Performance:** Performance has been improved…»),
emoji bullets (🚀 💡 ✅), a heading followed by a line that restates it («## Performance /
Speed matters.»).

Keep a list when items are steps, comparisons or separate facts; drop the bold labels and the
restating line.

## 16. Dashes

In English the em dash (—, also « -- ») is one of the strongest tells. By default replace almost
all: a period, comma, colon or parentheses, by meaning. En dash in ranges («2019–2024», «pages
10–12») stays. If the author's sample uses em dashes, keep them at the sample's rate.

Before: «The new policy — announced without warning — affects thousands of workers.»
After: «The new policy, announced without warning, affects thousands of workers.»

## 17. Stacked hedges

Before: «It could potentially possibly be argued that the policy might have some effect.»
After: «The policy may have some effect.»
One hedge stays: «may» must not become «will».

## 18. Promotional tone

Markers: «nestled in the heart of», «breathtaking», «stunning», «vibrant», «rich cultural
heritage», «boasts», «must-visit», «renowned», «groundbreaking», «we're thrilled to announce»,
«we're proud to present».

Before: «Nestled within the breathtaking region of Gonder, Alamata is a vibrant town with a rich cultural heritage.»
After: «Alamata is a town in the Gonder region.»

## 19. Template politeness and servility

Markers: «Thank you for your patience», «We appreciate your understanding», «Great question!»,
«That's an excellent point».

## 20-22. Traces of humanizing itself

Invented specifics («in 80% of cases», «within a month»), invented experience («I've tried»,
«when I was starting out»), forced liveliness (inserted «honestly», «basically», jokes,
«No fluff. No magic.»). Don't add them.

## 23. Writing from the diff

Before (in docs, not a changelog): «This function was added to replace the previous approach of iterating through all items.»
After: «This function uses a hash map for lookups instead of iterating through all items.»

## 24. Filler instead of knowledge

Markers: «As of my last training update», «While specific details are limited…», «based on
available information», «maintains a low profile», «keeps personal details private», «likely
grew up…», «it is believed that».

Before: «Information about her early life is not publicly available, suggesting she keeps personal details private.»
After: «Her early life is not documented in the available sources.» (or cut)

## English-only

**E1. Title Case in headings.** «## Strategic Negotiations And Global Partnerships» →
«## Strategic negotiations and global partnerships». Leave it if the publication's style
(or the rest of the author's text) uses Title Case.

**E2. Hyphenated pairs in predicate position.** Keep attributive hyphens («a high-quality report»),
drop them after the noun («the report is high quality»). Applies to: high-quality, data-driven,
cross-functional, real-time, long-term, end-to-end, decision-making.

**E3. Curly quotes.** “…” in a plain-text or Markdown context where the rest uses "…" → straight
quotes. Not a tell on its own: macOS, Word and most CMSes curl quotes automatically.

**E4. AI vocabulary.** Words that pile up in post-2023 text: delve, tapestry, testament, intricate,
interplay, landscape (abstract), pivotal, crucial, key (adj.), vibrant, showcase, underscore,
highlight (verb), foster, garner, enhance, align with, enduring, seamless, robust, leverage,
navigate (abstract), realm, embark, unlock, elevate. One word is nothing; three in a paragraph
is a cluster. Replace with the plain word the sentence means, or cut the clause.

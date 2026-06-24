# Hero prompt

This repo uses a hand-authored SVG hero at `assets/jsonl-vault-spike-hero.svg`, but the concept follows the `viggomeesters-asset-prompt` repo-hero pattern so it can be regenerated or redesigned consistently later.

## Final prompt

```text
Create a wide GitHub README hero illustration in the visual style of viggomeesters.com and the Reisplanner Agent README hero.

Project name: JSONL Vault Spike
Purpose: a synthetic proof of concept for turning Markdown-style vault knowledge into agent-readable JSONL records, bounded context bundles, and generated views.

Visual concept:
a dark editorial tech pipeline where synthetic raw evidence flows into typed JSONL record cards, then into a bounded agent context bundle and AI-ready output. Use floating cards/icons that represent:
- raw JSONL evidence
- typed records: claims, entities, tasks
- bounded context bundles
- generated SQLite / Markdown views
- public-safe synthetic data

Style:
modern editorial tech illustration, playful but professional, dark navy/black background, subtle glow, crisp vector-like shapes, rounded cards, clean iconography, vibrant teal, sky blue, purple, warm yellow, and coral accents. High contrast, polished GitHub README hero aesthetic, friendly and useful, not childish.

Composition:
main visual pipeline across the center, calm dark background, large readable labels if text is used, enough spacing for GitHub README width, no clutter. Dotted connection lines or flow arrows may connect the cards, but decorative lines must never cross visible text.

Constraints:
no logos, no watermark, no real people, no brand names, no UI screenshots, no private vault data, no real names, no real emails, no real filesystem paths. If text is included, only use exact short labels such as “RAW JSONL”, “TYPED RECORDS”, “BUNDLES”, and “AI”.

Aspect ratio: README-wide, around 1000×360 or 16:9.

Make it feel like part of the same visual family as viggomeesters.com project cards and the Reisplanner Agent README hero. Cohesive personal technical portfolio style. Clean, polished, source-backed systems builder aesthetic.
```

## Current asset notes

- Current implementation is SVG, not generated raster art.
- The SVG keeps labels short and readable at README width.
- Public-data boundary: no real personal data, no screenshots, no private paths.

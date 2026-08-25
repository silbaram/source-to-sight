```skill
---
name: 101-teacher
description: Explain a topic for a complete beginner as a source-grounded, self-contained HTML page that teaches through diagrams first and plain language second. Use when the user says /101-teacher, asks to "explain like I'm 5," or wants a dead-simple visual explainer. Do not use for ordinary prose documentation that does not need a visual teaching artifact.
metadata:
  short-description: Beginner-first visual explainer as offline HTML
---

# 101-teacher

Create one self-contained HTML page that lets a complete beginner answer, within a few seconds:

1. What is this?
2. Who or what is involved?
3. What happens, in what order?
4. What should I remember or avoid?

The reader should be able to answer 1–4 from the diagrams and their labels, without depending on long prose. Prose confirms and refines what the pictures already showed.

The page should feel simple because its information is organized, not because facts were removed or the type was made enormous.

## Deliverable

Write one `.html` file to disk and report its path. Use the location the user named; otherwise place it next to the material it explains or in the working directory.

The file must open directly in a browser with no network, build step, or hosted-artifact service.

## Establish the truth first

For code, documentation, or a repository system, read the actual sources before designing. Pull real identifiers, fields, codes, limits, sequence, and exceptions. Do not fill gaps with plausible examples.

When documentation and code disagree:

- explain the behavior the code currently implements;
- call out the disagreement where it matters;
- distinguish verified behavior from an inference or an external dependency.

Record the quantities you encounter—byte lengths, offsets, timeouts, limits, counts, retry numbers, percentages, and sizes—then identify where relative magnitude changes a beginner's understanding or decisions. Encode those relationships through visible size, length, or position. Exact-only values may remain labels or tables, and incidental numbers need not become diagrams.

If the user gives a reference HTML or visual, inspect both its source and rendered result when possible. Reuse its effective hierarchy, density, navigation, and typography rather than its incidental decoration.

## Beginner-first structure

Use progressive disclosure. A useful default order is:

1. **Direct answer** — one plain sentence saying what the thing does.
2. **Cast** — the people, systems, or objects and one job for each.
3. **Big flow** — the real ordered path as the main visual.
4. **Inputs and outputs** — familiar names first, real identifiers beside them.
5. **Details** — complete tables, protocol layouts, code, or edge cases.
6. **Things that go wrong** — a small set of concrete traps or errors.
7. **Sources and unknowns** — what was read and what was not verified.

Adjust the order when the subject has a better teaching sequence. Keep complete reference material in tables or behind `<details>` so it does not compete with the first explanation. Headings alone should form a useful page summary.

Core explanatory sections should normally lead with a visual before their first reference table, code block, or `<details>`. Reference-only sections such as sources, unknowns, appendices, and raw field catalogs are exempt. A table may lead when comparison itself is the lesson. Do not invent a diagram merely to satisfy section structure.

Make a useful diagram visible in the first screen near `1440 × 900`. A moderate system usually benefits from several distinct diagrams, but use only diagrams that teach a real relationship.

## Plain language

- State the literal truth before using a metaphor. Use a metaphor only when it removes a real conceptual obstacle, map it once to the real term, then return to the real term.
- Introduce jargon before relying on it. Use the newcomer's name first and the real identifier beside it once.
- Prefer active voice, short sentences, and concrete verbs.
- Keep running prose near 65 characters wide. Use no more than one or two short paragraphs per section unless the user needs a prose-heavy explanation.
- Keep captions to about two lines and explain what the picture means rather than repeating its labels.

## Visual contract

The picture must encode the relationship it teaches:

- **Magnitude → size or position.** Important unequal quantities should not become equal boxes with numbers printed inside.
- **Order → a shared path.** Steps should expose direction and sequence; the path may be horizontal, vertical, or use lanes when that better fits the content.
- **Sameness and difference → consistent shape and color.** Give each accent a semantic job and do not rely on color alone.
- **Repeated concepts → repeated geometry.** Reuse a visual model when it helps the reader transfer understanding, not when the later concept needs a different structure.

When the page needs a specialized pattern or an existing visual is dense, unclear, or colliding, read [diagram patterns](references/diagram-patterns.md) before drawing. Ordinary simple diagrams may use this visual contract directly.

Hard drawing requirements:

- Build diagrams with inline SVG or CSS. Do not use Mermaid, D3, a CDN, or external images.
- Keep essential labels horizontal and readable.
- In a connected flow, keep the arrowhead visibly separate from the final marker. Measure rendered edges including strokes, not transparent marker padding. At the intended size, leave at least the larger of 12 CSS pixels or three times the thicker stroke.
- Do not let same-colored shapes touch unless the contact encodes a real connection.
- For thin proportional fields, prefer a separate ordered legend, index, or enlarged detail. Use leader lines only when there is enough space to keep every line and label visibly separate and the target render can be inspected.
- Avoid forcing the main explanation through horizontal scrolling. If a genuinely wide technical diagram must scroll, add a readable narrow-screen summary or stacked representation.
- Give each diagram `role="img"` with a useful `aria-label`, or SVG `<title>` and `<desc>` that state what it shows.

## Design and build

Sketch a compact plan before markup: the job of each semantic color, the reading width and navigation behavior, desktop/mobile diagram behavior, and the relationship each planned visual encodes. If an entry is only “cards” or “list,” decide whether it is supporting content or find the real relationship.

Use a small semantic palette with deliberate neutrals and accents. Prefer documentation-scale type: body text normally at least `16px`, restrained display type, and a mono stack for identifiers. Treat these as defaults and follow an existing design system when the user supplied one.

Keep the page self-contained. Use inline CSS, scripts, SVG, fonts, and bitmap data; make no external requests. Design palette tokens for light and dark themes when both are appropriate; a justified single-theme page is allowed.

Use responsive grid or flex layouts, `gap`, `max-width: 100%`, and `min-width: 0` where children must shrink. Contain wide tables, code, and genuinely wide diagrams inside their own scroll wrappers; the page body must not scroll sideways.

Include UTF-8 and viewport metadata, semantic headings, visible keyboard focus, useful alternative text, valid element structure, and readable contrast. When the page uses animation, transitions, or smooth scrolling, honor `prefers-reduced-motion`.

## Verify before handoff

Before reporting completion, read and apply the [rendering and QA guide](references/qa.md). Inspect the rendered page when a local browser is available and permitted; source inspection alone is not sufficient for visual claims.

End the page with the sources used and anything not verified. In the final response, provide the file path and a concise verification summary, including the diagrams built and the relationship each one encodes.

```


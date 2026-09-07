---
name: visual-primer
description: Create a source-grounded, self-contained HTML picture explainer for a newcomer, using meaningful visuals and few words. Use for concept explanations and the rules or reasons behind a scoped software capability. Repository maps and fixed workflow charts belong to codebase-atlas and code-flow; ordinary prose documentation is outside this skill's scope.
metadata:
  short-description: Beginner-first visual explainer as offline HTML
---

# visual-primer

Explain the user's topic to someone who knows nothing about it, using one self-contained HTML page with big pictures and few words.

The visual-primer approach assumes zero context while treating the reader as an intelligent newcomer. Introduce the real terms plainly.

This skill produces the explanation artifact. Changes to the code, system, or subject being explained require a separate user request.

## Core contract

Keep these four decisions stable; let everything else adapt to the topic:

1. **Zero assumed context.** Introduce each term before the reader needs it.
2. **Pictures carry the idea.** Show the central relationship with large, meaningful geometry before expanding it in prose.
3. **Words stay sparse.** Use short labels and captions around the visuals. Move exact detail and edge cases later.
4. **The story follows the topic.** Let this topic's natural questions and biggest beginner obstacles determine the order, layout, and number of diagrams.

The page should feel simple through organization while retaining decision-relevant facts and comfortably readable type.

Never include source-code bodies, snippets, original prompts, or extracted source lines in the output HTML, including hidden elements and embedded data. Use plain descriptions and diagrams. Real identifiers may accompany those descriptions; file paths and line ranges may identify evidence locations.

Use the user's language unless they request specific languages. Produce separate files for multiple requested languages; preserve real identifiers in their original language.

## Ground the explanation

Inspect the material that defines the topic before designing the page. For a repository or technical system, read the actual code and documentation and use its real names, flows, limits, and failure states. For a general topic, prefer authoritative sources. Mark meaningful uncertainty, inference, or disagreement.

When explaining rules for an existing code-flow result, preserve its subject and scope. Re-read the source before adding rules: a previous verification badge does not verify a new claim. Confirm conditions, numerical values, units, configuration overrides, and exceptions. Omit numerical rules that cannot be verified and explain the gap.

For a paired source-backed rules page, follow [source-rules.md](references/source-rules.md), then apply the visual-story workflow below. The default is an authored, picture-first lesson: compose topic-specific HTML/SVG, CSS and meaningful interactions, bound to reviewed rules and behavior claims. The builder preserves evidence, identity and navigation; it does not prescribe the diagrams. The older comparison/condition/state layout remains available for existing inputs or an explicitly requested compact rules reference, not as the default replacement for a visual lesson. General concepts still use a standalone authored HTML document.

Preserve facts that affect understanding or decisions. A metaphor may unlock the first idea, but state the literal truth first, map the metaphor once, and return to the real terms.

If the user supplies a visual reference, reuse the hierarchy or teaching technique that works. Treat a previous explainer as a reference, and preserve its styling when the user asks for continuity.

## Shape the visual story

Find the one relationship that unlocks the topic, such as an order, handoff, comparison, hierarchy, boundary, composition, or cause. Make that relationship visible early and large enough to scan before reading paragraphs.

Use geometry to express meaning:

- order and handoffs use a visible path and unambiguous direction;
- containment and hierarchy use nesting or position;
- meaningful magnitude uses size, length, or position;
- sameness and difference use repeated shapes, labels, and a cue beyond color;
- causes and failures branch where they actually arise.

Let visual depth follow semantic depth. Context, actors, messages, boundaries, and annotations may occupy distinct layers when that separation helps the lesson. Give meaningfully different connector relationships an appropriate combination of direction, path, line treatment, endpoints, labels, position, or color; keep equivalent relationships visually consistent.

Choose each main visual because it answers a beginner's question faster than prose would. Cards, icons, illustrations, tables, and prose may remain supporting elements when they are the clearest form.

Use motion when time, direction, state change, or causality is part of the idea—for example, data moving through a real path. Consider a small simulation when changing an input or stepping through states explains cause and effect better than a static picture. Keep the essential meaning available in a static state, and encode only precision supported by the source.

After the picture, add only the prose needed to name what happened, correct a likely misconception, or expose an important limit. Put dense tables, field catalogs, and secondary exceptions later or behind `<details>` when that keeps the first explanation clear. Explain code behavior through words and pictures, including in those secondary sections.

Read [diagram patterns](references/diagram-patterns.md) when choosing or repairing a specialized visual, motion, or simulation. Use it as a toolbox.

When the user has not supplied a visual direction, read [visual treatment](references/visual-treatment.md) before styling the page. Derive the art direction from the topic while using that guide as a contemporary baseline.

## Deliverable

Write one `.html` file to the path the user named; otherwise choose a sensible location near the source material and report it.

The file must open directly in a browser without a build step or hosted-artifact service. Inline CSS, scripts, SVG, fonts, and bitmap data so it remains fully usable offline. End the page with the sources used and anything important that was not verified.

Use any browser-native visual technique that suits the lesson. Include UTF-8 and viewport metadata, semantic headings, readable contrast, visible keyboard focus, and useful text alternatives for diagrams. Keep essential content readable on narrow screens without body-level horizontal scrolling. If animation is used, honor `prefers-reduced-motion`.

## Verify before handoff

Read the [rendering and QA guide](references/qa.md) after implementation and apply the checks relevant to the page. When a local browser is available and permitted, base visual-quality claims on representative desktop and narrow-screen renders.

Report the file path and a concise summary of what was actually verified.

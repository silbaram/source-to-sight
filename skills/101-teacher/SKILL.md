---
name: 101-teacher
description: Create a source-grounded, self-contained HTML picture explainer for someone with no background knowledge, using large meaningful visuals and few words. Use when the user invokes $101-teacher, asks to "explain like I'm 5," or wants a dead-simple visual explainer. Do not use for ordinary prose documentation that does not need a visual teaching artifact.
metadata:
  short-description: Beginner-first visual explainer as offline HTML
---

# 101-teacher

Explain the user's topic to someone who knows nothing about it, using one self-contained HTML page with big pictures and few words.

“101” means zero assumed context, not baby talk. Introduce the real terms plainly and treat the reader as an intelligent newcomer.

This is an explanation skill. Do not modify the code, system, or subject being explained unless the user separately asks for that change.

## Core contract

Keep these four decisions stable; let everything else adapt to the topic:

1. **Zero assumed context.** The reader should not need an unexplained term to understand the next sentence.
2. **Pictures carry the idea.** Show the central relationship with large, meaningful geometry before expanding it in prose.
3. **Words stay sparse.** Use short labels and captions around the visuals. Move exact detail and edge cases later.
4. **The story follows the topic.** Choose the questions, order, layout, and visual forms that remove this topic's biggest beginner obstacles. Do not impose a reusable table of contents or a fixed number of diagrams.

The page should feel simple because the information is organized, not because important facts were removed or the type was made enormous.

## Ground the explanation

Inspect the material that defines the topic before designing the page. For a repository or technical system, read the actual code and documentation and use its real names, flows, limits, and failure states. For a general topic, prefer authoritative sources. Mark meaningful uncertainty, inference, or disagreement instead of filling gaps with a plausible story.

Preserve facts that affect understanding or decisions. A metaphor may unlock the first idea, but state the literal truth first, map the metaphor once, and return to the real terms.

If the user supplies a visual reference, reuse the hierarchy or teaching technique that works rather than copying its decoration. A previous explainer is not a template unless the user asks to preserve it.

## Shape the visual story

Find the one relationship that unlocks the topic, such as an order, handoff, comparison, hierarchy, boundary, composition, or cause. Make that relationship visible early and large enough to scan before reading paragraphs.

Use geometry to express meaning:

- order and handoffs use a visible path and unambiguous direction;
- containment and hierarchy use nesting or position;
- meaningful magnitude uses size, length, or position;
- sameness and difference use repeated shapes plus labels, not color alone;
- causes and failures branch where they actually arise.

Let visual depth follow semantic depth. Context, actors, messages, boundaries, and annotations may occupy distinct layers when that separation helps the lesson, but do not impose a fixed number of layers. When connectors represent meaningfully different relationships, preserve those differences with an appropriate combination of direction, path, line treatment, endpoints, labels, position, or color. Do not make different relationships look interchangeable, and do not add ornamental variation to relationships that are actually the same.

Cards, icons, and decorative illustrations are not automatically diagrams. Each main visual should answer a beginner's question faster than prose would. Remove a visual that does not improve understanding, and do not add a diagram merely to satisfy a section pattern.

Use motion only when time, direction, state change, or causality is part of the idea—for example, data moving through a real path. Consider a small simulation when changing an input or stepping through states would explain cause and effect better than a static picture. Motion and simulation are teaching tools, not default polish: keep the essential meaning available in a static state, avoid invented precision, and omit the interaction when it does not materially improve understanding.

After the picture, add only the prose needed to name what happened, correct a likely misconception, or expose an important limit. Put dense tables, code, field catalogs, and secondary exceptions later or behind `<details>` when that keeps the first explanation clear.

Read [diagram patterns](references/diagram-patterns.md) when choosing or repairing a specialized visual, motion, or simulation. It is a toolbox, not an outline.

When the user has not supplied a visual direction, read [visual treatment](references/visual-treatment.md) before styling the page. Use it as a contemporary default, not a house style; the topic's meaning and any provided reference still lead.

## Deliverable

Write one `.html` file to the path the user named; otherwise choose a sensible location near the source material and report it.

The file must open directly in a browser with no network, build step, or hosted-artifact service. Keep CSS, scripts, SVG, fonts, and bitmap data inline. End the page with the sources used and anything important that was not verified.

Use any browser-native visual technique that suits the lesson. Include UTF-8 and viewport metadata, semantic headings, readable contrast, visible keyboard focus, and useful text alternatives for diagrams. Keep essential content readable on narrow screens without body-level horizontal scrolling. If animation is used, honor `prefers-reduced-motion`.

## Verify before handoff

Read the [rendering and QA guide](references/qa.md) after implementation and apply the checks relevant to the page. When a local browser is available and permitted, inspect representative desktop and narrow-screen renders; do not claim visual quality from source inspection alone.

Report the file path and a concise summary of what was actually verified.

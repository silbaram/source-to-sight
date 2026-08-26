# Diagram patterns

Read this guide while deciding which diagrams the explainer needs. Choose the smallest set of patterns that teaches the subject accurately.

## Selection rule

A diagram earns its space when length, position, direction, grouping, or repeated geometry makes an important relationship faster to understand than prose or a table.

Use tables, code blocks, lists, cards, icons, and `<details>` directly when comparison, reference lookup, or exact wording is the actual lesson.

## Proportional strip

Use for packet layouts, budgets, storage, quotas, and time splits when relative size matters.

- Keep segment width proportional to the real quantity and state any visual distortion introduced by a minimum width.
- Exact SVG rectangles are appropriate when the ratio must remain truthful.
- Thin fields should normally use a separate ordered legend or field index. An inset or enlarged detail is another good option.
- If leader lines are justified, keep every line, endpoint, and label visibly separate and inspect the rendered result.
- On narrow screens, pair a compact proportional strip with a readable field list when inline labels would compromise the ratio.

## Connected flow

Use when order is the lesson.

- Put stages on one shared path so direction remains visible without reading every label.
- The path may be horizontal, vertical, or divided into lanes. Choose the geometry that fits the number of stages and the narrow-screen layout.
- Number markers when the sequence is real and the numbers help scanning.
- Keep the final marker and arrowhead as distinct shapes with a visible connecting segment between them.
- SVG markers include invisible view-box space, so verify the rendered arrowhead edge and line endpoint together.

### Connector grammar

Treat the connectors in one visual as a system. If relationships differ by sender, payload, direction, trust boundary, state, or outcome, give the reader a consistent way to see the relevant difference—for example through route, line treatment, endpoint, marker, label plate, position, or restrained color. Match every styling difference to a semantic difference, and keep equivalent relationships visually consistent.

### Motion along a path

Animate a connected flow only when motion makes direction, timing, order, state change, or causality easier to understand.

- Keep the path and its meaning readable before motion begins and when motion is disabled.
- For a data stream, moving markers should follow the real direction and route. Use motion properties only for traffic, speed, volume, and synchronization claims supported by the source.
- Prefer a short, purposeful demonstration. Provide pause and replay or step controls when the motion persists, contains multiple stages, or needs focused study.
- Honor `prefers-reduced-motion` with a useful static or stepped explanation.

## Value assembly

Use an equation of large mono tokens when a value is constructed from meaningful parts, such as an identifier, code, key, or URL. Color tokens by semantic origin.

## Failure map

Reuse the main flow geometry when failures attach naturally to its stages. Branch each failure at the point where it becomes visible to the caller, and end the branch in the actual code or state the caller sees.

Choose a separate geometry when concurrency, retries, or cross-cutting behavior needs its own spatial structure.

## Anchor number

Use one value at display size with its unit and consequence beneath it when a single number is the lesson.

## Annotated object

Draw a record, screen, message, or device once and call out only the parts needed for the current lesson. Put remaining fields in a separate reference table or field list.

Prefer an ordered legend over many callout lines when annotations become dense. If callouts are necessary, route them through whitespace, keep endpoints away from text, and verify them at the actual rendered size.

## Explanatory simulation

Use a small simulation when a reader-controlled input or step reveals cause and effect that would be cumbersome or misleading as a static sequence. Good candidates include changing a permission to reveal its consequence, following a request through states, or comparing the same flow with and without a safeguard.

- Teach one relationship at a time and keep the state space small.
- Make inputs, current state, transition, and result visibly distinct; provide a clear reset when the reader can change state.
- Keep behavior deterministic. Use randomness when it is the lesson, label simplifications, and use source-supported values and precision.
- Preserve a concise static explanation so the lesson survives disabled scripts, reduced motion, and assistive reading.
- Choose a labeled before/after picture or short sequence when it teaches the same idea more directly.

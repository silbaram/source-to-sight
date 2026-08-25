```markdown
# Diagram patterns

Read this guide while deciding which diagrams the explainer needs. These are patterns and decision criteria, not a required checklist. Choose the smallest set that teaches the subject accurately.

## Selection rule

A diagram earns its space when length, position, direction, grouping, or repeated geometry makes an important relationship faster to understand than prose or a table.

Supporting elements such as tables, code blocks, lists, cards, icons, and `<details>` remain useful. They do not need to become diagrams when comparison, reference lookup, or exact wording is the actual lesson.

## Proportional strip

Use for packet layouts, budgets, storage, quotas, and time splits when relative size matters.

- Keep segment width proportional to the real quantity. If a minimum width distorts the ratio, state that clearly.
- Exact SVG rectangles are appropriate when the ratio must remain truthful.
- Thin fields should normally use a separate ordered legend or field index. An inset or enlarged detail is another good option.
- If leader lines are justified, apply the clearance and render-check requirements from `SKILL.md`.
- On narrow screens, a compact unlabeled proportional strip plus a readable field list is usually better than shrinking every label or stacking segments in a way that destroys the ratio.

## Connected flow

Use when order is the lesson.

- Put stages on one shared path so direction remains visible without reading every label.
- The path may be horizontal, vertical, or divided into lanes. Choose the geometry that fits the number of stages and the narrow-screen layout.
- Number markers when the sequence is real and the numbers help scanning.
- Keep the final marker and arrowhead as distinct shapes with a visible connecting segment between them.
- SVG markers include invisible view-box space. Verify the rendered arrowhead edge rather than trusting the line endpoint.

## Value assembly

Use an equation of large mono tokens when a value is constructed from meaningful parts, such as an identifier, code, key, or URL. Color tokens by semantic origin, not decoration.

## Failure map

Reuse the main flow geometry when failures attach naturally to its stages. Branch each failure at the point where it becomes visible to the caller, and end the branch in the actual code or state the caller sees.

Use a different geometry when forcing failures onto the main path would hide concurrency, retries, or cross-cutting behavior.

## Anchor number

Use one value at display size with its unit and consequence beneath it when a single number is the lesson. Do not use an anchor number merely to decorate a section.

## Annotated object

Draw a record, screen, message, or device once and call out only the parts needed for the current lesson. Put remaining fields in a separate reference table or field list.

Prefer an ordered legend over many callout lines when annotations become dense. If callouts are necessary, route them through whitespace, keep endpoints away from text, and verify them at the actual rendered size.

```


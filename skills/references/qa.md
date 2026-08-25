```markdown
# Rendering and QA

Read this guide after the HTML is implemented and before handoff.

## Render representative sizes

When a local browser is available and permitted:

1. Render a desktop viewport near `1440 × 900`.
2. Render a narrow viewport near `390 × 844`.
3. Inspect the first screen and the densest diagram or table.
4. Inspect every distinct diagram geometry once at its intended size. “Distinct” means a unique visual structure or template, not every repeated instance of the same component.
5. Recheck diagrams changed during collision fixes or responsive adjustments.

For connected flows, inspect at 100% zoom:

- the final marker and arrowhead;
- branch junctions and line endings;
- leader lines and label edges;
- shapes that share a color or nearly touch.

Repeat a diagram in both themes when theme colors could merge nearby shapes or reduce contrast. Do not repeat every diagram merely because both themes exist.

## Fix visible defects

Fix clipped text, unreadably small labels, excessive empty space, narrow cards, body-level horizontal overflow, merged shapes, misleading proportional distortion, and dark-theme contrast problems.

Do not hide body overflow to conceal a layout bug. Wide technical material may scroll inside a clearly contained wrapper.

## Handoff tests

- **Five-second test:** the first screen says what the subject is and what it does.
- **Picture-first test:** core explanatory sections normally lead with an informative visual. Source, unknown, appendix, and raw-reference sections are exempt, and a table may lead when comparison itself is the lesson.
- **Label-off test:** without labels, the intended order, relative size, direction, or grouping still reads. Exact names need not remain knowable.
- **Magnitude test:** relationships whose relative magnitude changes understanding or decisions appear as size, length, or position. Exact-only values may remain labels or tables.
- **Collision test:** trace every line ending, arrowhead, node outline, leader line, and label edge at desktop and mobile sizes. Nothing touches or overlaps unless that contact encodes a relationship.
- **Novice test:** no unexplained term is required to understand the next sentence.
- **Scan test:** headings and diagrams tell the main story without every paragraph.
- **Prose test:** no long note is standing in for a missing picture.
- **Source test:** identifiers, values, and exceptions match the inspected source.
- **Mobile test:** essential content is readable without sideways body scrolling.
- **Reference test:** a supplied reference influences clarity and information density, not merely colors.

When browser rendering is unavailable, validate markup, duplicate IDs, internal anchors, and external URLs. State clearly that visual rendering was not verified.

```


# Rendering and QA

Read this guide after the HTML is implemented and before handoff. Apply the checks that match the page's actual content; do not add sections, diagrams, themes, or interactions just to create something to test.

## Inspect representative views

When a local browser is available and permitted:

- Render desktop and narrow-screen views that represent the intended use. `1440 × 900` and `390 × 844` are useful examples, not fixed targets.
- Inspect the first screen, the densest content, and every distinct visual geometry at least once.
- Recheck any visual changed to fix a collision or responsive defect.
- Check each supported theme only when its colors or contrast could change the result.

For connected flows and annotated visuals, inspect the places where accidental contact would change the meaning:

- arrowheads and their target shapes;
- branch junctions and line endings;
- leader lines and label edges;
- shapes that nearly touch or share a color.

Compare connectors as a system. If relationships differ by sender, payload, direction, trust boundary, state, or outcome, verify that the rendered connector grammar preserves the differences that matter. If the relationships do not differ, avoid ornamental variation.

## Inspect layers and collisions

For every layered or connected visual, identify which objects are meant to be inside a boundary, outside it, or intentionally overlapping before judging the render. Then inspect the actual screenshot, not only the DOM or source coordinates:

- **box against box:** unrelated cards, nodes, controls, badges, and captions do not intersect, crowd one another, or create a false group;
- **object against boundary:** an actor is clearly inside or outside a trust, system, or ownership boundary. It must not straddle the boundary unless crossing it is the lesson and that meaning is explicit;
- **connector against object:** each route remains traceable from source to target. A useful length of the shaft and the complete arrowhead stay visible instead of disappearing beneath a card, boundary, label, or clipped container;
- **text against layer:** labels, captions, and explanatory text are not covered, clipped, threaded through a connector, or pressed against a container edge;
- **stacking order:** background regions remain behind their contents, while foreground objects do not hide essential boundaries, connector endpoints, controls, or annotations.

Intentional overlap is allowed only when it communicates containment, crossing, comparison, or another real relationship. Preserve enough exposed outline, whitespace, and contrast that the relationship is unmistakable, and never obscure essential text or an arrow endpoint.

Viewport overflow checks and bounding rectangles can flag candidates, but they cannot prove that a layered visual is collision-free or semantically correct. Do not declare QA passed from automated metrics alone.

When the page uses motion or simulation:

- inspect the static, active, completed, paused, replayed or reset, and `prefers-reduced-motion` states that actually exist;
- verify controls are keyboard operable, state changes are announced or otherwise perceivable, and the explanation remains understandable without motion;
- confirm animation paths, timing, and simulation outcomes do not imply unsupported throughput, precision, ordering, or causality.

## Fix visible defects

Fix clipped or tiny text, ambiguous direction, overlapping connectors, false visual contact, misleading proportions, excessive empty space, narrow cards, weak contrast, and body-level horizontal overflow.

Repair collisions by correcting the visual geometry: reserve whitespace, move an actor wholly to the correct side of a boundary, enlarge the canvas or container, reroute a connector through open space, or correct the stacking order. Do not merely hide overflow or cover the collision with another fill. After a repair, recapture the affected visual at desktop and narrow widths and recheck every object, boundary, connector, label, and relevant animation state that shares the changed space.

Do not hide body overflow to conceal a layout bug. A genuinely wide table or technical diagram may scroll inside a clearly bounded wrapper.

## Outcome checks

Every page should pass these core checks:

- **Zero-context test:** a newcomer can follow the first explanation without already knowing an unexplained term.
- **Picture-first test:** the central relationship is visible before long prose or reference material.
- **Few-words test:** the strongest visuals use short labels and a concise interpretation instead of paragraph-sized annotations.
- **Topic-fit test:** the sequence and headings follow this topic's natural questions rather than a reusable template.
- **Five-second test:** the first screen says what the subject is and why it matters.
- **Source test:** identifiers, values, limits, and exceptions match the inspected sources; uncertainty is labeled.
- **Responsive test:** essential content remains readable without sideways body scrolling.
- **Accessibility test:** semantic structure, focus, contrast, and text alternatives support keyboard and assistive-technology users.

Apply these when the corresponding relationship exists:

- **Order test:** direction and stage boundaries are unambiguous.
- **Magnitude test:** important relative size appears through size, length, or position, or the limitation is disclosed.
- **Comparison test:** the visual uses consistent geometry for like-for-like comparison.
- **Collision test:** connectors, shapes, and labels do not overlap or touch in a way that changes the meaning.
- **Box collision test:** cards, nodes, controls, captions, and badges neither intersect nor become falsely grouped unless the overlap is deliberate and readable.
- **Boundary integrity test:** each object is unmistakably inside, outside, or crossing a semantic boundary, and its rendered position matches that meaning.
- **Occlusion test:** no layer, clipping region, or stacking order hides essential text, connector shafts, arrowheads, endpoints, controls, or boundary edges.
- **Connector distinction test:** relationships that matter differently do not all look interchangeable, and each visible connector variation represents a real distinction.
- **Motion test:** motion accurately teaches change, direction, order, or causality; the essential meaning remains available when paused or reduced.
- **Simulation test:** inputs, transitions, results, reset behavior, and stated simplifications remain understandable and correct.
- **Reference test:** a supplied reference influences useful hierarchy or teaching technique rather than only decoration.

When browser rendering is unavailable, validate markup, duplicate IDs, internal anchors, and external URLs. State clearly that the visual result was not rendered.

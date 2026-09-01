# Rendering and QA

Read this guide after the HTML is implemented and before handoff. Let the page's actual content determine which checks apply.

## Inspect representative views

When a local browser is available and permitted:

- Render desktop and narrow-screen views that represent the intended use. `1440 × 900` and `390 × 844` are useful starting points.
- Inspect the first screen, the densest content, and every distinct visual geometry at least once.
- Recheck each visual after geometry or responsive changes.
- Check each supported theme whose colors or contrast could change the result.

For connected flows and annotated visuals, inspect the places where accidental contact would change the meaning:

- arrowheads and their target shapes;
- branch junctions and line endings;
- leader lines and label edges;
- shapes that nearly touch or share a color.

Compare connectors as a system. Relationships that differ by sender, payload, direction, trust boundary, state, or outcome should retain the relevant visual differences; equivalent relationships should use a consistent treatment.

## Inspect layers and collisions

For every layered or connected visual, identify which objects belong inside a boundary, outside it, or in an intentional overlap. Inspect the actual screenshot alongside the DOM or source coordinates:

- **box against box:** independent cards, nodes, controls, badges, and captions maintain clear separation and grouping;
- **object against boundary:** each actor lies clearly inside, outside, or across a trust, system, or ownership boundary according to its meaning;
- **connector against object:** every route is traceable from source to target, with a useful shaft length and complete arrowhead visible;
- **text against layer:** labels, captions, and explanatory text remain fully visible with comfortable edge clearance;
- **stacking order:** background regions support their contents while essential boundaries, connector endpoints, controls, and annotations remain exposed.

Intentional overlap should communicate containment, crossing, comparison, or another real relationship. Preserve enough exposed outline, whitespace, and contrast to make that relationship unmistakable while keeping essential text and arrow endpoints visible.

Use viewport overflow checks and bounding rectangles to locate candidates, then use rendered inspection to determine whether the layered visual is clear and semantically correct.

When the page uses motion or simulation:

- inspect the static, active, completed, paused, replayed or reset, and `prefers-reduced-motion` states that actually exist;
- verify controls are keyboard operable, state changes are announced or otherwise perceivable, and the static explanation remains complete;
- confirm animation paths, timing, and simulation outcomes express only throughput, precision, ordering, and causality supported by the source.

## Fix visible defects

Fix clipped or tiny text, ambiguous direction, overlapping connectors, false visual contact, misleading proportions, excessive empty space, narrow cards, weak contrast, and body-level horizontal overflow.

Repair collisions through visual geometry: reserve whitespace, move an actor wholly to the correct side of a boundary, enlarge the canvas or container, reroute a connector through open space, or correct the stacking order. After a repair, recapture the affected visual at desktop and narrow widths and recheck every object, boundary, connector, label, and relevant animation state that shares the changed space.

Achieve page-level horizontal fit through responsive geometry. A genuinely wide table or technical diagram may scroll inside a clearly bounded wrapper.

## Outcome checks

Every page should pass these core checks:

- **Zero-context test:** the first explanation introduces each term before using it.
- **Picture-first test:** the central relationship is visible before long prose or reference material.
- **Few-words test:** the strongest visuals use short labels and a concise interpretation.
- **Topic-fit test:** this topic's natural questions shape the sequence and headings.
- **Five-second test:** the first screen says what the subject is and why it matters.
- **Source test:** identifiers, values, limits, and exceptions match the inspected sources; uncertainty is labeled.
- **Responsive test:** essential content remains readable within the body width.
- **Accessibility test:** semantic structure, focus, contrast, and text alternatives support keyboard and assistive-technology users.

Apply these when the corresponding relationship exists:

- **Order test:** direction and stage boundaries are unambiguous.
- **Magnitude test:** important relative size appears through size, length, or position, or the limitation is disclosed.
- **Comparison test:** the visual uses consistent geometry for like-for-like comparison.
- **Collision test:** every contact among connectors, shapes, and labels communicates the intended relationship; independent elements retain clear space.
- **Box collision test:** cards, nodes, controls, captions, and badges have readable separation, grouping, and intentional overlap.
- **Boundary integrity test:** each object is unmistakably inside, outside, or crossing a semantic boundary, and its rendered position matches that meaning.
- **Occlusion test:** essential text, connector shafts, arrowheads, endpoints, controls, and boundary edges remain visible across layers and clipping regions.
- **Connector distinction test:** each visible connector variation represents a real distinction, and equivalent relationships remain consistent.
- **Motion test:** motion accurately teaches change, direction, order, or causality; the essential meaning remains available when paused or reduced.
- **Simulation test:** inputs, transitions, results, reset behavior, and stated simplifications remain understandable and correct.
- **Reference test:** a supplied reference meaningfully influences hierarchy or teaching technique.

When browser rendering is unavailable, validate markup, duplicate IDs, internal anchors, and external URLs, and report the scope of verification accurately.

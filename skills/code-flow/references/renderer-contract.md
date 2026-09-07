# Renderer contract

This directory contains the shared renderer and validation foundation, used by code-flow and the codebase-atlas companion. The host agent performs source discovery and semantic review; scripts capture evidence, validate, and render. The [assembly protocol](assembly-protocol.md) documents the installed `author.py` 0.7.0 helpers; the graph schema remains the unfrozen 0.1.0 draft.

## Run

Python 3.10+ is required; the Python validator is bundled with its [license and provenance](../scripts/vendor/PROVENANCE.md). No Python package installation is needed. Node is only needed for development, browser tests, and updating the vendored layout engine.

Set `SKILL_ROOT` to the installed code-flow directory and `SOURCE_ROOT` to the project being explained. The following commands use an internal graph prepared at `$SOURCE_ROOT/work/graph.json` through the [assembly protocol](assembly-protocol.md).

~~~sh
python3 "$SKILL_ROOT/scripts/s2s.py" validate "$SOURCE_ROOT/work/graph.json"
python3 "$SKILL_ROOT/scripts/s2s.py" render "$SOURCE_ROOT/work/graph.json" \
  --source-root "$SOURCE_ROOT" --output "$SOURCE_ROOT/build/behavior.html"
python3 "$SKILL_ROOT/scripts/s2s.py" inspect "$SOURCE_ROOT/build/behavior.html"
~~~

`render` always re-reads the referenced source files before writing a page. Use the actual source checkout as `--source-root`. Input, HTML and optional `--data-output` render JSON must use separate files, including symlink/hardlink aliases. Existing HTML must belong to the same repository, layer, subject, scope and language. These guards are shared with `author.py build` and run before output writes.

`inspect` extracts the subject/language/command needed for future agent-driven refresh. It does not perform discovery or execute the command.

## Two contracts

- [Internal schema](ir-internal-v0.1.0.schema.json): evidence has a one-line `anchorText`, a captured SHA-256 `contentHash` (or null on first capture), and the source location.
- [Render schema](ir-render-v0.1.0.schema.json): no anchors or source-body fields; claims additionally have a computed `displayStatus`.
- `contentHash` preserves the source revision used for the review. Each reread sets `observedContentHash` to the current file's SHA-256, or null if the file could not be read. A failed comparison does not replace the reviewed hash. The new field is optional when reading older 0.1.0 pages.
- Keep shared fields consistent across both schemas while preserving each contract's evidence and display differences.
- The bundled validator supports the keywords currently used by these Draft 2020-12 schemas through a checked Draft 7-compatible subset. Unsupported schema extensions are rejected until their compatibility is reviewed. Validation does not insert defaults or mutate input data. Graph errors retain their previous path ordering; layout errors now use that same deterministic ordering. Diagnostic wording can differ.
- `snapshot.generatedAt` is always checked as an RFC 3339 date-time, including calendar dates and UTC offsets. Lowercase `t`/`z` and fractional seconds are supported; leap-second spelling is rejected. Older installations could skip this check when the optional format checker was absent; malformed timestamps must be corrected before rebuilding.
- Root fields include the subject/scope, snapshot, provenance, language, analysis status, summary, nodes, edges, optional scenario contents, rules, evidence, warnings, links, and regeneration metadata. Collections may be empty; fields are still explicit.
- Profiles are discovery metadata. The renderer only branches on graph semantics, analysis state, layer, viewport size, and language.

IDs are globally unique within a document. Edges, steps, state transitions, rules, regions, warnings, and supplemental sources must reference existing objects. A step references exactly one node or edge. Context-only actors have no verification claims.

The contract supports Korean and English viewer controls. Labels and explanations come from the IR. Other languages are not yet validated as complete localized viewer experiences.

## Trust boundary

The author must re-read the relevant code and supply an honest semantic review using `supportStatus` and `verificationNote`. The script checks locations, hashes, schemas, and references; it cannot decide whether arbitrary prose accurately describes a program.

- `exact/resolved` plus a supported claim and verified locations receives `confirmed`.
- Location failure receives `unverified`; it never becomes `resolved` merely by failing.
- Inferred or semantically uncertain claims remain visibly uncertain.
- Unsupported claims are omitted. A broken scenario is omitted as a whole rather than silently skipping a step.
- Numerical rules require confirmed evidence. A digit check covers `plainText`, `condition`, `outcome`, optional `rationale` and `exceptions`, and also catches an incorrectly unset `numeric` flag. The author must still identify written-out quantities, units, and configuration overrides. Reasons and exceptions share the rule's evidence and review status; they are not independent unchecked captions.
- A copied anchor or a recognizable fenced/declaration-style code block in output text is rejected. This is an additional guard, not a universal classifier of code versus prose.

Synthetic examples are prominently identified and are not counted as source-tracing evaluations. `humanReviewed` must only be true after an actual human review.

## Output and navigation

Generated HTML embeds data, scripts, styles, font, and licenses. No server or external asset request is needed. JSON is escaped for an HTML data script; displayed text is created through text nodes.

Evidence paths stay inside the supplied source root, including after symlink resolution. Page links are relative. Existing linked pages are checked for layer, subject, kind, module, targets, scope, language, and source snapshot. A file with the wrong subject does not activate a link. Legacy minimal catalogs retain their ID-only subject check. Different or unknown source snapshots produce a warning; navigation involving an atlas also requires a snapshot match before enabling the link.

Snapshot comparison rejects failed locations, missing captured hashes, and conflicting observed hashes. When resolving a page link, the renderer rereads every evidence file recorded by either page under the current source root and compares its SHA-256, including files only examined by the linked page. Missing files and symlinks outside the source root cannot establish a match. A shared clean commit allows different evidence selections only after this reread: Git cleanliness alone does not cover ignored settings or installed dependencies. Without access to the source root, or for a dirty or unknown working tree, the entire recorded evidence-file set and its hashes must match; agreement on a shared subset is insufficient. This compares the recorded evidence scope, not files that were never examined. Warnings name the affected page while keeping a valid destination navigable.

Create a child page, then regenerate the parent to bake in its new link state. The renderer cannot generate another explanation by clicking in an offline page. Generation commands are copied for the user to run in the host.

The `visual-primer` pair builder can supply both newly prepared render graphs to the same link checks before writing the files. The rules graph retains the behavior's subject, scope, language, nodes, edges, scenarios and state transitions, preserves its evidence and rule meaning, and adds reviewed rules/reasons/exceptions. The presentation layout only selects rules and existing transitions. It cannot silently change the behavior. Both destinations are checked before replacement; each individual replacement is atomic, and a write failure may require rerunning the pair.

The source-backed rules page uses `data-viewer="primer"`, the same output IR, regeneration metadata, semantic palette and theme preference. Its topic-specific composition selects comparison, condition/result and state figures without inventing execution edges. All explanations are readable without JavaScript; scripts add condition selection. If verification removes a selected claim, its entire figure is withheld. Small logic graphs remain valid in the canvas renderer; general visual-primer concepts retain their authored HTML workflow.

## Layout and interaction

The vendored Dagre engine computes geometry; the template draws native SVG connections and accessible HTML node buttons. Layout uses private node and edge IDs so valid IR identifiers such as `constructor` or `toString` cannot collide with Graphlib's object keys. Selection, evidence, search, and walkthroughs retain the original IR identifiers. Self-edge endpoints use a small documented correction for Dagre 3.1.1. Browser tests check every displayed connection's endpoints and intersections with unrelated nodes.

The production template uses the approved canvas UI. Its left rail searches actual node labels, roles, and identifiers; the component list also reaches detail nodes. Structure is the initial view. Walkthrough controls appear only after choosing a scenario or the walkthrough view, and only when the IR supplies ordered scenarios. Unordered and single-node explanations do not acquire invented playback.

Dagre uses horizontal layout on wide canvases and vertical layout on narrow canvases. A scaled scroll surface supports native touch scrolling, pointer dragging, keyboard panning, zoom/fit, and a minimap. Initial zoom keeps labels readable; larger graphs can extend beyond the viewport. The scroll surface has stable room around the graph so edge nodes can move clear of a panel. Fit frames the graph bounds rather than this extra scroll space. Arrow checks account for the SVG screen transform.

Evidence panels open on selection on both desktop and mobile. Node selection and zoom keep the selected node in the visible map area beside the desktop panel or above the mobile sheet. The mobile page reserves scroll room while its sheet is open. Walkthrough navigation reveals detail nodes and brings its target into view without opening a panel. Neighbor focus dims unrelated items and names its anchor in the breadcrumb. Selecting a different node or evidence item clears that focus; canvas, search, list, and keyboard selection share this rule. Reopening the same anchor offers “Clear connection focus,” which keeps the current selection and camera. Changing views or advancing a walkthrough also clears the filter. Back independently restores the prior focus, selected item, view, scenario step, detail level, and camera within this page. Autoplay starts only on request, stops on manual navigation or the final step, and respects reduced-motion settings for animated edges.

During autoplay a marker travels from source to target along the actual routed SVG edge, followed by a brief arrival highlight. The transfer strip names both ends and the relationship, also when paused or motion is reduced. This depicts the existing relationship direction (including calls and read requests), not measured payload delivery or a recorded execution. Both the step and edge must be confirmed; registration/dependency and uncertain/unverified edges keep static styling. A node-only step can use exactly one confirmed forward edge from the immediately preceding confirmed node step. Missing/reverse/ambiguous links and repeated node captions never create new edges or inferred returns. Explicit self-loop steps use the existing self-loop route.

Selection and walkthrough navigation move the map to the target with a 360 ms eased pan, shrinking only when needed to fit the available map area. The page scrolls with that movement only when the map needs to enter the viewport. A target that already fits leaves the camera still. Revealing detail nodes retains the preceding connection's source position before moving, so a graph rebuild does not first jump to a different location.

Playback waits for camera movement to finish before starting the connection marker and the step's reading time (1.5 seconds at 1×). Camera travel adds to that time, including on the first and final steps; a one-step scenario can play once. The status identifies camera travel separately from explanation playback. Pause freezes both the camera and reading progress. Resuming completes any needed framing before using the remaining reading time, including on the final step; playing a completed scenario restarts it. New selection, scenario/view changes, and a hidden page cancel pending movement and the marker. Wheel scrolling, canvas dragging/touch panning, and keyboard panning take control and pause autoplay.

Resizing cancels the old camera destination, reframes the current step in the new viewport, and keeps its reading progress. Enabling reduced motion immediately finishes any pending camera movement. Reduced motion retains arrows, endpoint names, evidence status, and timed step progression without animated camera movement, moving markers, or arrival pulses.

The player shows explanation progress and ready/playing/paused/completed status for every step. Steps without an animated transfer pulse their currently explained nodes, preserving uncertain/unverified colors; parallel groups are labeled explicitly. These nondirectional pulses show the reader's place in the explanation, not worker timing, concurrency counts, or an inferred event chain. Pause removes pulses and freezes progress. Reduced motion uses discrete step progress and static node emphasis instead. The current target has `aria-current="step"`, and the progress indicator exposes a localized step count and status without announcing animation frames.

The walkthrough player displays the scenario `kind`, step `branch`, optional step `condition`, and optional `execution` (`sequential`, `parallel`, `unordered`) next to the caption. Condition and execution metadata belong to the step's evidence-backed claim, including its uncertainty. Parallel/unordered node-only steps prevent inferred transfers between adjacent captions on either side of that boundary. An explicit step `edgeId` can animate a checked dispatch, local call, or join using the normal relationship/status gates, even within a parallel/unordered group. It identifies that relationship, not an order or timing between workers; an unordered receiver loop can still await one recipient at a time. Missing, structural and unchecked relationships never acquire motion from execution metadata. The condition and labels are cleared when the next step does not supply them. These optional fields extend the unfrozen 0.1.0 draft; earlier inputs remain valid.

The desktop inspector belongs to the canvas overlay and fits the available map/viewport height, including page scrolling and window resizing. It leaves with the map when the map scrolls out of view. Mobile uses a sheet capped by the dynamic viewport height. Only the explanation body scrolls; the status/close header and connection-focus button remain reachable. A new selection starts its explanation at the top. Long evidence lists must not cover the map footer or push the inspector controls outside the visible panel.

The header's dark-mode switch updates the entire semantic palette, including graph edges and arrowheads. Its preference is saved under `s2s-atlas-theme` when local storage is available; denied storage does not block rendering or switching. The default is light. Generated files embed these assets; existing HTML must be regenerated to receive template changes. The `data-viewer="canvas"` marker and browser tests guard against accidentally using the old shell.

The walkthrough player provides 1×, 1.5× and 2× speeds and a direct step selector. The speed applies to a shared explanation clock used by the step timeout, progress and moving marker. Changing it preserves elapsed time during playback, pause or camera movement; it neither restarts the step nor advances it while the camera is framing. Direct selection pauses playback, updates the caption/condition/evidence and exposes required detail nodes. No-scenario pages keep these controls hidden.

Keyboard navigation remains local to the exploration workspace. Enter on the canvas focuses the selected or first visible node. Node arrow keys find a nearby node in the indicated layout direction, Home/End focus the first/last visible node, and native Enter/Space opens its evidence. Focus stays on the same visible item across a redraw. Canvas arrow keys retain panning. In walkthrough view, brackets move steps and P plays/pauses; Space on the canvas also toggles playback. Editable fields, selects, inspector content, composition events and browser modifier shortcuts are excluded. Native button activation is not replaced.

The current-view link uses a versioned `#s2s=1` fragment, with the subject ID, view, detail level, speed, stable scenario/step IDs and optional node/edge/item, panel and connection-focus state. It does not encode executable commands, camera coordinates or an autoplay request. Values are encoded as URL parameters and resolved against the current render IR. Missing/duplicate/invalid references or an incompatible subject restore the default view and show a notice. Existing non-view document anchors are left alone. Updates use `replaceState` so autoplay does not fill browser history; hash navigation also restores views. If URL updates are denied, the copy control still builds the link from current state. Clipboard denial exposes a selectable field instead of reporting success.

The mobile sheet can expand for reading and shrink to leave more map visible. Its header keeps link, size and close controls accessible; connection focus stays below the internally scrolling body. Safe-area padding and a viewport-bounded minimum reading height support short/rotated screens. Sheet changes reframe the current inspected node or edge, and do not restart playback. Desktop retains its existing bounded overlay.

The same visual components serve IR layers without changing coverage: behavior output says “Scoped overview”; only atlas output uses a whole-map label. The codebase-atlas companion supplies actual project discovery and reviewed assembly. The design prototype's synthetic samples are never imported by the production renderer.

In structure view, changing Core/Detail preserves a still-visible node or edge selection and its evidence panel. If the selected item is hidden by Core, its selection/panel and any hidden focus anchor are cleared. Walkthrough view retains its existing step-reset behavior on Core/Detail changes.

State panels show the transition trigger separately from the state summary, together with the verification note and evidence. Map regions display their own verification badges and open their own evidence panels; a region's uncertainty is separate from its member nodes' status.

An item's inspector omits a verification note when its text matches the visible title or description after collapsing whitespace. Distinct verification notes, including extra conditions or uncertainty, remain visible. This presentation rule does not remove claim metadata, evidence locations, or status badges from the output data.

Changing source evidence, wording, or the schema requires rebuilding outputs. Changing layout or interaction requires relevant browser tests and screenshot inspection.

## Project maps

Project maps include scoped `subjects` entries for representative capabilities. Each has its own summary, resolved subject identity, question, targets, included/excluded scope, owner node and evidence-backed claim status. Rejected entries are omitted and uncertain entries retain their own badge, independently of the owner. New atlas authoring requires code/config evidence for capability entry locations. Existing label-only behavior targets can be preserved with explicit location evidence; the copyable generation request carries both. Old four-field catalogs remain readable.

Atlas regions have disjoint node membership. Compound layout groups actual nodes without inventing aggregate invocation edges. Their labels show the group's own status and open its evidence; entering a region shows all members and their immediate neighbors through actual edges. Region navigation and capability search preserve detail reveal, selection, zoom, mobile inspection and Back. Single-node maps need no region or scenario. A catalog is not a playback scenario.

The atlas builder checks supplied behavior identity against the catalog and checks the parent's catalog on return. Only explicitly supplied details are built; other compatible existing files may be linked when they already expose an active return link to this map, but are not rewritten. Missing, stale, incompatible or one-way files remain precise generation requests. Requested pages are all validated/rendered before any destination replacement. Replacements are individually atomic; a filesystem failure may require rerunning the build.

Atlas detail links carry a `s2s-atlas` query parameter containing the parent's versioned hash state. Region, selected item, core/detail mode and finite bounded camera coordinates return through behavior and rules pages without browser storage. The destination always comes from the detail's own validated atlas URL. Incoming state cannot supply a destination or request autoplay; invalid IDs or camera values use the default view and a notice. Ordinary current-view copy links capture IDs and region, while camera coordinates are added only for map/detail round trips.

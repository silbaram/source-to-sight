# Development

M0 implements the technology-neutral data contracts, evidence/location checks, offline graph renderer, and fixture/browser tests. M1 adds the `code-flow` source-discovery skill, six profiles, draft/evidence/build helpers, and six pinned source readings. M1.5 adds source-role comparisons, regression reports, and digest-bound human review forms. M2 expands the corpus to 24 candidates and adds complex-behavior guidance, path conditions, execution-order labels, and required behavior/path checks. M3 adds source-backed rules discovery and paired `visual-primer` pages, with six more evaluation cases. Independent human gates remain pending. M4 adds playback speeds, direct step selection, keyboard navigation, adjustable mobile sheets and view links; repository-map discovery remains M5 work.

See the [development plan](../plans/source-to-sight-evolution-plan.md), [M0 verification record](../eval/reports/m0-verification.md), [renderer contract](../skills/code-flow/references/renderer-contract.md), and [fixture provenance](../fixtures/manifest.md).

## Reproduce the examples

Requirements: Python 3.10+ with pip, Node.js with npm, and a local Chromium installed through Playwright for browser tests.

~~~sh
python3 -m pip install -r skills/code-flow/scripts/requirements.txt
npm ci
npx playwright install chromium
python3 scripts/fetch_fixture_sources.py
npm run fixtures
npm run m1:sources
npm run m1:examples
npm run eval:rules -- --output build/eval/m4
npm test
S2S_EVAL_DIR=build/eval/m4 npm run test:browser
~~~

Dependency installation and the pinned source download need internet access. Rendering and browser tests use local files. The generated HTML itself makes no external asset requests.

Open `build/examples/agent-run.html`, `framework-plugin.html`, or `utility-minimum.html` directly in a browser. All eleven examples are in the same folder. Screenshots from the browser tests are written to `build/qa/`.

The six M1 readings are in `build/m1/`; their browser screenshots go to `build/m1/qa/`. `npm run m1:examples` renders the checked-in readings with fresh evidence checks. It is not an automatic analyzer. For a new repository/question, the host follows [code-flow](../skills/code-flow/SKILL.md) and its discovery/assembly protocols. See [M1 verification](../eval/reports/m1-verification.md), [case provenance](../eval/m1/README.md), and the [human review worksheet](../eval/reports/m1-human-review.md).

The command above renders **24 behavior + 6 paired rules pages** to `build/eval/m4/`. Runs require a new output directory to preserve earlier results and reviewer answers. For subsequent runs choose another directory and set `S2S_EVAL_DIR=build/eval/<run-name>` when running the browser suite; all evaluation browser tests then use that run. See the [evaluation guide](evaluation.md), [case catalog](../eval/cases.md), and [rubric](../eval/rubric.md). The original 18-case manifest remains at `eval/cases-m15.json`, and `eval/cases.json` still defines the 24 behavior cases. These are recorded candidate replays, not independent model generation experiments.

Open `build/eval/m4/agent-parallel-tools.html` for parallel tool dispatch and result recording, or `utility-retry-budget.html` for retry/stop conditions. Choose the walkthrough view and a scenario. Each step shows its path kind, branch, prerequisite and execution-order metadata when present. Confirmed explicit dispatch/call/result-recording connections can animate within parallel groups too; node-only captions do not invent connections or worker order across parallel/unordered boundaries. Registration/dependency and uncertain connections retain static direction styling. Every step shows explanation progress. Steps without a moving transfer pulse the currently explained nodes, and parallel groups have an explicit playback label.

Open `build/eval/m4/agent-parallel-tools-rules.html` to compare per-run/default step limits and recoverable/fatal errors. `library-resize-callbacks-rules.html` includes calculated input examples; `event-async-lifecycle-rules.html` shows registration and release states. Each links back to its matching behavior page, which now links to the rules page. The pages share the theme preference and evidence conventions. Comparisons have keyboard controls; the full explanation is also present in static HTML.

For new rules, the host follows the [rule checklist](../skills/code-flow/references/rule-checklist.md), then the actual installed `visual-primer` [source-rules workflow](../skills/visual-primer/references/source-rules.md). `author.py explain` creates an unendorsed draft from the internal behavior IR. After rereading the source, author the reasons, exceptions and presentation layout, then use `rules.py build-pair`. The two pages must keep the same factual graph and subject/scope/language. A saved HTML alone does not restore stripped evidence.

Offscreen targets come into view with a 360 ms eased camera movement; targets already visible keep the map still. When needed, page alignment and zoom happen within the same movement. The connection animation and the step clock start after the camera settles. At 1× a step takes 1.5 seconds; 1.5× and 2× scale both the reading time and transfer. Changing speed preserves elapsed explanation time, including while paused. Camera movement retains its duration. Pause freezes movement and progress; resume finishes framing before continuing the remaining step time. Manual wheel scrolling or canvas panning pauses autoplay. Reduced motion keeps immediate framing, static emphasis and discrete step progress.

The M1 source fetcher can resume a failed download from an empty, unborn Git checkout with the expected origin (or one interrupted immediately after init). It preserves checkouts with local files, another origin, local changes, or another commit. Recovery tests use local Git repositories and need no network.

M4's step selector jumps directly to any explanation step and pauses autoplay. The displayed step, evidence, condition and URL update together; a detail target reveals its node. The speed selector offers 1×/1.5×/2×. These controls appear only for available walkthroughs. On the focused map, Enter starts node navigation; arrows on nodes move focus, and Enter opens evidence. Arrows on the empty canvas still pan. In walkthrough view, `[` / `]` move between steps and `P` toggles playback; Space on the canvas also toggles it. Input, selection and editable controls retain native key behavior. The canvas footer contains keyboard help.

Use **Copy link to this view** or **Link** in an evidence panel to capture the current node, relationship or scenario step. The URL stores stable IDs, subject identity, detail level, speed, inspection and connection focus. Reopening never starts autoplay. A missing ID, incompatible subject or malformed state falls back to the default view with a visible notice. Ordinary document anchors still work. Local links require the same HTML file to be available; they do not upload or publish it. If clipboard access fails, a visible text field permits manual copying.

On narrow screens, **More explanation** expands the evidence sheet, and **More map** reduces it. The body scrolls while link, size, close and focus controls remain accessible. Touch controls are at least 44 pixels tall, and source details stay inside the panel. The existing reduced-motion preference keeps all conditions, directions, statuses and timed steps without camera or transfer animation.

The source caches, generated output, browser reports, and dependencies are ignored by Git. Pinned fixtures and licenses are versioned. No private repository is required.

Keep project explanations and development guides in `docs/`. Store retained verification/review records, human review worksheets, and their selected screenshots under `eval/reports/`; UI proposals and prototypes belong in `plans/design/`. The [verification index](../eval/reports/README.md) links the existing records.

## Change the contract or renderer

- Edit `scripts/build_schemas.py`, then run `python3 scripts/build_schemas.py` to regenerate both schemas.
- Edit `viewer.css`, `viewer.js`, or `flow-viewer-template.html` under `skills/code-flow/templates/`, then run `npm run fixtures` and `npm run m1:examples`. Both builders and installed `author.py build` use this same template bundle. The HTML under `plans/design/` is a design reference, not the generation entrypoint.
- After shared renderer/schema/validator changes, also run `eval:rules` for all 30 cases and the full browser suite against that new output directory.
- Source-backed rule pages use `skills/visual-primer/templates/` and a presentation layout that references reviewed rules/transitions. Rebuild both linked pages with `rules.py build-pair` after changing either skill's shared assets. The canvas and primer are different views with the same fact/evidence contract; neither uses the design prototype as its generation template.
- Rebuild fixtures with `python3 scripts/build_fixtures.py` only after reviewing the underlying sources/claims. This recreates the synthetic evidence model too.
- Update vendored Dagre from the locked dependency with `npm run vendor`.
- The two-pass example build demonstrates lazy links: sibling pages are produced first, then parent link state is refreshed.
- For M1 cases, edit `eval/m1/author_cases.py` only after rereading the corresponding source and claims, then run it followed by `npm run m1:examples`. This is a case-ledger builder, not the discovery implementation.
- M3's `eval/m3/author_cases.py` records the six source rereadings, logic candidates, layouts and independently listed rule criteria. Existing reference JSON is preserved on rerun. Deliberately update both the reference ledger and JSON after source review; never regenerate references to make a failing candidate pass. Keep the 24 behavior inputs and references intact.
- `python3 skills/code-flow/scripts/author.py doctor` verifies the installed skill's local resources. The authoring tests copy that skill alone to a temporary directory and exercise draft, evidence capture, and rendering without sibling skills or repository helper scripts.
- `python3 scripts/prepare_m1_review.py --output <new-path>` prepares another human worksheet. It refuses to replace existing reviewer answers.

## Validation limits

The Python checks validate schemas, references, source locations/hashes, confidence display, omission of unsupported claims, numerical-rule handling, serialization, and linked-page identity. They also reproduce a changed or deleted source linked to an older page and check complete evidence-file sets for dirty snapshots.

The browser suite opens all fixture pages at desktop and narrow widths in offline Chromium. It checks runtime errors, external requests, body overflow, node overlap, unrelated-node crossings, actual arrow endpoints, playback, mobile interactions, and navigation. Canvas checks cover search, detail reveal, zoom/pan, focus/back state, dark-mode persistence, denied local storage, selection visibility outside the panel, and structure selection preservation across Core/Detail changes. Endpoint checks use SVG screen transforms so they remain meaningful after zoom. The CLI fixture exercises actions and a conditional state change; map variants exercise confirmed, uncertain, and unverified regions with their own evidence panels.

M3 tests also verify retained behavior facts, rejected source/scope drift, numerical reasons/exceptions, omitted dependent figures, output collision protection and separately installed skills. Browser checks cover all six rule pages, both link directions, condition selection, state geometry, dark mode, denied storage/clipboard, inert authored HTML-shaped text and explanations with JavaScript disabled. Screenshots are under `build/qa/m3/`.

M4 browser tests use a controlled clock for each speed, mid-step speed changes, pauses and camera travel. They also exercise a synthetic 60-step explanation, real cases across all six profiles, keyboard/native-control separation, restored and invalid URLs, hidden detail nodes, mobile sheet controls, and denied clipboard/history APIs. That synthetic long explanation is an interface test, not another source-analysis evaluation case. Screenshots are under `build/qa/m4/`.

Neither suite proves that an arbitrary natural-language explanation is true. Semantic claims in the real fixtures were reviewed against pinned code by the coding agent. Human comprehension and independent fact review are still required by the later M1/M1.5 gates.

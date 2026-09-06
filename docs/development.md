# Development

M0 implements the technology-neutral data contracts, evidence/location checks, offline graph renderer, and fixture/browser tests. M1 adds the `code-flow` source-discovery skill, six profiles, draft/evidence/build helpers, and six pinned source readings. M1.5 adds source-role comparisons, regression reports, and digest-bound human review forms. M2 expands the corpus to 24 candidates and adds complex-behavior guidance, path conditions, execution-order labels, and required behavior/path checks. Independent human gates remain pending. The complete free-form rules workflow (M3) and repository-map discovery (M5) remain later milestones.

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
npm run eval:run -- --output build/eval/m2
npm test
npm run test:browser
~~~

Dependency installation and the pinned source download need internet access. Rendering and browser tests use local files. The generated HTML itself makes no external asset requests.

Open `build/examples/agent-run.html`, `framework-plugin.html`, or `utility-minimum.html` directly in a browser. All eleven examples are in the same folder. Screenshots from the browser tests are written to `build/qa/`.

The six M1 readings are in `build/m1/`; their browser screenshots go to `build/m1/qa/`. `npm run m1:examples` renders the checked-in readings with fresh evidence checks. It is not an automatic analyzer. For a new repository/question, the host follows [code-flow](../skills/code-flow/SKILL.md) and its discovery/assembly protocols. See [M1 verification](../eval/reports/m1-verification.md), [case provenance](../eval/m1/README.md), and the [human review worksheet](../eval/reports/m1-human-review.md).

The 24 candidates are rendered to `build/eval/m2/` by the command above. Runs require a new output directory to preserve earlier results and reviewer answers. For subsequent runs choose another directory and set `S2S_EVAL_DIR=build/eval/<run-name>` when running the browser suite. See the [evaluation guide](evaluation.md), [case catalog](../eval/cases.md), and [rubric](../eval/rubric.md). The original 18-case manifest remains at `eval/cases-m15.json`. These are recorded candidate replays, not independent model generation experiments.

Open `build/eval/m2/agent-parallel-tools.html` for parallel tool dispatch and result recording, or `utility-retry-budget.html` for retry/stop conditions. Choose the walkthrough view and a scenario. Each step shows its path kind, branch, prerequisite and execution-order metadata when present. Confirmed explicit dispatch/call/result-recording connections can animate within parallel groups too; node-only captions do not invent connections or worker order across parallel/unordered boundaries. Registration/dependency and uncertain connections retain static direction styling. Every step shows explanation progress. Steps without a moving transfer pulse the currently explained nodes, and parallel groups have an explicit playback label.

Offscreen targets come into view with a 360 ms eased camera movement; targets already visible keep the map still. When needed, page alignment and zoom happen within the same movement. The connection animation and 1.5-second step time start after the camera settles. Pause freezes movement and progress; resume finishes framing before continuing the remaining step time. Manual wheel scrolling or canvas panning pauses autoplay. Reduced motion keeps immediate framing, static emphasis and discrete step progress.

The M1 source fetcher can resume a failed download from an empty, unborn Git checkout with the expected origin (or one interrupted immediately after init). It preserves checkouts with local files, another origin, local changes, or another commit. Recovery tests use local Git repositories and need no network.

The source caches, generated output, browser reports, and dependencies are ignored by Git. Pinned fixtures and licenses are versioned. No private repository is required.

Keep project explanations and development guides in `docs/`. Store retained verification/review records, human review worksheets, and their selected screenshots under `eval/reports/`; UI proposals and prototypes belong in `plans/design/`. The [verification index](../eval/reports/README.md) links the existing records.

## Change the contract or renderer

- Edit `scripts/build_schemas.py`, then run `python3 scripts/build_schemas.py` to regenerate both schemas.
- Edit `viewer.css`, `viewer.js`, or `flow-viewer-template.html` under `skills/code-flow/templates/`, then run `npm run fixtures` and `npm run m1:examples`. Both builders and installed `author.py build` use this same template bundle. The HTML under `plans/design/` is a design reference, not the generation entrypoint.
- After shared renderer/schema/validator changes, also run the full 24-case evaluation and its browser checks using the same production template.
- Rebuild fixtures with `python3 scripts/build_fixtures.py` only after reviewing the underlying sources/claims. This recreates the synthetic evidence model too.
- Update vendored Dagre from the locked dependency with `npm run vendor`.
- The two-pass example build demonstrates lazy links: sibling pages are produced first, then parent link state is refreshed.
- For M1 cases, edit `eval/m1/author_cases.py` only after rereading the corresponding source and claims, then run it followed by `npm run m1:examples`. This is a case-ledger builder, not the discovery implementation.
- `python3 skills/code-flow/scripts/author.py doctor` verifies the installed skill's local resources. The authoring tests copy that skill alone to a temporary directory and exercise draft, evidence capture, and rendering without sibling skills or repository helper scripts.
- `python3 scripts/prepare_m1_review.py --output <new-path>` prepares another human worksheet. It refuses to replace existing reviewer answers.

## Validation limits

The Python checks validate schemas, references, source locations/hashes, confidence display, omission of unsupported claims, numerical-rule handling, serialization, and linked-page identity. They also reproduce a changed or deleted source linked to an older page and check complete evidence-file sets for dirty snapshots.

The browser suite opens all fixture pages at desktop and narrow widths in offline Chromium. It checks runtime errors, external requests, body overflow, node overlap, unrelated-node crossings, actual arrow endpoints, playback, mobile interactions, and navigation. Canvas checks cover search, detail reveal, zoom/pan, focus/back state, dark-mode persistence, denied local storage, selection visibility outside the panel, and structure selection preservation across Core/Detail changes. Endpoint checks use SVG screen transforms so they remain meaningful after zoom. The CLI fixture exercises actions and a conditional state change; map variants exercise confirmed, uncertain, and unverified regions with their own evidence panels.

Neither suite proves that an arbitrary natural-language explanation is true. Semantic claims in the real fixtures were reviewed against pinned code by the coding agent. Human comprehension and independent fact review are still required by the later M1/M1.5 gates.

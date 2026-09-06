# Development

M0 implements the technology-neutral data contracts, evidence/location checks, offline graph renderer, and fixture/browser tests. Agent-driven repository discovery (`code-flow` M1), the complete free-form rules workflow (M3), and repository-map discovery (M5) remain later milestones.

See the [development plan](../plans/source-to-sight-evolution-plan.md), [M0 verification record](m0-verification.md), [renderer contract](../skills/code-flow/references/renderer-contract.md), and [fixture provenance](../fixtures/manifest.md).

## Reproduce the examples

Requirements: Python 3.10+ with pip, Node.js with npm, and a local Chromium installed through Playwright for browser tests.

~~~sh
python3 -m pip install -r skills/code-flow/scripts/requirements.txt
npm ci
npx playwright install chromium
python3 scripts/fetch_fixture_sources.py
npm run fixtures
npm test
npm run test:browser
~~~

Dependency installation and the pinned source download need internet access. Rendering and browser tests use local files. The generated HTML itself makes no external asset requests.

Open `build/examples/agent-run.html`, `framework-plugin.html`, or `utility-minimum.html` directly in a browser. All eleven examples are in the same folder. Screenshots from the browser tests are written to `build/qa/`.

The source caches, generated output, browser reports, and dependencies are ignored by Git. Pinned fixtures and licenses are versioned. No private repository is required.

## Change the contract or renderer

- Edit `scripts/build_schemas.py`, then run `python3 scripts/build_schemas.py` to regenerate both schemas.
- Edit `viewer.css`, `viewer.js`, or `flow-viewer-template.html` under `skills/code-flow/templates/`, then run `npm run fixtures`.
- Rebuild fixtures with `python3 scripts/build_fixtures.py` only after reviewing the underlying sources/claims. This recreates the synthetic evidence model too.
- Update vendored Dagre from the locked dependency with `npm run vendor`.
- The two-pass example build demonstrates lazy links: sibling pages are produced first, then parent link state is refreshed.

## Validation limits

The Python checks validate schemas, references, source locations/hashes, confidence display, omission of unsupported claims, numerical-rule handling, serialization, and linked-page identity. They also reproduce a changed or deleted source linked to an older page and check complete evidence-file sets for dirty snapshots.

The browser suite opens all fixture pages at desktop and narrow widths in offline Chromium. It checks runtime errors, external requests, body overflow, node overlap, unrelated-node crossings, actual arrow endpoints, playback, mobile interactions, and navigation. The CLI fixture exercises actions and a conditional state change; map variants exercise confirmed, uncertain, and unverified regions with their own evidence panels.

Neither suite proves that an arbitrary natural-language explanation is true. Semantic claims in the real fixtures were reviewed against pinned code by the coding agent. Human comprehension and independent fact review are still required by the later M1/M1.5 gates.

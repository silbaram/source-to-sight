# M1 source-reading cases

These are six **agent-authored, source-traced readings** used to exercise the new discovery/assembly workflow. They cover six public repositories, three source languages, all six initial profiles, and mixed-profile cases. They are not the M1.5 eighteen-case golden set, a blind model evaluation, or human-approved ground truth.

| Case | Repository | Source language | Profiles | Local output |
| --- | --- | --- | --- | --- |
| `utility-strip` | chalk/strip-ansi | JavaScript | CLI/utility + library | `build/m1/utility-strip.html` |
| `plugin-hooks` | pytest-dev/pluggy | Python | Framework/plugin | `build/m1/plugin-hooks.html` |
| `agent-tool-loop` | huggingface/smolagents | Python | AI agent | `build/m1/agent-tool-loop.html` |
| `library-eviction` | hashicorp/golang-lru | Go | Library + framework/plugin | `build/m1/library-eviction.html` |
| `web-dispatch` | julienschmidt/httprouter | Go | Web + library | `build/m1/web-dispatch.html` |
| `event-receivers` | pallets-eco/blinker | Python | Data/event + library + framework/plugin | `build/m1/event-receivers.html` |

The requested test questions, selected profiles, and artifact identities are in [cases.json](cases.json). Immutable commits are in [sources.json](sources.json). The readings and rejected interpretations are recorded in [discovery.md](discovery.md). Internal [graphs](graphs/) include exact verification anchors and hashes; share rendered HTML, not those internal files, for source-body-free explanations.

## Reproduce

From the repository root after installing the development dependencies:

```sh
npm run m1:sources
npm run m1:examples
npx playwright test tests/m1.spec.cjs
```

The fetch command downloads clean detached Git checkouts to `.cache/m1-sources/`. It does not install or run the third-party projects and refuses to reset an existing changed checkout. The build command rechecks the current commit, every evidence location and hash, graph contracts, source-anchor exclusion, and profile/repository/language coverage before rendering.

`author_cases.py` reproduces the **recorded claims**. It is not an automatic analyzer: changing those claims or their source revision requires new source reading and semantic review. The utility, pluggy, and agent cases reuse M0 graph structure after rereading the same immutable source and tightening scope/claim notes. The cache, router, and event cases were newly traced for M1. Do not count these as six independent model runs.

The utility is complete for its selected local scope. The other cases preserve unresolved application callbacks, concrete plugins, handlers, model outputs, or runtime recipients. The known dispatch rule can remain confirmed even when the external node is uncertain. The event graph has no playback and makes no fixed receiver-order claim.

## Human gate

[Human review worksheet](../../docs/m1-human-review.md) has pending evidence and comprehension checks. It was generated without filling reviewer identities, verdicts, or answers. `prepare_m1_review.py --output <new-path>` creates another worksheet and refuses to overwrite existing reviewer work.

M1 requires a human sample of up to five evidence locations per type (all when fewer exist), checking both location and semantic support. A reader unfamiliar with each capability must explain purpose, inputs/results, behavior, and meaningful limits. The same reader may review multiple types. Until that occurs, the implementation and automated checks can be recorded as finished, but the M1 final gate remains pending.

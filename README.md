# Source to Sight

The technology-neutral evolution is in development. **`code-flow` now provides the M1 source-discovery skill, six composable profiles, evidence capture, and offline HTML assembly**, on the M0 graph/validation foundation. The coding agent has traced six pinned repositories across JavaScript, Python, and Go. Independent human fact and comprehension review is pending; this is not universal-support certification.

[Development plan](plans/source-to-sight-evolution-plan.md) · [Run the examples and checks](docs/development.md) · [M1 cases and provenance](eval/m1/README.md) · [M1 status](eval/reports/m1-verification.md)

M2 expands the corpus to [24 evaluation candidates](eval/cases.md), preserving the original 18 and adding one complex case per profile. It adds retry, exception, wrapper, concurrency and resource guidance, visible path conditions/order metadata, and required behavior/path checks in the [rubric](eval/rubric.md) and [comparison/review tools](docs/evaluation.md). The recorded-candidate baseline is provisional: independent human fact and comprehension review remains pending.

English | [한국어](README.ko.md)

An agent skill that turns complex topics into visual explanations for people seeing them for the first time.

The `$visual-primer` skill checks source material and authoritative references, then creates a self-contained HTML page that explains the topic with large visuals and few words. The output opens directly in a browser without a build step or separate server.

## Code behavior examples

Use `$code-flow` for a bounded capability, public API, lifecycle, or workflow. The host agent reads the source, resolves the target, reviews the claims, and creates an offline explanation; the helper scripts validate and render that authored analysis.

```text
$code-flow Explain how ToolCallingAgent uses tools and decides to stop.
$code-flow Explain when Cache.Add evicts an item and invokes its callback.
$code-flow Explain which Blinker receivers are called by Signal.send.
```

| Source reading | What the page explains | Local generated page |
| --- | --- | --- |
| strip-ansi | One-function input checking and string transformation | `build/m1/utility-strip.html` |
| pluggy | Registration versus a later hook invocation | `build/m1/plugin-hooks.html` |
| smolagents | Agent loop, model/tool boundaries, and termination | `build/m1/agent-tool-loop.html` |
| golang-lru | Eviction, state buffering, and callback after unlocking | `build/m1/library-eviction.html` |
| httprouter | Matching request dispatch to a registered handler | `build/m1/web-dispatch.html` |
| Blinker | Sender filtering and unordered receiver relationships | `build/m1/event-receivers.html` |

Run `npm run m1:sources` and `npm run m1:examples` after the [development setup](docs/development.md). The examples are agent-authored readings, not six blind model evaluations. M1's [human review worksheet](eval/reports/m1-human-review.md) remains pending. Generated pages now use the approved canvas UI: component search, structure/walkthrough views, pan/zoom, on-demand evidence panels, and a persistent dark-mode switch. The [atlas prototype](plans/design/atlas-prototype.html) remains a design reference; whole-project discovery remains M5 work.

## Concept explanation example

The following prompt creates a beginner-friendly visual guide to OAuth:

```text
$visual-primer Explain OAuth.
```

[![OAuth visual-primer output preview](assets/oauth-visual-primer-example-preview.png)](./assets/oauth-visual-primer-example.html)

[Open the OAuth visual-primer example HTML](assets/oauth-visual-primer-example.html) · If GitHub does not display the interactive page, download the file and open it in a browser.

This example includes:

- Distinct connector shapes and clear arrowheads for different relationships
- An animated Authorization Code + PKCE data flow
- An interactive, step-by-step PKCE simulation
- A decision structure that distinguishes OAuth from OpenID Connect
- Desktop and mobile rendering QA for boxes, layers, and overflow

## Installation

Install `visual-primer` with the Agent Skills CLI:

```bash
npx skills add silbaram/source-to-sight --skill visual-primer
```

For the new `code-flow` skill, install from a checkout containing this implementation:

```bash
npx skills add . --skill code-flow
```

Alternatively copy the complete `skills/code-flow` directory into your host's skill directory. Keep its scripts, references, templates, font, and licenses together. Its Python helper requires `jsonschema`; use the included `scripts/requirements.txt`. A sibling skill and Node.js are not required for rendering. Local-source and named-skill installation are described in the [Skills CLI documentation](https://github.com/vercel-labs/skills#source-formats).

If the skill does not appear in the current session after installation, start a new conversation.

## Usage

Provide the skill name, the topic to explain, and an output path:

```text
$visual-primer Explain OAuth. Save the result to docs/oauth-visual-primer-example.html.
```

You can change both the topic and the destination:

```text
$visual-primer Explain Kubernetes Pods. Save the result in the current project root.
```

Generated files follow these principles:

- Assume no prior knowledge and introduce real terms in a useful order.
- Show the central relationship with a large visual before using long prose.
- Distinguish connector direction, shape, and color according to meaning.
- Use animation or a small simulation only when time, movement, or state changes matter.
- Record authoritative sources and important unverified areas at the end of the page.
- Support UTF-8, responsive layouts, keyboard focus, and `prefers-reduced-motion`.

## Updating

Update the installed skill with:

```bash
npx skills update visual-primer
```

If the current session still has the previous version loaded, start a new conversation before using `$visual-primer` again.

## Repository structure

```text
.
├── README.md
├── README.ko.md
├── skills/code-flow/              # Source discovery, profiles, authoring, renderer
├── docs/                          # Project overview and development guide
├── plans/                         # Development plan and UI design proposals/prototypes
├── fixtures/                      # Fixed contract and renderer test inputs
├── eval/
│   ├── m1/                        # Pinned source readings and case records
│   ├── m15/                       # 18 candidates and source-based review criteria
│   ├── m2/                        # Six complex candidates and behavior/path criteria
│   ├── runs/                      # Retained provisional baseline records
│   └── reports/                   # Verification, reviews, and retained screenshots
├── skills/visual-primer/
│   ├── SKILL.md
│   └── references/
│       ├── diagram-patterns.md
│       ├── qa.md
│       └── visual-treatment.md
└── assets/
    ├── oauth-visual-primer-example.html
    └── oauth-visual-primer-example-preview.png
```

- `SKILL.md` contains the core instructions used by `$visual-primer` to research and structure an explanation.
- `references/` contains separate guidance for diagrams, visual treatment, and rendering QA.

See the [documentation index](docs/README.md) for project guidance and the [verification index](eval/reports/README.md) for development records.

The repository uses the open [Agent Skills](https://agentskills.io/) format and can be installed with the [`skills` CLI](https://github.com/vercel-labs/skills).

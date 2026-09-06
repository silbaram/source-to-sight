# Source to Sight

The technology-neutral evolution is in development. **M0 includes common graph contracts, evidence validation, and an offline workflow viewer**, with eleven fixtures including real plugin-framework, AI-agent, and JavaScript-utility sources. The repository-discovery `code-flow` skill is the next milestone.

[Development plan](plans/source-to-sight-evolution-plan.md) · [Run the examples and checks](docs/development.md) · [Fixture provenance](fixtures/manifest.md)

English | [한국어](./README.ko.md)

An agent skill that turns complex topics into visual explanations for people seeing them for the first time.

The `$visual-primer` skill checks source material and authoritative references, then creates a self-contained HTML page that explains the topic with large visuals and few words. The output opens directly in a browser without a build step or separate server.

## Example output

The following prompt creates a beginner-friendly visual guide to OAuth:

```text
$visual-primer Explain OAuth.
```

[![OAuth visual-primer output preview](./assets/oauth-visual-primer-example-preview.png)](./assets/oauth-visual-primer-example.html)

[Open the OAuth visual-primer example HTML](./assets/oauth-visual-primer-example.html) · If GitHub does not display the interactive page, download the file and open it in a browser.

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

The repository uses the open [Agent Skills](https://agentskills.io/) format and can be installed with the [`skills` CLI](https://github.com/vercel-labs/skills).

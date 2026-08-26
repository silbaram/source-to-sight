# Simple Output

English | [한국어](./README.ko.md)

A Codex plugin that turns complex topics into visual explanations for people seeing them for the first time.

The included `$e11y-teacher` skill checks source material and authoritative references, then creates a self-contained HTML page that explains the topic with large visuals and few words. The output opens directly in a browser without a build step or separate server.

## Example output

The following prompt creates a beginner-friendly visual guide to OAuth:

```text
$e11y-teacher Explain OAuth.
```

[![OAuth e11y output preview](./assets/oauth-e11y-example-preview.png)](./assets/oauth-e11y-example.html)

[Open the OAuth e11y example HTML](./assets/oauth-e11y-example.html) · If GitHub does not display the interactive page, download the file and open it in a browser.

This example includes:

- Distinct connector shapes and clear arrowheads for different relationships
- An animated Authorization Code + PKCE data flow
- An interactive, step-by-step PKCE simulation
- A decision structure that distinguishes OAuth from OpenID Connect
- Desktop and mobile rendering QA for boxes, layers, and overflow

## Installation

First, add this repository as a Codex marketplace:

```bash
codex plugin marketplace add silbaram/skill-plugin --ref main
```

Install `simple-output` from the marketplace:

```bash
codex plugin add simple-output@personal
```

Start a new conversation after installation. Plugin skills are loaded in new conversations.

## Usage

Provide the skill name, the topic to explain, and an output path:

```text
$e11y-teacher Explain OAuth. Save the result to docs/oauth-e11y-example.html.
```

You can change both the topic and the destination:

```text
$e11y-teacher Explain Kubernetes Pods. Save the result in the current project root.
```

Generated files follow these principles:

- Assume no prior knowledge and introduce real terms in a useful order.
- Show the central relationship with a large visual before using long prose.
- Distinguish connector direction, shape, and color according to meaning.
- Use animation or a small simulation only when time, movement, or state changes matter.
- Record authoritative sources and important unverified areas at the end of the page.
- Support UTF-8, responsive layouts, keyboard focus, and `prefers-reduced-motion`.

## Updating

Upgrade the registered Git marketplace and reinstall the plugin:

```bash
codex plugin marketplace upgrade personal
codex plugin add simple-output@personal
```

After updating, start a new conversation before using `$e11y-teacher` again.

## Repository structure

```text
.
├── .agents/plugins/marketplace.json
├── README.md
├── README.ko.md
├── plugins/simple-output/
│   ├── .codex-plugin/plugin.json
│   └── skills/e11y-teacher/
│       ├── SKILL.md
│       └── references/
│           ├── diagram-patterns.md
│           ├── qa.md
│           └── visual-treatment.md
└── assets/
    ├── oauth-e11y-example.html
    └── oauth-e11y-example-preview.png
```

- `.agents/plugins/marketplace.json` declares the installable plugin and its local source path.
- `.codex-plugin/plugin.json` defines the `simple-output` name, version, display metadata, and skill path.
- `SKILL.md` contains the core instructions used by `$e11y-teacher` to research and structure an explanation.
- `references/` contains separate guidance for diagrams, visual treatment, and rendering QA.

Codex plugins bundle reusable skills and external-service connections to extend ChatGPT and Codex. See the [official OpenAI Plugins documentation](https://developers.openai.com/plugins) for the concepts and component model.

# Source to Sight

Source to Sight is an Agent Skills package that turns source code into offline visual explanations. It supports project maps (`codebase-atlas`), behavior walkthroughs (`code-flow`), and rules explanations (`visual-primer`) for utilities, libraries, frameworks, AI agents, event systems, and web projects.

## Install

```text
npx skills add silbaram/source-to-sight --skill code-flow
npx skills add silbaram/source-to-sight --skill visual-primer
npx skills add silbaram/source-to-sight --skill codebase-atlas
```

Install only the skills your host needs. Each skill directory must be copied or installed as a complete directory, including its references, templates, vendored assets, and licenses.

## Use

```text
$code-flow Explain how this project's request lifecycle works.
$code-flow --explain Explain the retry and failure rules for this operation.
$codebase-atlas Explain this project's purpose, responsibilities and representative capabilities.
$visual-primer Explain OAuth.
```

The host agent reads the target source and records evidence. The skills validate that evidence and generate a self-contained HTML page that opens directly in a browser. Generated pages use the maintained templates under each skill directory and do not require a server.

## Repository layout

```text
skills/code-flow/       Source-backed behavior walkthroughs and shared canvas renderer
skills/visual-primer/   Concept and source-backed rules explanations
skills/codebase-atlas/  Project maps and links to representative capabilities
docs/                   Product guidance and distribution policy
assets/                 A browsable visual-primer example
```

See the [documentation index](docs/README.md) and [distribution file policy](docs/distribution.md). Development evaluation cases and temporary prototypes were removed from the product branch; test generated pages in a separate workspace when needed.

English | [한국어](README.ko.md)

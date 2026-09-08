# Source to Sight

Source to Sight is an Agent Skills package that turns source code into offline visual explanations. It supports project maps (`codebase-atlas`), behavior walkthroughs (`code-flow`), and rules explanations (`visual-primer`) for utilities, libraries, frameworks, AI agents, event systems, and web projects.

## Install

New here? Follow the [step-by-step quickstart](docs/quickstart.en.md) for tool checks, installation, copyable agent requests, opening your first HTML, and troubleshooting. [한국어 안내](docs/quickstart.md) is also available.

Installation needs Git and Node.js 22.20.0+ with npm/npx, following the current [Skills CLI requirement](https://github.com/vercel-labs/skills/blob/main/package.json).

```text
npx skills add silbaram/source-to-sight --global --skill '*'
```

This installs all skills for use across projects. To install only the skills your host needs, replace `--skill '*'` with specific names such as `--skill code-flow`. Each skill directory must be copied or installed as a complete directory, including its references, templates, vendored assets, and licenses.

Source-backed generation requires Python 3.10+; the validator is included, so no additional Python packages or virtual environment are needed.

## Use

```text
$code-flow Explain how this project's request lifecycle works.
$code-flow --explain Explain the retry and failure rules for this operation.
$codebase-atlas Explain this project's purpose, responsibilities and representative capabilities.
$visual-primer Explain OAuth.
```

Explore **project map → capability/behavior → a picture-first explanation of the important business rules**. The last page uses topic-specific diagrams and meaningful interactions, with the teaching approach illustrated by the [OAuth example](assets/oauth-visual-primer-example.html), rather than requiring another fixed flowchart or rule-card layout.

The host agent reads the target source, records evidence and authors the visual lesson. The builders check evidence locations, identity and links, and package offline HTML that opens directly in a browser. Maps and walkthroughs use the maintained canvas; business-rule lessons use authored visuals inside the shared navigation/evidence shell. No server is required. Request the details you need; clicking an ungenerated item copies a request rather than running analysis in the browser.

Atlas builds automatically retain reusable analysis, evidence and picture-layout JSON below the HTML directory in `_internal/<map filename without extension>/`. Without an output-location request, use `docs/atlas/<project-key>.html` and `docs/atlas/_internal/<project-key>/`. These JSON files are regeneration inputs and may contain source excerpts: exclude them from sharing and web publishing. See the [quickstart's retention and refresh instructions](docs/quickstart.en.md#keep-share-and-regenerate-your-files).

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

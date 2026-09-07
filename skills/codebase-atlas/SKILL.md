---
name: codebase-atlas
description: Explain a software repository or package through an evidence-backed offline project map of its purpose, responsibilities, relationships and representative capabilities. Use for whole-project orientation and navigation into scoped behavior or rules explanations, across utilities, libraries, frameworks, agents, data tools and web projects.
metadata:
  short-description: Project maps connected to source-grounded explanations
---

# Codebase Atlas

Help a newcomer understand what a repository does, which parts carry its responsibilities, and where to explore a representative capability. Read the actual source and documents; the supplied tools validate and render your reviewed findings rather than infer an arbitrary repository's architecture.

Use this installed directory as `ATLAS_ROOT`. Discover the installed `code-flow` companion through the host's skill catalog or an actual sibling directory. Its schemas, evidence capture and fixed canvas renderer are required. Pass `--code-flow-root` when it is installed elsewhere. Only a requested rules page needs `visual-primer`. Read their actual entrypoints when using their workflows. No target installation, execution, model API, particular host or subagent is required.

## Discover the project

Resolve the repository or package boundary and the user's question first. A monorepo may need an initial package map; a small utility may have one node and no responsibility groups. Use [discovery.md](references/discovery.md) to read the build/package declarations, public surfaces, implementation, registrations and representative usage. Combine profiles when the source has several responsibilities.

Group by observed responsibility. Directory proximity is not an invocation or dependency. Distinguish actual calls, registrations, dependencies and data relationships. Reuse the evidence confidence and location conventions from `code-flow`; do not promote a plausible grouping or unknown external implementation to a checked fact.

Describe the purpose briefly, label parts in plain language, and retain real symbols as secondary identifiers. Record included, excluded, searched and unresolved areas. Never label a bounded reading of one function as the whole project's verified architecture. Unknown behavior stays visible; small or unordered maps are valid.

## Assemble and connect

Follow [assembly.md](references/assembly.md) to create an internal atlas draft, capture evidence with the companion's `author.py capture`, and build through `scripts/atlas.py`. The shared template supplies the product's canvas, theme, responsive panels and navigation. Do not use an old HTML output or a design prototype as a template.

Each representative capability needs a resolved target, module, explicit scope, supporting locations and the responsible node. Include commands, public functions, hooks, agent workflows and data jobs when present. A catalog item is not an execution scenario. Trace a representative scenario separately before assigning an order.

Generate only the detail pages the user requests. The atlas can contain ungenerated capabilities with precise copyable requests. To create a detail, follow `code-flow` for that exact subject/scope, then rebuild the atlas with that explicit internal graph in its pages manifest. The intended drill-down is **project map → capability/behavior → picture-first explanation of its important business rules**. For that final page, follow the companion's `--explain` workflow and include the reviewed logic and visual-primer's authored layout (version 2), preserving any requested visual reference. The builder checks both directions and the source snapshot before enabling navigation. Do not regenerate every listed capability.

## Verify and deliver

Open the result on a wide and a narrow screen when a browser is available. Check the initial purpose and groups, region entry and return, search, individual evidence status, generated detail links and ungenerated commands, and return from the detail to the selected map position. Check dark mode and reduced motion. Report any visual verification not performed.

The HTML must work offline with no target code bodies, snippets, source prompts or verification anchors in visible or hidden data. Internal evidence JSON is a local authoring input, not a shareable page. Default output is `docs/atlas/<project-key>.html` in the target repository; a user path or repository output policy takes precedence. Use the user's language; current controls are Korean and English. Other languages require disclosing that UI limit.

Deliver the HTML link, actual scope and remaining uncertainty. A human comprehension review and an observed runtime trace may be claimed only when performed. Regeneration starts by rereading the source and existing metadata, not refreshing timestamps on old claims.

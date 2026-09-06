---
name: code-flow
description: Explain how a scoped software capability, command, public API, lifecycle, or agent workflow works by reading its source and producing an evidence-backed offline HTML diagram. Use for requests to trace or visualize code behavior across components, including utilities and frameworks. Whole-project maps belong to codebase-atlas; detailed rules and reasons can be delegated to an available visual-primer skill.
metadata:
  short-description: Source-grounded workflow explanations as offline HTML
---

# Code Flow

Turn a user's question about **one bounded capability** into a readable explanation with a diagram, optional walkthrough, evidence locations, and honest limits. This skill supplies the source-reading workflow and local authoring/rendering tools. The host agent performs discovery and semantic review; the scripts do not infer arbitrary program behavior.

Use the installed directory containing this file as `SKILL_ROOT`, and the target repository/package as `SOURCE_ROOT`. They need not share a checkout. File search, file reading, local command execution, and preferably a browser are sufficient. No specific model, provider, subagent, language server, target-project installation, or server is required. The phases below can run sequentially in one context.

## Resolve the question

Read the relevant package/build manifest, public surface, and examples or tests. Resolve natural language, a symbol, `file:line`, command, route, event, or lifecycle to concrete locations and an explicit scope. Multiple entrypoints can belong to one lifecycle. Distinct plausible targets require a concise clarification with their locations; continue independent reading while waiting. Never silently choose between unrelated functions with the same name.

Use [discovery-protocol.md](references/discovery-protocol.md) for the source trace. Select only the relevant profiles; combine them when the capability crosses boundaries:

| Observed responsibility | Read |
| --- | --- |
| Command, options, transformation, small standalone function | [CLI and utility](references/profiles/cli-utility.md) |
| Public library/SDK API, resource or error contract | [Library and SDK](references/profiles/library-sdk.md) |
| Registration, extension point, host-to-plugin control | [Framework and plugin](references/profiles/framework-plugin.md) |
| Agent loop, model/tool boundary, memory, harness lifecycle | [AI agent](references/profiles/ai-agent.md) |
| Producer/consumer, signal, task or data graph | [Data and event](references/profiles/data-event.md) |
| HTTP or UI event handling | [Web](references/profiles/web.md) |

A whole-repository request remains a map request. If `codebase-atlas` is installed, inspect its actual entrypoint before using it. If unavailable, report that map generation is not installed and provide the source-grounded scope/candidate list already found; do not present this behavior viewer or the design prototype as a complete repository map. A clearly requested capability can still be explained with this skill alone.

## Trace, explain, assemble

1. **Trace facts.** Record the selected target, includes/excludes, files searched, node/relationship candidates, conditions, evidence, and unresolved alternatives. Read callsites and dispatch rules, not just declarations. Keep runtime choices unresolved when source cannot determine them.
   For branches, retries, wrappers, concurrent work, resource lifetimes, or multiple packages/profiles, read [complex-behavior.md](references/complex-behavior.md). It defines which conditions, ordering boundaries, and failure effects to preserve in the existing graph.
2. **Explain the trace.** Follow [explainer-guide.md](references/explainer-guide.md). A useful one-node explanation or unordered relationship graph is a normal result. Add scenarios only when order is meaningful. Do not introduce facts while writing captions.
3. **Assemble and review.** Follow [assembly-protocol.md](references/assembly-protocol.md) and the [renderer contract](references/renderer-contract.md). Use `scripts/author.py` to create a draft, capture exact evidence, check the installed bundle, and build. Reread evidence against every claim before marking it supported. The location/hash checks are separate from this semantic review.
4. **Inspect the result.** Open the generated HTML when a browser is available. Check text, relationships, uncertainty, the structure/walkthrough switch, on-demand evidence, dark mode, and a narrow screen. If no browser is available, report that visual verification was not performed; do not invent a successful check.

Never embed target source bodies, extracted source lines, original prompts stored in the target, or verification anchors in output HTML, including hidden data. Identifiers and file/line locations are allowed. Internal IR with anchors belongs in a local working directory and is not the shareable artifact.

## Output and refresh

Use the user's language, preserving source identifiers. The currently validated viewer controls are Korean and English; disclose the UI-localization limit for other requested languages. Create separate pages only for languages explicitly requested.

Use the bundled `templates/flow-viewer-template.html`, `viewer.css`, and `viewer.js` through `author.py build`. They provide the approved canvas UI; do not copy an old generated HTML or the prototype sample as a new output.

Default output: `docs/flows/<subject-key>.html` under the source project. Derive the key from module, resolved target, and scope; the helper adds a stable digest so identical names in different scopes do not collide. A user-specified destination takes precedence. For multiple languages add language suffixes. Inspect existing HTML metadata before reusing a destination for a different subject.

Deliver the HTML link, its exact scope, and material unresolved parts. Do not claim entire-project coverage or universal support from one successful case. Runtime traces and human review must not be claimed unless they actually occurred.

For regeneration, read `s2s.py inspect <existing.html>`, return to the current source, and rerun discovery/review. Do not merely change hashes or timestamps on stale assertions. The offline page does not execute a generation command when clicked.

For a requested rules explanation (`--explain` in a skill prompt), discover the installed `visual-primer/SKILL.md`, preserve the subject/scope, and reread its rule guidance. If absent, finish the authorized behavior page and state that the additional rules skill is unavailable. Locate sibling skills through the host's skill catalog or an actual sibling directory, never a hardcoded user path. Link only generated, identity-checked pages; otherwise provide the precise generation request. Installation and initial rendering work with `code-flow` alone.

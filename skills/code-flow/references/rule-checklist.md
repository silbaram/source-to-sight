# Rules and reasons

Use this checklist for `--explain` and questions about why the selected capability follows a particular condition, priority or failure path. Keep its existing subject, scope, nodes, relationships and state transitions. New rules extend `rules[]`; they do not create another interpretation of the behavior graph.

## Discover the contract

Read the decision and its caller/configuration together. Follow the applicable questions, not a fixed number of rules:

| Responsibility | Questions that change the result |
| --- | --- |
| Utility/command | Which inputs are accepted? Do defaults come from the helper or caller? What counts as a total attempt versus a retry? |
| Library/SDK | What does the public API promise? Which mutation happens before callbacks, cleanup or errors? What is outside the input contract? |
| Framework/plugin | Which implementation wins? Does a result stop dispatch or still unwind wrappers? Can an extension replace a result or exception? |
| Agent/harness | Which per-run settings override defaults? What is one counted step? Which failures continue, terminate or trigger fallback? |
| Data/event | What controls delivery, ordering and registration lifetime? Which effects remain after a recipient fails? |
| Web | What precedes fallback handling? Which method/path/settings select a branch? Do custom handlers change the default result? |

For each rule record its condition, observable outcome, related nodes, and evidence. Put the implementation reason in optional `rationale`, and material exceptions or exclusions in optional `exceptions`. These fields share the rule's semantic review and evidence. A rationale explains the checked mechanism; do not invent the developer's motivation or a performance/security benefit absent from the source.

Where applicable, read permission/ownership gates and resource acquisition, cleanup or reuse together. Identify who can perform the operation, which denied condition stops it, and what remains after failure. Do not add an access-control rule or lifecycle phase without evidence that it exists in the selected scope.

Check units, inclusive bounds, defaults, configuration precedence and written-out quantities. Mark any quantitative rule `numeric: true`, including numbers that appear only in its rationale or exceptions. Unverified numerical rules are omitted entirely. Non-numerical uncertainty remains explicit; a visual must not make it appear settled.

## Build the paired explanation

Start from the **internal behavior JSON**, not metadata extracted from an old HTML. If only HTML remains, inspect its regeneration information and recover the evidence from current source. Render JSON deliberately lacks verification anchors and is not an authoring input.

`author.py explain behavior.json --source-root <source> --output <new-rules.json>` creates a draft with the same facts and a pending rule review. Reread the actual source, add or enrich rules, record the search and limits, and update support status only after review. Existing behavior facts and the core meaning of its rules remain unchanged; correct the behavior input first if discovery reveals an error.

For the rules page, locate the available `visual-primer` skill and read its source-rules guide and visual-story instructions. Use its authored layout by default: make the key business decision understandable through a large topic-specific picture, short captions and useful reader-controlled examples. Condition/result cards remain a compact reference option, not the required final drill-down. Bind each scene to its reviewed rules and any additional nodes, edges, steps or state transitions that it illustrates. Use real relationships for arrows and source-supported outcomes for interactions; adjacent rules alone do not imply execution order. A missing companion does not prevent `code-flow` from producing the authorized behavior page.

Build both pages from the same reviewed inputs. The pair builder checks inherited facts, subject, scope, language, captured source and output identities before replacing files. It resolves both links against the newly prepared pages, so a stale prior page cannot certify the new pair. Offline links navigate or copy a generation request; they do not execute analysis.

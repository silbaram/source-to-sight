# Source discovery

Read the source at the requested checkout. The output of discovery is a claim ledger and scoped graph candidates, not a diagram invented from the project's framework name.

## Resolve scope before drawing

- Begin with the relevant manifest, exports/entrypoints, and examples/tests. Search with the host's file tools; `rg --files` and symbol/reference searches are useful local equivalents.
- Record the user's question, candidate locations, selected symbol/configuration, and why it answers the question. A command may resolve through registration; a lifecycle may have several entrypoints; independent APIs may have no order.
- Include the preconditions that make the chosen path meaningful. Specify completion/return boundaries and excluded features. “A registered callback is present” and “the callback always runs” are different claims.
- When the scope is ambiguous, retain candidates with file/line locations and ask the user to disambiguate. If producing a partial page helps, retain the ambiguity in warnings and scope. Do not label an arbitrary candidate complete.
- Keep a short local trace record: question, selected profiles, actual search terms, files read, chosen/rejected candidates, claims and their evidence, unresolved questions, next attempts. Count only reads actually performed.

## Follow relationship semantics

| Relationship | Required source reading |
| --- | --- |
| Direct invocation | Caller expression and target resolution; include aliases/overloads that matter |
| Data transfer | Actual value binding/return/argument or serialization boundary |
| Registration | Registration storage or configuration plus the registration contract |
| Dynamic dispatch | Dispatch selection rule and candidate implementations; concrete runtime selection may remain unknown |
| State transition | State owner, write, guarding condition, initialization/reset if necessary |
| Dependency | Import/configuration or construction establishes dependency, not execution order |
| Event delivery | Producer, receiver registry/filter, dispatch policy and failure behavior |
| External boundary | The local call/configuration and its contract; not an invented implementation of the external service |

Do not create call edges from directory adjacency, matching names, type annotations alone, or documentation examples that bypass the actual implementation. Test code helps establish usage and contracts; production callsites still need implementation evidence. If installed dependency source is absent, stop at the documented local boundary and say what is missing.

For callbacks, framework inversion, agents, and events, distinguish the **known invocation rule** from the **unknown concrete recipient/output**. A dispatch rule may be confirmed while its concrete target remains uncertain. Mark individual claims accordingly rather than making every related node either certain or uncertain.

## Claim ledger and reread

For each node, action, edge, transition, scenario step, and rule, record:

- A plain-language claim and its intended scope/path.
- Evidence file, symbol/key, start/end lines, one exact anchor line, and file SHA-256.
- `confidence`: `exact` for a direct reading, `resolved` for a target established through explicit resolution, `inferred` for a hypothesis.
- `supportStatus`: `supported`, `uncertain`, or `unsupported`, with a **claim-specific** verification note describing the condition or resolution actually checked.

`author.py capture` captures location and hash; it does not create or endorse the claim. Reopen the selected ranges and nearby control flow for the semantic pass. A matching signature does not establish a call, condition, ordering guarantee, or state change. Use multiple evidence IDs when caller and callee or registration and dispatch jointly support the explanation.

Context-only actors can aid orientation but have no evidence badge, verified actions, or invented factual claims. Every factual edge still needs evidence.

## Stop with an honest boundary

The stopping condition is enough evidence to answer the agreed scope, not finding a fixed node count. If exploration limits, missing files, generated code, runtime configuration, or ambiguity prevent that, record the searched areas, unresolved questions, candidates, and concrete next reads. Keep supported parts and set `partial`; use `insufficient` if implementation evidence cannot support a useful graph. Do not omit difficult parts and call the original wider scope complete.

Do not run the target project merely to infer behavior. This source-explanation workflow does not require dependency installation or runtime execution. A user-authorized runtime investigation is a separate evidence source and must be labeled as such.

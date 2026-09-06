# Complex behavior

Use this reference when a scoped capability has alternatives, retries, wrappers, concurrent work, shared state, or package boundaries. Keep the same node/relationship model and select profiles by actual responsibility. A utility inside an agent repository can still be a utility explanation.

## Read the boundaries that change the result

| Source pattern | Resolve before writing |
| --- | --- |
| Early return or failure | Exact guard, branch priority, what has already changed, returned/raised result, skipped later work |
| Retry or loop | Effective configuration and overrides, initial counter, comparison and increment, total attempts versus retries, retriable failures, backoff update before/after sleep, success/stop path |
| Wrapper or callback | Registration versus invocation, runtime selection, setup and unwind order, short circuit, exception propagation/replacement/suppression |
| Async or parallel | Submission, actual await/worker policy, partial order, collection versus presentation order, what one failure skips, already-running side effects |
| State or resource | Owner, initialization, exact write/guard, lock or context boundary, cleanup on success/error, callback position relative to release |
| Multiple packages/profiles | Real callsite and receiver contract at each boundary; distinguish configuration, dispatch, conversion and implementation |

Read the guard and its surrounding control flow, not just a helper name or a docstring. If a default says three attempts, do not describe three retries. An agent's next decision after an error does not prove the same tool is retried. Catching a broad exception does not guarantee continuation if the predicate, callback, logger or cleanup can itself raise. State precisely which effects are included in the scope.

`async` does not imply parallel execution. A loop that awaits each receiver is sequential even when receiver selection order is unspecified. Completion order, input order and sorted output order are separate facts. Failure after some work completes does not roll back that work. Do not promise cancellation, atomicity, idempotency, or cleanup on every path without reading the corresponding implementation.

For wrappers, inspect the actual implementation sequence and unwind stack; do not invent an order for unnamed application plugins. For locks and resources, check whether release is in a finally/defer/context manager or only on the normal path. Treat external callbacks as boundaries while keeping the local invocation rule confirmed when supported.

## Express the result

- Use separate `scenarios` for meaningful normal, alternate, error, retry, or lifecycle paths. Their `kind` and each step's `branch` are visible labels, not runtime observations.
- Put the exact path prerequisite in the claimed step's optional `condition`; write a caption explaining the effect. Both share that step's evidence and semantic reread. Use `returns` for a real return/raised result, not a fabricated return edge.
- Use optional step `execution: sequential | parallel | unordered` only when the source supports it. `parallel` describes a concurrent group, not its internal sequence. `unordered` means concrete recipient order is unspecified; the caption must still say whether the dispatcher awaits recipients one at a time.
- Group concurrent workers/unknown recipients by their actual dispatch responsibility. Do not draw worker A → worker B merely to walk the reader through them. Across a parallel/unordered boundary, use a step `edgeId` for an evidenced entry/dispatch, a call within each worker, or a join/result-recording dependency. Include evidence for both the named relationship and the caption. The viewer can animate that checked relationship without implying worker order or timing. Node-only parallel/unordered steps remain nondirectional; adjacent captions never infer transfers across that boundary. Use an evidenced loop edge to explain the next iteration, not an invented return from an output artifact.
- Repeated walkthrough steps explain the loop once; their count is not a promised iteration count. Preserve the effective budget and stopping condition in `rules` and the corresponding step conditions.
- Record state writes/releases in `stateTransitions`, with the owner and `trigger`; put helper operations in that owner's `actions` when no independent component is needed. Never split one function into invented services to enlarge the graph.
- Across files in the same snapshot, attach all necessary evidence to the relationship. Across repositories whose exact sources are unavailable, keep the local call and an unresolved boundary. Do not claim a second snapshot was validated by the first repository's hash.

## Review the changed claim

Reread every branch caption, numeric rule, ordering assertion and state transition. Check normal and failure paths independently, including cleanup and callbacks that can override a result. Record unresolved choices in both `analysis` and user-visible limits. Missing concrete implementations can produce a useful `partial` result.

The evaluation corpus checks required source roles, paths and behavioral claims; it cannot establish arbitrary prose truth. Preserve human review as pending until a person actually checks facts and comprehension. Never repair a failing case by deleting its required condition or relabeling an unknown recipient confirmed.

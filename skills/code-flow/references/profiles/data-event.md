# Data and event discovery

Find producers, job/task definitions, transformations, receiver registration, filtering/selection, joins, persistence, and acknowledgement/checkpoint code relevant to the requested scope. Distinguish a data dependency graph from a scheduler's runtime ordering.

An event name alone does not establish delivery. Trace subscription storage, sender/topic filters, dispatch, and the local failure/return behavior. Do not infer delivery guarantees, transactions, retries, or persistence from framework naming.

For fan-out, inspect ordering and exception behavior before saying all consumers finish. For iteration, separate a declared collection from the runtime count. For a pipeline, show split/join constraints without imposing an order on independent branches.

Inspect await placement: awaiting each receiver inside a loop is different from scheduling a group. Record whether failure skips remaining recipients and whether a temporary subscription is disconnected or a previous registration state is actually restored.

Example reading: Blinker `Signal.connect`, `receivers_for`, and `send` establish registration, sender filtering/weak-reference cleanup, and synchronous receiver calls. Check muted signals, async receiver adaptation, and exception propagation. An unspecified receiver order must remain unspecified; this in-process signal is not a durable broker or a distributed delivery guarantee.

Combine library/SDK for a public signal API and framework/plugin for application-supplied receivers. These mixed profiles still produce the same graph contract.

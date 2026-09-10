# Explain only the traced facts

Start with what the capability is for, what enters, what comes out, and one limit that changes how the reader should interpret it. Use the user's language. Keep real symbol names as secondary labels so readers can find the implementation without having to understand the language first.

For a node, write a short role label and one to three sentences explaining its responsibility in this scope. Keep intermediate helpers as actions on their actual owner when that preserves the relationships. Independent public functions do not need an artificial entrypoint, database, pipeline, or return node.

Describe edge labels with concrete verbs: registers, requests, forwards, records, reads, returns. The label must agree with its semantic type. Registration does not mean a plugin has executed; dependency does not mean execution order; a callback's existence does not guarantee invocation.

Scenarios are optional. Each caption must have its own semantic reread, even when it reuses a node's evidence. A caption such as “always calls every receiver” is a stronger claim than “dispatches to matching receivers.” Preserve alternate/error/retry/stop conditions. A repeated node in a walkthrough is an explanation of the loop, not a recorded runtime trace or a fixed iteration count.

For parallel work, label the fork/join and absence of a guaranteed internal order; a linear walkthrough is a teaching sequence, not proof of serialization. Mark the claimed group step's `execution` as `parallel` or `unordered` so playback cannot imply a serial transfer. Put a branch prerequisite in `condition` and its effect in the caption. See [complex behavior](complex-behavior.md) for retry, cleanup and mixed-profile contracts. For unordered APIs or registration-only views without a meaningful surrounding lifecycle, leave scenarios empty.

Useful limits name the boundary: nonstreaming model path; registered implementations selected at runtime; normal method/path match with redirect behavior excluded. Avoid empty boilerplate such as “details may vary.” Do not introduce numerical rules, latency, scores, token use, runtime outputs, or undocumented guarantees to make the page look complete.

Prefer one precise sentence to a list of framework/class names. For example, describe “the registry stores the handler; a later request looks it up” and show the actual identifiers below it. Verify both registration and lookup before adding that sentence.

The existing viewer handles one-node, dependency, branch, loop, state, and partial-result graphs. It does not require every explanation to fill every optional panel. The installed viewer uses the approved canvas design, including search, structure/walkthrough views, on-demand evidence panels, and dark mode. Its graph comes only from the reviewed IR. Shared visual design does not expand a scoped behavior explanation into a whole-project map.

## Teach the data flow to a new maintainer

Keep the picture central. Use concrete payload labels on data edges so a reader
can see what enters a processing step and what it sends onward. Preserve failure
conditions and state changes, not only the successful path. A node's inspector
shows recorded incoming/outgoing data, its decision rules, and an action into the
matching picture lesson. Keep implementation identifiers, evidence and explicitly
linked test locations in maintenance disclosures. Missing test mappings are gaps,
not evidence that no tests exist. Pair important rules with authored visual-primer
scenes rather than asking the reader to interpret code or dense rule lists.

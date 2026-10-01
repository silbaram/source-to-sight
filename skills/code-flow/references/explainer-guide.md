# Explain only the traced facts

Start with what the capability is for, what enters, what comes out, and one limit that changes how the reader should interpret it. Use the user's language and plain-language labels. Keep real symbol names in search/navigation metadata; implementation pointers show file and line locations without a separate code-name label.

For a node, write a short role label and one to three sentences explaining its responsibility in this scope. Keep intermediate helpers as actions on their actual owner when that preserves the relationships. Independent public functions do not need an artificial entrypoint, database, pipeline, or return node.

For newly authored processing nodes, record an `operation` when the traced source
establishes what the node does. Its `kind` describes the action, optional
`targetKind` describes the resource, and optional `target` names the affected
business object or destination in plain language. These fields share the node's
evidence and review status. Keep the node's title concrete: "Save the order" and
"Request payment approval" explain more than "Process data" and "Call service".
Do not turn identifiers, filenames, framework names or familiar label words into
automatic classifications. If the trace does not establish an operation, omit it.

| `operation.kind` | Meaning to verify |
| --- | --- |
| `receive` | Accept input, an event or a request at this boundary |
| `validate` | Check input or an invariant before processing continues |
| `decide` | Choose a branch, result or eligible destination |
| `transform` | Compute, assemble or change the representation of data |
| `read` | Retrieve existing data from the named source |
| `write` | Save or update data in the named destination |
| `request` | Invoke an API or service to perform work |
| `publish` | Emit or enqueue a message or event |
| `wait` | Wait for an event, response or completion condition |
| `respond` | Return a result to a caller or user |
| `stop` | End processing, reject work or stop after a failure |

Resource types are `database`, `file`, `api`, `queue`, `cache`, and `service`.
For example, a reviewed database write uses `kind: write`, `targetKind: database`
and a target such as "Order record"; writing a generated HTML document uses
`kind: write`, `targetKind: file`. An API request uses `kind: request` and
`targetKind: api`, naming the provider only if the evidence identifies it.
API access alone does not establish a third-party service, a remote deployment,
successful delivery or a committed transaction. Use `target` to clarify a
verified boundary without exposing source expressions, table identifiers or URLs
copied from the implementation.

Choose the dominant operation for a single responsibility. Separate a database
write from an API request when they have distinct data, conditions or failure
effects that matter to this scope; keep incidental helpers as actions. Do not
invent storage, service or return nodes to fill the vocabulary. Context-only
actors cannot carry an operation because they have no reviewed behavior claim.

Describe edge labels with concrete verbs: registers, requests, forwards, records, reads, returns. The label must agree with its semantic type. Registration does not mean a plugin has executed; dependency does not mean execution order; a callback's existence does not guarantee invocation.

Scenarios are optional. Each caption must have its own semantic reread, even when it reuses a node's evidence. A caption such as “always calls every receiver” is a stronger claim than “dispatches to matching receivers.” Preserve alternate/error/retry/stop conditions. A repeated node in a walkthrough is an explanation of the loop, not a recorded runtime trace or a fixed iteration count.

For parallel work, label the fork/join and absence of a guaranteed internal order; a linear walkthrough is a teaching sequence, not proof of serialization. Mark the claimed group step's `execution` as `parallel` or `unordered` so playback cannot imply a serial transfer. Put a branch prerequisite in `condition` and its effect in the caption. See [complex behavior](complex-behavior.md) for retry, cleanup and mixed-profile contracts. For unordered APIs or registration-only views without a meaningful surrounding lifecycle, leave scenarios empty.

Useful limits name the boundary: nonstreaming model path; registered implementations selected at runtime; normal method/path match with redirect behavior excluded. Avoid empty boilerplate such as “details may vary.” Do not introduce numerical rules, latency, scores, token use, runtime outputs, or undocumented guarantees to make the page look complete.

Prefer one precise sentence to a list of framework/class names. For example, describe “the registry stores the handler; a later request looks it up” and provide the supporting file/line locations on demand. Verify both registration and lookup before adding that sentence.

The existing viewer handles one-node, dependency, branch, loop, state, and partial-result graphs. It does not require every explanation to fill every optional panel. The installed viewer uses the approved canvas design, including search, structure/walkthrough views, on-demand evidence panels, and dark mode. Its graph comes only from the reviewed IR. Shared visual design does not expand a scoped behavior explanation into a whole-project map.

The behavior structure view starts with readable processing cards, grouped by
the recorded responsibility areas, with no arrows. Operation icons and explicit
action/resource labels distinguish saving, requesting, validating and other work.
Card order and group membership do not establish execution order. The connection
view can reveal the recorded topology; following a scenario uses only its reviewed
steps and preserves branches, parallel work and uncertainty.

## Teach the data flow to a new maintainer

Keep the picture central. Use concrete payload labels on data edges so a reader
can see what enters a processing step and what it sends onward. Preserve failure
conditions and state changes, not only the successful path. A node's inspector
shows recorded incoming/outgoing data, its decision rules, and an action into the
matching picture lesson. Keep implementation locations, verification status and
explicitly linked test locations in maintenance disclosures. Missing test mappings are gaps,
not evidence that no tests exist. Pair important rules with authored visual-primer
scenes rather than asking the reader to interpret code or dense rule lists.

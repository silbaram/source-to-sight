# A visual explanation for the next maintainer

Use this contract when authoring or improving the three-layer journey. The reader
is new to this project. They need to locate a change, understand what it affects,
and know which implementation and tests to inspect without first reading code.

## Project map: orient before selecting

Lead with the project's purpose in one sentence and short input/result labels.
Make the responsibility map the dominant surface. Name the work each component
does, enclose related responsibilities, and label observed connections with what
is requested, transferred or used. Explain each group's shared responsibility in
a short caption. Containment alone never asserts order, data transfer or mandatory
composition. Keep shared infrastructure and supporting documentation/tests
recognizable as their actual roles, rather than pretending they are all user-facing
features. Unconnected means no connection is recorded, not proven independence.

A component with one generated capability opens that exact behavior directly.
Multiple capabilities require a choice; missing detail exposes reviewed context
and a precise generation request. Keep the searchable catalog and physical tree
available on demand. Symbols, paths, verification notes and generation controls
must not compete with the first picture. Material uncertainty stays discoverable
before the reader acts; do not conceal synthetic provenance or unsupported claims.

## Behavior: follow data and decisions

Stay within the selected capability's target and scope. Start with the input and
observable result, then draw meaningful processing steps. A node names a
responsibility; an edge names the actual transferred data, requested action or
dependency. For a data edge, label the payload in plain language, including a
transformation or state when relevant. Use the existing edge types accurately:
dependency/registration is not runtime data transfer.

Record branch conditions, failures, retries, side effects and state transitions
where the source establishes them. Scenarios describe reviewed paths, including
their actual ordering boundaries. Never turn a capability catalog or a series of
manual authoring operations into an automatic call chain. Put optional/manual
steps in their explicit context. Preserve parallel and unordered segments.

For each important node, identify the decision rules, implementation locations,
and explicitly linked test evidence. Other observed connections help a maintainer
inspect collaborators; they are not exhaustive change-impact analysis. If a test
mapping or an explanation is missing, say so instead of inventing it. Recorded
tests are source locations, not a claim that those tests passed.

## Node lesson: explain the rule in pictures

Bind a node's rules through `rules[].nodeIds`. Use the existing paired logic page
and version 2 authored scenes. The viewer passes the selected node and behavior
location to the lesson; it shows matching rule pictures and can reveal all rules.
Returning to behavior restores the selected node; returning to the map preserves
the selected capability. A missing or withheld picture remains an explicit gap.

Choose geometry that explains the actual rule: composition for a calculation,
before/after for a state change, boundaries for access, matching documents for an
identity check, or a concrete success/failure comparison. Keep condition, result
and decision-critical exceptions legible. Add a short reason only when supported.
Do not substitute another generic workflow chart, prose-heavy modal, or decorative
icons for the rule explanation. Never include source bodies or guessed policies.

## Review the information as well as the UI

Trace a newcomer journey from an actual component through data flow to one rule
picture and back. Verify labels against source, each link against subject/scope,
and maintenance pointers against actual files/tests. On desktop and a narrow
screen, check that the picture precedes dense metadata, labels remain readable,
keyboard controls work, and returning preserves context. Check both themes,
offline use, uncertainty and absent data. Successful rendering and automation do
not establish human comprehension or complete project coverage.

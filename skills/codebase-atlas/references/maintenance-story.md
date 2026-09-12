# A visual explanation for the next maintainer

Use this contract when authoring or improving the three-layer journey. The reader
is new to this project. They need to locate a change, understand what it affects,
and know which implementation and tests to inspect without first reading code.

Keep captions about the target project's work and results. Do not add paragraphs
explaining how to read or operate the generated HTML. Clear control labels,
interactive styling and location indicators carry navigation. Preserve analysis
limits and missing-data states. For a documentation tool, its actual generation
or viewer behavior still belongs in the relevant feature explanation.

## Project map: composition, then feature groups

The grouping unit is a real product capability or task: payment, order lookup,
account creation, report generation, or another actual feature of this project.
Each group crosses the components that implement it. Do not group all controllers,
all services, all databases, or the stages of reading this documentation as the
main feature list.

At the top, draw the project's actual composition: applications, packages,
execution environments, storage and external services, with short roles and
recorded connections. Use reviewed atlas nodes/regions/edges selected through
`composition.regionIds` and `composition.edgeIds`. A library or skill package has
its own topology; never invent a web server, database or provider to fit a template.

Below it, list capability groups directly on the same page. Above each group's
processing boxes, place its actual incoming request/data → produced result as a
compact full-width header. Then show the components responsible for that feature,
with a short role on each box and labels on the data/request passing between them.
For a web payment feature, source evidence might establish controller → service →
DB write/read; these are roles inside the payment group, not separate feature groups.
Shared components can appear in several features, but each preview must use that
feature's exact subject/scope and checked graph. The builder supplies public
`featureDetails` from the linked behavior documents; do not handwrite another
unverified graph or infer a trace from a shared owner.

Keep the request/result and a few responsibility boxes visible at reading size.
In each exact behavior graph, author evidence-backed `regions` with `role: primary`
as the feature's summary groups. Give each a short responsibility label and one
sentence about its work; `nodeIds` maps it to the detailed processing nodes. Primary
groups must be disjoint. Aim for two to four meaningful roles when the code supports
that division; a small feature may need only one. Do not invent layers or simply
rename every detailed node. Summaries and full processing are different levels.

The overview uses only recorded edges crossing these groups. Internal checks,
error branches and scenario controls belong in the behavior detail. Preserve
parallel relationships and return/dependency connections without making them a
serial path. A missing reviewed summary shows the request/result and detail link,
not an automatically copied detailed graph.

Selecting a summary box opens its detailed processing list and highlights the
members in the behavior page. Selecting a processing node then exposes its data,
conditions and rule pictures. Returning restores the feature heading. Search,
package paths, source evidence and the comprehensive structural graph remain
secondary inspection tools. Important uncertainty and missing data stay visible.
Feature order is page order, never a claim that all features execute in sequence.

Legacy region interfaces and nested area selection remain readable for retained
inputs without `composition`. New project authoring uses composition plus visible
feature groups. For large projects choose a bounded project/package scope and
keep feature navigation available; do not shrink the entire repository graph.

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

Trace a newcomer journey from a visible feature group through one processing box to its rule
picture and back. Verify labels against source, each link against subject/scope,
and maintenance pointers against actual files/tests. On desktop and a narrow
screen, check that the picture precedes dense metadata, labels remain readable,
keyboard controls work, and returning preserves context. Check both themes,
offline use, uncertainty and absent data. Successful rendering and automation do
not establish human comprehension or complete project coverage.

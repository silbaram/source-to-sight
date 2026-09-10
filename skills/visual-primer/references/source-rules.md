# Source-backed rule pages

Use this mode for the final drill-down: **project map → capability/behavior → a picture-first lesson about the important business rules**. Keep visual-primer's topic-specific art direction and teaching techniques here, too. A source-backed explanation should not lose those capabilities just because it is linked from a map. General concept explainers keep their standalone HTML workflow.

Read `code-flow/references/rule-checklist.md` in the actual companion installation. Keep an internal behavior JSON and a reviewed logic JSON with the same subject, scope, nodes, edges, scenarios and state transitions. The logic input can enrich existing rules with a source-backed rationale and exceptions, and add rules/evidence. It cannot silently alter the behavior's facts. Use the companion's `author.py explain` for a draft; it deliberately does not endorse the rules.

Node-specific navigation uses the existing `rules[].nodeIds` and rendered scene
rule bindings. A behavior link may carry `s2s-node` and `s2s-behavior`; the shell
focuses matching scenes, offers all rules, and restores the selected behavior
location using the checked local link. Bind rules to their actual processing
nodes so unrelated rules do not appear in a selected node's lesson. Missing or
withheld scenes must not be replaced with invented explanatory content.

## Compose the lesson

Use an **authored layout, version 2**, following [authored-layout.md](authored-layout.md) and [its schema](authored-layout.schema.json). Design the lesson with the main skill's visual-story instructions: a dominant picture, short explanations, topic-specific geometry, and a small interaction when it makes the real decision clearer. A supplied explainer such as the OAuth example can guide hierarchy, connected paths and step controls; do not copy its OAuth facts or turn its exact layout into a universal template.

Each scene binds its HTML/SVG, CSS and optional script to reviewed `ruleIds` and any additional `claimIds` it uses. Those bindings let the builder withhold a scene and all its assets when its source support fails. The builder supplies the shared navigation, evidence disclosure, theme, offline assets, scope and metadata. The host still reviews the meaning of every label, arrow and interactive outcome against the source; schema validation cannot perform that review.

Keep exact conditions, reasons and exceptions in the reviewed rules, with concise accurate labels in the picture. Do not introduce business policy, numerical values, timing, or execution order only in markup or JavaScript. Place detailed reference material after the picture or inside evidence disclosure. Defaulting to a list of condition/result cards does not satisfy a picture-first explanation request.

### Compatibility: compact rule reference

Existing version 1 layouts remain supported through [rule-layout.schema.json](rule-layout.schema.json). Use this mode for old inputs or when the user explicitly wants a compact rules reference. Each section has an ID, a question-like title, `kind`, and `ruleIds`:

- `comparison`: two or more alternatives with the same condition/result geometry. A reader can select a case; all cases remain available without JavaScript.
- `conditions`: one or more condition → outcome pictures. There is no execution edge between different rules.
- `states`: existing `transitionIds` show a before/after state and its real trigger, with the selected rules explaining the contract.

Use headings to organize existing facts; put factual values, reasons and exceptions in the reviewed rules, not layout titles. Every selected rule needs a rationale. Every new rule must appear in a figure. Preserve all conditions in the visible picture; do not replace them with an identifier or an incomplete short label. When a rule or transition is omitted during verification, the whole dependent figure is withheld with a notice.

These legacy figures are not a timed workflow. Do not fall back to version 1 silently when an authored scene fails validation; fix the scene or report the limitation.

## Build and inspect

Set `PRIMER_ROOT` to the actual installed `visual-primer` folder and run from any directory. A sibling `code-flow` installation is discovered by its real path. Supply `--code-flow-root` if the two skills are installed separately.

~~~sh
python3 "$PRIMER_ROOT/scripts/rules.py" build-pair \
  --behavior-input behavior.json --input reviewed-rules.json --layout layout.json \
  --source-root /path/to/source \
  --behavior-output output/behavior.html --output output/rules.html
~~~

Inputs must remain separate from all HTML/render-JSON outputs. Builds validate and render both pages before writing either page; each file replacement is atomic. A write failure can require rerunning the pair. Old pages with another subject, scope, repository or language are not overwritten. Source drift invalidates evidence; unsupported numerical content and dependent figures never remain as fallback prose.

The rules page embeds the standard output IR, so `s2s.py inspect` and the existing link/snapshot checks work on both pages. Version 2 embeds only a public scene index, not a duplicate of the private authored layout. Keep that original layout with the internal graphs for regeneration. Rebuild the parent for independently generated children; a missing child produces a generation command, and a source mismatch remains visibly warned. The atlas manifest's existing `layout` field accepts either version, so all three pages can be assembled together without a separate publishing step.

For map-linked lessons, use the owning map's `_internal/<map-html-stem>/` directory (or its explicit private override) for behavior/logic graphs and the original layout. The atlas builder retains these inputs and their page mappings; `build-pair` alone does not create that bundle. Reuse the retained layout for presentation-only changes, while keeping the normal source checks. Do not recreate it from the public scene index. Exclude the entire private directory from shared HTML packages and static-site publishing.

Follow the [QA guide](qa.md): inspect the first picture, every geometry, static and interactive states, evidence disclosure, both themes and a narrow screen. Check the entire map → behavior → picture lesson → behavior/map round trip, including the selected map position. Source rereads and automatic checks are not independent human acceptance.

# Source-backed rule pages

Use this mode for the rules and reasons behind an existing `code-flow` capability. General concept explainers keep their authored HTML workflow.

Read `code-flow/references/rule-checklist.md` in the actual companion installation. Keep an internal behavior JSON and a reviewed logic JSON with the same subject, scope, nodes, edges, scenarios and state transitions. The logic input can enrich existing rules with a source-backed rationale and exceptions, and add rules/evidence. It cannot silently alter the behavior's facts. Use the companion's `author.py explain` for a draft; it deliberately does not endorse the rules.

## Compose the lesson

Write a small layout JSON using [rule-layout.schema.json](rule-layout.schema.json). Each section has an ID, a question-like title, `kind`, and `ruleIds`. Choose the order and number of figures for this topic:

- `comparison`: two or more alternatives with the same condition/result geometry. A reader can select a case; all cases remain available without JavaScript.
- `conditions`: one or more condition → outcome pictures. There is no execution edge between different rules.
- `states`: existing `transitionIds` show a before/after state and its real trigger, with the selected rules explaining the contract.

Use headings to organize existing facts; put factual values, reasons and exceptions in the reviewed rules, not layout titles. Every selected rule needs a rationale. Every new rule must appear in a figure. Preserve all conditions in the visible picture; do not replace them with an identifier or an incomplete short label. When a rule or transition is omitted during verification, the whole dependent figure is withheld with a notice.

These figures form a topic-specific explanation, not a timed workflow. Keep meaningful information in the static HTML. The shared shell preserves the product palette, dark-mode preference, evidence labels, scope and page navigation. Other visual-primer topics may use different authored geometry.

## Build and inspect

Set `PRIMER_ROOT` to the actual installed `visual-primer` folder and run from any directory. A sibling `code-flow` installation is discovered by its real path. Supply `--code-flow-root` if the two skills are installed separately.

~~~sh
python3 "$PRIMER_ROOT/scripts/rules.py" build-pair \
  --behavior-input behavior.json --input reviewed-rules.json --layout layout.json \
  --source-root /path/to/source \
  --behavior-output output/behavior.html --output output/rules.html
~~~

Inputs must remain separate from all HTML/render-JSON outputs. Builds validate and render both pages before writing either page; each file replacement is atomic. A write failure can require rerunning the pair. Old pages with another subject, scope, repository or language are not overwritten. Source drift invalidates evidence; unsupported numerical content and dependent figures never remain as fallback prose.

The rules page embeds the standard output IR, so `s2s.py inspect` and the existing link/snapshot checks work on both pages. Rebuild the parent for independently generated children; a missing child produces a generation command, and a source mismatch remains visibly warned.

Follow the [QA guide](qa.md): inspect the first picture, every geometry, case selection, evidence disclosure, both themes and a narrow screen. Check both navigation directions. Source rereads and automatic checks are not independent human acceptance.

# Authored source-backed picture lessons

Version 2 keeps the original visual-primer teaching freedom inside the linked
product: author large HTML/SVG pictures, topic-specific composition and meaningful
reader interaction, while the builder owns evidence and navigation. No new CLI
option or graph schema is needed. Pass this layout to `rules.py build-pair --layout`
or to an atlas pages manifest's `layout` field.

## Author scenes, not another fixed chart

Apply the main skill's visual-story workflow and relevant diagram patterns. Start
with the relationship that makes the business decision understandable. Choose the
number, order and geometry of scenes from the topic. A cancellation gate, pricing
composition and permission boundary need different pictures. Preserve a requested
reference's effective hierarchy and teaching technique without copying unrelated
facts. Do not impose an OAuth sequence on a policy with no sequential behavior.

The JSON envelope is deliberately small:

~~~json
{
  "version": 2,
  "sections": [
    {
      "id": "decision",
      "title": "What changes the outcome?",
      "kind": "authored",
      "ruleIds": ["rule-main"],
      "claimIds": [],
      "html": "<svg viewBox=\"0 0 640 180\" role=\"img\" aria-labelledby=\"scene-decision-title\"><title id=\"scene-decision-title\">The reviewed condition determines the outcome</title><text x=\"32\" y=\"96\">Condition</text><path d=\"M220 90 H390 l-14 -10 m14 10 l-14 10\" fill=\"none\" stroke=\"currentColor\"/><text x=\"430\" y=\"96\">Outcome</text></svg>",
      "css": "#figure-decision svg text{font:24px S2S,sans-serif;fill:var(--ink)}",
      "script": ""
    }
  ]
}
~~~

This is a syntax example, not the required visual design or a verified policy.
Replace its labels and bindings with the reviewed subject's facts. The schema is
[authored-layout.schema.json](authored-layout.schema.json). `css`, `script` and
`claimIds` are optional; the builder does not insert defaults or modify the input.

## Bind what the picture claims

- Every scene has one or more `ruleIds`, each with a reviewed rationale. Every new
  rule added to the behavior graph must appear in at least one scene.
- Put additional illustrated relationships in `claimIds`: node, action, edge,
  scenario **step** or state-transition IDs from the same graph. A scenario ID is
  not itself a claim; list its illustrated steps. Include the actual edge/step
  claims when drawing calls, handoffs or step controls.
- Related nodes and edge/step targets are included transitively. Only confirmed
  claims (plus explicitly context-only actors) allow an authored scene to render.
  Uncertain, unsupported, missing or drifted dependencies withhold its **entire
  HTML, CSS, script and title**, replacing them with a neutral notice. Other valid
  scenes remain available. Never repeat an omitted scene's assertions elsewhere.
- All policy values, boundary conditions, priorities, exceptions and simulation
  outcomes belong in reviewed rules or behavior claims, not only in presentation
  code. Keep critical exceptions visible in the lesson; the builder also adds a
  collapsible exact-condition/reason/exception/evidence reference below each scene.

Bindings are an author-supplied dependency declaration, not automatic proof of a
diagram's meaning. Re-read the source and review every visual claim and interaction
before delivery. Do not equate a passing schema/hash check with semantic review,
an observed execution, or human acceptance.

## Fragment and interaction contract

`html` is a balanced body **fragment**, not a whole document. Inline SVG, semantic
HTML, embedded bitmap images and native buttons are supported. Do not insert a
second header, navigation system, evidence database or output metadata block.

- Close every non-void HTML element explicitly (`<div></div>`, not `<div />`),
  including HTML inside SVG `foreignObject`. SVG geometry such as `<path />` and
  void HTML such as `<br />` may self-close. Finish all comments and tags; escape
  literal `<` in text as `&lt;` so it cannot consume the surrounding page.
- The container is `#figure-<id>`. Scope CSS to it, and prefix every authored DOM
  ID with `scene-<id>-`. Keep fragment links, SVG marker references and ARIA targets
  inside the same scene. This prevents clashes with the shell and other scenes.
- Use `css` and `script` fields, not `<style>`, `<script>`, inline style attributes
  or `on...` handlers inside `html`. The script executes once after its scene is
  present, with `root` bound to that section. Query within `root`; avoid global
  state or dependencies on other scenes that may be withheld. Do not assume the
  later `s2s-data` script has been parsed yet.
- Inline SVG is preferred for pictures. Bitmap `src` values can be base64 PNG,
  JPEG, GIF or WebP data URLs. No external/local asset loads, frames, forms, CSS
  imports or external scripts. The bundled `S2S` font is already available.
- Use the shared semantic variables `--ink`, `--muted`, `--paper`, `--surface`,
  `--line`, `--accent`, `--accent-soft` and `--data` where appropriate;
  `--teal` and `--soft` remain compatibility aliases for existing layouts.
  Topic-specific accent colors must remain readable in both
  `html[data-theme="light"]` and `"dark"`.
- Preserve a complete static picture without JavaScript. Use short labeled
  controls, perceivable state changes, and reset/pause where relevant. Honor
  `prefers-reduced-motion` in JavaScript or SVG animation too; the shell disables
  scene CSS animation/transitions under that preference.
- New UI code is allowed; copied target code, source prompts and verification
  anchors are forbidden in every field, including comments and hidden content.

The builder checks fragment boundaries, duplicate/reserved IDs, local references,
obvious copied anchors and asset embedding. A Content Security Policy blocks
external asset/network loads and form submission. These checks are **not a
sandbox or a general JavaScript/CSS sanitizer**: only package locally authored,
reviewed presentation code. Do not import untrusted executable HTML. The host's
offline/no-source-body review still covers the complete final artifact.

## Verify the lesson and the journey

Follow [qa.md](qa.md), including the five-second/picture-first checks, reference
continuity, text size, geometry and narrow-screen behavior. Exercise the actual
controls with keyboard and pointer, with reduced motion and JavaScript disabled.
Inspect both themes and any fallback/withheld state. Then follow map → behavior →
lesson → behavior/map and verify the return preserves the selected map position.
When a browser is unavailable, disclose that visual and interaction QA was not run.

Keep the private layout alongside internal behavior/logic JSON. The output embeds
only the rendered scenes and a public scene index; it is not a reusable private
layout. Refresh from current source, re-review the lesson, and rebuild all requested
connected pages. Existing version 1 layouts remain supported for compact references.

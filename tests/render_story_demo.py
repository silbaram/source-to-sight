#!/usr/bin/env python3
"""Render the synthetic bilingual map → behavior → picture-lesson QA fixture."""
import argparse
import importlib.util
from pathlib import Path

from authored_cases import SOURCE, story_case


def render_runtime_fixtures(atlas, source, folder, language):
    """Exercise shared controls without imposing their classes on authored HTML."""
    s2s, _ = atlas.companion()
    primer = atlas.load_primer()
    _, _, logic, layout = story_case(language)
    logic["links"]["behavior"] = {"url": "pending.html", "generated": False, "command": "$code-flow synthetic cancellation"}
    section = layout["sections"][0]
    section.update({"css": "", "script": "", "html": '''<section class="rule-figure comparison" data-kind="comparison"><p>Two reviewed outcomes.</p></section>
<section class="rule-figure comparison" data-kind="comparison">
<div class="case-controls" hidden><button type="button" aria-pressed="false">Authored control</button></div>
<article class="rule-case">Not shipped: cancelled.</article><article class="rule-case">Already shipped: manual review.</article>
</section>
<svg viewBox="0 0 20 20"><path d="M0 0 L20 20"/><foreignObject><div>Reviewed</div></foreignObject></svg>
<textarea>Complete explanation</textarea><!-- complete scene annotation -->'''})
    prepared = s2s.prepare(logic, source)
    page, _ = primer.render_rules(prepared, layout, s2s, original=logic)
    (folder / "runtime-authored.html").write_text(page, encoding="utf-8")
    legacy = {"version": 1, "sections": [{"id": "cancellation", "title": section["title"], "kind": "comparison", "ruleIds": section["ruleIds"]}]}
    page, _ = primer.render_rules(prepared, legacy, s2s, original=logic)
    (folder / "runtime-comparison.html").write_text(page, encoding="utf-8")
    # Fault injection: incomplete legacy markup must not stop unrelated controls.
    incomplete = page.replace('class="case-controls"', 'class="incomplete-controls"')
    (folder / "runtime-incomplete.html").write_text(incomplete, encoding="utf-8")
    for name, markup, script in (
        ("navigation", '''<svg viewBox="0 0 160 50"><a data-layer="outcome" href="#scene-cancellation-outcome"><text x="0" y="25">Outcome</text></a></svg>
<a data-layer="atlas" href="#scene-cancellation-outcome">Read the outcome</a>
<p id="scene-cancellation-outcome">Not shipped: cancelled.</p>''', ""),
        ("copy", '''<output>Cancelled</output>
<button type="button" class="copy-command">Copy outcome</button>
<button type="button" class="copy-command" data-command="scene-only-command">Copy outcome again</button>''',
         "root.querySelectorAll('button').forEach(button => button.addEventListener('click', () => navigator.clipboard.writeText(root.querySelector('output').textContent)));"),
    ):
        section.update({"html": markup, "script": script})
        page, _ = primer.render_rules(prepared, layout, s2s, original=logic)
        (folder / f"runtime-{name}.html").write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory for synthetic QA artifacts")
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists():
        parser.error("Use a new output directory; existing files are not overwritten.")
    source = root / "source"
    source.mkdir(parents=True)
    (source / "example.py").write_text(SOURCE, encoding="utf-8")
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("demo_atlas", repo / "skills/codebase-atlas/scripts/atlas.py")
    atlas = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(atlas)
    for language in ("ko", "en"):
        project, behavior, logic, layout = story_case(language)
        folder = root / language
        atlas.build_site(project, source, folder / "project.html", pages=[{
            "behavior": behavior, "output": folder / "behavior.html", "logic": logic,
            "layout": layout, "logicOutput": folder / "logic.html",
        }])
        render_runtime_fixtures(atlas, source, folder, language)
        print(folder / "project.html")


if __name__ == "__main__":
    main()

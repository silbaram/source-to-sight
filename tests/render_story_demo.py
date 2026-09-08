#!/usr/bin/env python3
"""Render the synthetic bilingual map → behavior → picture-lesson QA fixture."""
import argparse
from copy import deepcopy
import importlib.util
from pathlib import Path

from authored_cases import SOURCE, story_case


def render_structure_fixtures(s2s, project, source, folder):
    """Verify literal ancestry independently of path length and input order."""
    fixture = deepcopy(project)
    directory_template, file_template = deepcopy(fixture["structureEntries"])
    for index, directory in enumerate(("R", "_", "가", "R/skipped/nested", "Rextra")):
        relative_file = directory + "/example.py"
        target = source / relative_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(SOURCE, encoding="utf-8")
        evidence = deepcopy(fixture["evidence"][0])
        evidence.update({"id": f"evidence-tree-{index}", "file": relative_file})
        fixture["evidence"].append(evidence)
        for kind, path, template in (("directory", directory, directory_template),
                                     ("file", relative_file, file_template)):
            entry = deepcopy(template)
            entry.update({"id": f"structure-tree-{index}-{kind}", "path": path,
                          "label": path, "evidenceIds": [evidence["id"]]})
            fixture["structureEntries"].append(entry)
    # Children precede parents in authored input. No entry is recorded for
    # R/skipped; its descendant must use the closest *recorded* ancestor R.
    fixture["structureEntries"].reverse()
    for variant in ("rooted", "rootless"):
        data = deepcopy(fixture)
        if variant == "rootless":
            data["structureEntries"] = [entry for entry in data["structureEntries"] if entry["path"] != "."]
        prepared = s2s.prepare(data, source)
        assert all(entry["displayStatus"] == "confirmed" for entry in prepared["structureEntries"])
        (folder / f"entry-tree-{variant}.html").write_text(s2s.render(prepared), encoding="utf-8")


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
        rendered = atlas.build_site(project, source, folder / "project.html", pages=[{
            "behavior": behavior, "output": folder / "behavior.html", "logic": logic,
            "layout": layout, "logicOutput": folder / "logic.html",
        }])
        s2s, _ = atlas.companion()
        for variant in ("legacy", "missing", "empty", "uncertain", "ungrouped"):
            fixture = deepcopy(rendered[(folder / "project.html").resolve()])
            if variant == "legacy":
                fixture.pop("structureEntries")
            if variant == "missing":
                for subject in fixture["subjects"]:
                    subject["link"]["generated"] = False
            if variant == "empty":
                fixture["subjects"] = []
            if variant == "uncertain":
                fixture["structureEntries"][0].update({"confidence": "inferred", "supportStatus": "uncertain", "displayStatus": "uncertain"})
            if variant == "ungrouped":
                fixture["regions"] = []
            (folder / f"entry-{variant}.html").write_text(s2s.render(fixture), encoding="utf-8")
        render_structure_fixtures(s2s, project, source, folder)
        render_runtime_fixtures(atlas, source, folder, language)
        if language == "en":
            # These tags satisfy the IR contract, but some are rejected by
            # browser Intl implementations. Keep the original language data.
            for locale in ("en-GB-oed", "en-foo", "ko-foo", "en-US", "ko-KR"):
                fixture = deepcopy(project)
                fixture["language"] = fixture["regeneration"]["language"] = locale
                page = s2s.render(s2s.prepare(fixture, source))
                (folder / f"entry-locale-{locale}.html").write_text(page, encoding="utf-8")
        print(folder / "project.html")


if __name__ == "__main__":
    main()

"""Authored business-rule scenes keep the map/behavior/evidence contracts."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from authored_cases import SOURCE, story_case

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import author
import s2s


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


rules = module("story_rules", ROOT / "skills/visual-primer/scripts/rules.py")
atlas = module("story_atlas", ROOT / "skills/codebase-atlas/scripts/atlas.py")


class AuthoredRulesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="s2s-story-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "example.py").write_text(SOURCE, encoding="utf-8")
        self.map, self.behavior, self.logic, self.layout = story_case()

    def render(self):
        return rules.render_rules(s2s.prepare(self.logic, self.source), self.layout, s2s, original=self.logic)

    def test_authored_scene_keeps_svg_interaction_evidence_and_metadata(self):
        original = deepcopy(self.layout)
        page, omitted = self.render()
        self.assertFalse(omitted)
        self.assertIn('<svg viewBox="0 0 560 470"', page)
        self.assertIn("button.addEventListener('click'", page)
        self.assertIn("Conditions, reasons, exceptions and code evidence", page)
        self.assertIn('connect-src \'none\'', page)
        self.assertNotIn("def check(shipped):", page)
        self.assertNotIn("anchorText", page)
        embedded_layout = page.split('<script id="s2s-rule-layout" type="application/json">')[1].split('</script>')[0]
        self.assertEqual(json.loads(embedded_layout), {"version": 2, "sections": [{"id": "cancellation", "kind": "authored", "withheld": False}]})
        self.assertEqual(self.layout, original)

    def test_uncertain_rule_withholds_all_scene_assets_including_title(self):
        self.logic["rules"][0]["supportStatus"] = "uncertain"
        self.layout["sections"][0]["title"] = "A stale 77-unit refund"
        page, omitted = self.render()
        self.assertEqual(omitted, ["cancellation"])
        for private in ("A stale 77-unit refund", "lesson-hero", "const outcomes", "scene-cancellation-diagram-title"):
            self.assertNotIn(private, page)
        self.assertIn("Scene pending review", page)

    def test_rejected_numeric_rule_leaves_no_authored_fallback(self):
        self.logic["rules"][0].update({"numeric": True, "supportStatus": "uncertain", "outcome": "Refund 77 units"})
        self.layout["sections"][0]["html"] += "<p>Refund 77 units</p>"
        page, omitted = self.render()
        self.assertEqual(omitted, ["cancellation"])
        self.assertNotIn("Refund 77 units", page)
        self.assertNotIn("lesson-hero", page)

    def test_uncertain_flow_claim_and_transitive_owner_withhold_scene(self):
        for key in ("edges", "nodes"):
            with self.subTest(key=key):
                _, _, self.logic, self.layout = story_case()
                self.logic[key][0]["supportStatus"] = "uncertain"
                page, omitted = self.render()
                self.assertEqual(omitted, ["cancellation"])
                self.assertNotIn("lesson-hero", page)

    def test_source_drift_cannot_reuse_the_authored_lesson(self):
        evidence = author.capture_evidence(self.source, "ev-main", "example.py", "check", 1, 4)
        self.logic["evidence"] = [evidence]
        (self.source / "example.py").write_text(SOURCE + "\n# Source changed\n", encoding="utf-8")
        page, omitted = self.render()
        self.assertEqual(omitted, ["cancellation"])
        self.assertNotIn("lesson-hero", page)

    def test_withholding_one_scene_keeps_an_independent_reviewed_scene(self):
        self.logic["rules"][0]["supportStatus"] = "uncertain"
        self.layout["sections"].append({"id": "review", "kind": "authored", "title": "Review outcome",
                                        "ruleIds": ["rule-shipped"], "html": "<p>Independent checked result</p>"})
        page, omitted = self.render()
        self.assertEqual(omitted, ["cancellation"])
        self.assertIn("Independent checked result", page)
        self.assertNotIn("lesson-hero", page)

    def test_action_binding_includes_its_owner(self):
        owner = deepcopy(self.logic["nodes"][0])
        owner.update({"id": "node-extra", "supportStatus": "uncertain"})
        owner["actions"][0]["id"] = "action-extra"
        self.logic["nodes"].append(owner)
        self.layout["sections"][0]["claimIds"].append("action-extra")
        page, omitted = self.render()
        self.assertEqual(omitted, ["cancellation"])
        self.assertNotIn("lesson-hero", page)

    def test_dom_ids_are_unique_even_when_scene_prefixes_overlap(self):
        self.layout["sections"][0]["html"] += '<p id="scene-cancellation-extra-label">First</p>'
        self.layout["sections"].append({"id": "cancellation-extra", "kind": "authored", "title": "Second",
                                        "ruleIds": ["rule-main"], "html": '<p id="scene-cancellation-extra-label">Second</p>'})
        with self.assertRaisesRegex(ValueError, "unique across scenes"):
            rules.validate_layout(self.layout, self.logic, s2s)

    def test_unknown_claims_and_duplicate_scene_ids_are_rejected(self):
        for mutate in (
            lambda value: value["sections"][0].update({"claimIds": ["missing-edge"]}),
            lambda value: value["sections"].append(deepcopy(value["sections"][0])),
            lambda value: value["sections"][0].update({"ruleIds": ["missing-rule"]}),
        ):
            value = deepcopy(self.layout)
            mutate(value)
            with self.assertRaises(ValueError):
                rules.validate_layout(value, self.logic, s2s)

    def test_fragment_boundary_and_offline_guards(self):
        bad_html = [
            '<script>alert(1)</script>', '<style>p{color:red}</style>', '<iframe src="about:blank"></iframe>',
            '<img src="https://example.org/image.png">', '<button onclick="alert(1)">Go</button>',
            '<p id="s2s-data">Collision</p>', '<p id="scene-cancellation-x"></p><p id="scene-cancellation-x"></p>',
            '<svg><path marker-end="url(#missing)"/></svg>', '<a href="#missing">Missing</a>',
            '<svg><path fill="url(https://example.org/paint.svg)"/></svg>',
            '<div><p>Unbalanced</div>', '<form><input></form>',
        ]
        for fragment in bad_html:
            with self.subTest(fragment=fragment):
                self.layout["sections"][0]["html"] = fragment
                with self.assertRaises(ValueError):
                    rules.validate_layout(self.layout, self.logic, s2s)

    def test_html_self_closing_elements_cannot_consume_the_shell(self):
        for fragment in (
            '<textarea />', '<div />', '<button />', '<section><p /></section>',
            '<svg><foreignObject><textarea /></foreignObject></svg>',
            '<svg><title><span /></title></svg>', '<svg><desc><div /></desc></svg>',
            '<svg><g><div /></g></svg>',
            '<math><mtext><span /></mtext></math>',
            '<math><annotation-xml encoding="text/html"><div /></annotation-xml></math>',
            '<plaintext>Cannot be closed</plaintext>',
        ):
            with self.subTest(fragment=fragment):
                self.layout["sections"][0]["html"] = fragment
                with self.assertRaises(ValueError):
                    rules.validate_layout(self.layout, self.logic, s2s)

    def test_foreign_self_closing_elements_and_complete_html_remain_supported(self):
        for fragment in (
            '<svg />', '<svg><g><path d="M0 0 L10 10"/><circle r="2"/></g></svg>',
            '<svg><foreignObject><div><br/><svg><path d="M0 0"/></svg></div></foreignObject></svg>',
            '<svg><title>Diagram</title><desc><span>Explanation</span></desc></svg>',
            '<math><mrow><mi>x</mi><mspace width="1em"/></mrow></math>',
            '<math><mtext><mglyph /></mtext><annotation-xml encoding="text/html"><p>Note</p></annotation-xml></math>',
            '<p>Reviewed &amp; complete</p><!-- scene annotation -->',
            '<textarea>Reviewed &lt;condition&gt;</textarea><input/><br/>',
            '<p>A &lt; B</p>Trailing &amp',
        ):
            with self.subTest(fragment=fragment):
                self.layout["sections"][0]["html"] = fragment
                rules.validate_layout(self.layout, self.logic, s2s)

    def test_incomplete_markup_is_rejected_before_pair_outputs_are_replaced(self):
        behavior, logic = self.root / "behavior.html", self.root / "logic.html"
        rules.build_pair(self.behavior, self.logic, self.layout, self.source, behavior, logic)
        before = [path.read_bytes() for path in (behavior, logic)]
        for fragment in (
            '<p>Reviewed explanation.</p><!-- scene annotation',
            '<p>Reviewed explanation.</p><div', '<p>Reviewed explanation.</p><div title="unfinished',
            '<p>Reviewed explanation.</p><?unfinished', '<textarea />', '<div />',
        ):
            with self.subTest(fragment=fragment):
                self.layout["sections"][0]["html"] = fragment
                with self.assertRaises(ValueError):
                    rules.build_pair(self.behavior, self.logic, self.layout, self.source, behavior, logic)
                self.assertEqual([path.read_bytes() for path in (behavior, logic)], before)

    def test_source_excerpts_in_text_attributes_comments_and_assets_are_rejected(self):
        for key, value in (("html", '<p>def check(shipped):</p>'),
                           ("html", '<p title="def check&#40;shipped&#41;:">Example</p>'),
                           ("html", '<!-- def check(shipped): -->'),
                           ("css", '/* def check(shipped): */'),
                           ("script", 'const copied = "def check(shipped):";')):
            with self.subTest(key=key, value=value):
                layout = deepcopy(self.layout)
                layout["sections"][0][key] = value
                with self.assertRaises(ValueError):
                    rules.validate_layout(layout, self.logic, s2s)

    def test_external_css_and_raw_text_breakouts_are_rejected(self):
        for key, value in (("css", '@import "https://example.org/a.css";'),
                           ("css", 'p{background:url(https://example.org/a.png)}'),
                           ("css", '</style><script>alert(1)</script>'),
                           ("script", '</script><p>Escape</p>')):
            with self.subTest(key=key):
                layout = deepcopy(self.layout)
                layout["sections"][0][key] = value
                with self.assertRaises(ValueError):
                    rules.validate_layout(layout, self.logic, s2s)

    def test_authored_pair_preserves_both_links_and_fails_before_writes(self):
        behavior, logic = self.root / "behavior.html", self.root / "logic.html"
        result = rules.build_pair(self.behavior, self.logic, self.layout, self.source, behavior, logic)
        self.assertTrue(result["behavior"]["links"]["logic"]["generated"])
        self.assertTrue(result["logic"]["links"]["behavior"]["generated"])
        before = [path.read_bytes() for path in (behavior, logic)]
        self.layout["sections"][0]["claimIds"] = ["unknown"]
        with self.assertRaises(ValueError):
            rules.build_pair(self.behavior, self.logic, self.layout, self.source, behavior, logic)
        self.assertEqual([path.read_bytes() for path in (behavior, logic)], before)

    def test_subject_and_language_guards_remain_enforced(self):
        for key, value in (("language", "ko"), ("subject", {**self.logic["subject"], "id": "different"})):
            logic = deepcopy(self.logic)
            logic[key] = value
            logic["regeneration"]["language"] = logic["language"]
            logic["regeneration"]["subjectId"] = logic["subject"]["id"]
            with self.assertRaises(ValueError):
                rules.build_pair(self.behavior, logic, self.layout, self.source, self.root / "b.html", self.root / "l.html")

    def test_installed_trio_in_english_and_korean_with_cp949_defaults(self):
        installed = Path(os.environ["S2S_INSTALLED_SKILLS"]).resolve(strict=True) if os.environ.get("S2S_INSTALLED_SKILLS") else self.root / "installed skills"
        if not os.environ.get("S2S_INSTALLED_SKILLS"):
            shutil.copytree(ROOT / "skills", installed, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for language in ("en", "ko"):
            with self.subTest(language=language):
                project, behavior, logic, layout = story_case(language)
                folder = self.root / language
                folder.mkdir()
                for name, data in (("atlas.json", project), ("behavior.json", behavior), ("logic.json", logic), ("layout.json", layout),
                                   ("pages.json", [{"behavior": "behavior.json", "output": "behavior.html", "logic": "logic.json", "layout": "layout.json", "logicOutput": "logic.html"}])):
                    (folder / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                result = subprocess.run([sys.executable, "-E", "-S", "-B", str(ROOT / "tests/locale_runner.py"),
                                         str(installed / "codebase-atlas/scripts/atlas.py"), "build", str(folder / "atlas.json"),
                                         "--pages", str(folder / "pages.json"), "--source-root", str(self.source), "--output", str(folder / "project.html")],
                                        cwd=self.source, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                rendered = {layer: s2s.read_embedded(folder / file) for layer, file in (("atlas", "project.html"), ("behavior", "behavior.html"), ("logic", "logic.html"))}
                self.assertTrue(rendered["atlas"]["subjects"][0]["link"]["generated"])
                for source, target in (("behavior", "atlas"), ("behavior", "logic"), ("logic", "atlas"), ("logic", "behavior")):
                    self.assertTrue(rendered[source]["links"][target]["generated"])
                page = (folder / "logic.html").read_text(encoding="utf-8")
                self.assertIn("lesson-hero", page)
                self.assertIn("취소 요청" if language == "ko" else "Cancel request", page)
                self.assertNotIn("anchorText", page)


if __name__ == "__main__":
    unittest.main()

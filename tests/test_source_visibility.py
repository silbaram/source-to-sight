"""Public explanations reject source expressions in every text-bearing surface."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from authored_cases import SOURCE, story_case

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import s2s


class SourceVisibilityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="s2s-source-visibility-")
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name)
        (self.source / "example.py").write_text(SOURCE, encoding="utf-8")
        self.project, self.behavior, self.logic, _ = story_case()

    @staticmethod
    def set_text(data, location, value):
        target = data
        for part in location[:-1]:
            target = target[part]
        target[location[-1]] = value

    def test_prepare_rejects_source_expressions_outside_the_private_anchor(self):
        cases = (
            (("evidence", 0, "symbolOrKey"), 'rules["required"]'),
            (("nodes", 0, "codeName"), "render_rules(data, layout)"),
            (("nodes", 0, "summary"), 'return "cancelled"'),
            (("nodes", 0, "summary"), "if active: return cached"),
            (("nodes", 0, "actions", 0, "plainText"), "import json"),
            (("rules", 0, "condition"), 'status == "shipped"'),
            (("rules", 0, "outcome"), "result = cancelled"),
            (("rules", 0, "rationale"), 'The check uses `status !== "shipped"`.'),
            (("scenarios", 0, "steps", 0, "condition"), "items.length <= 3"),
            (("summary", "purpose"), "const result = check(shipped);"),
            (("warnings",), [{"id": "warning-source", "kind": "coverage-limited", "severity": "low",
                              "message": "```python\ncheck(shipped)\n```", "relatedIds": [], "candidates": []}]),
        )
        for location, value in cases:
            with self.subTest(location=location, value=value):
                data = deepcopy(self.behavior)
                self.set_text(data, location, value)
                before = deepcopy(data)
                with self.assertRaises(s2s.InvalidGraph):
                    s2s.prepare(data, self.source)
                self.assertEqual(data, before, "Rejected input stays available for author correction")

    def test_direct_render_cannot_bypass_source_text_checks(self):
        for graph in (self.project, self.behavior, self.logic):
            prepared = s2s.prepare(graph, self.source)
            for location, value in (
                (("evidence", 0, "symbolOrKey"), 'data["rules"]'),
                (("nodes", 0, "codeName"), "check(shipped)"),
                (("rules", 0, "condition"), 'state != "ready"'),
                (("summary", "purpose"), "from pathlib import Path"),
            ):
                with self.subTest(layer=graph["layer"], location=location):
                    data = deepcopy(prepared)
                    self.set_text(data, location, value)
                    with self.assertRaises(s2s.InvalidGraph):
                        s2s.render(data)

    def test_generation_request_metadata_does_not_exempt_source_expressions(self):
        request = (
            '$code-flow Explain cancellation | subject=subject-main | language=en'
            ' | targets=[{"label":"check","file":"example.py","symbol":"check"}]'
            ' | scope={"includes":["Cancellation"],"excludes":[]}'
            ' | locations=[{"file":"example.py","startLine":1,"endLine":4}]'
            ' | atlas=project.html'
        )
        self.behavior["regeneration"]["command"] = request
        prepared = s2s.prepare(self.behavior, self.source)
        self.assertEqual(prepared["regeneration"]["command"], request)
        s2s.render(prepared)
        for expression in (' | scope=state == "shipped"', ' | locations=items["required"]', ' | targets=check(shipped)'):
            with self.subTest(expression=expression):
                data = deepcopy(self.behavior)
                data["regeneration"]["command"] = request + expression
                with self.assertRaises(s2s.InvalidGraph):
                    s2s.prepare(data, self.source)

    def test_plain_explanations_locations_and_identifiers_remain_supported(self):
        for language in ("ko", "en"):
            project, behavior, logic, _ = story_case(language)
            for graph in (project, behavior, logic):
                with self.subTest(language=language, layer=graph["layer"]):
                    graph["nodes"][0]["codeName"] = "CancellationService.check"
                    graph["evidence"][0]["symbolOrKey"] = "check"
                    graph["summary"]["purpose"] = (
                        "Return the cancellation result. See docs/flow.md and https://example.org/guide?view=summary."
                        if language == "en" else "취소 결과를 반환합니다. 구현 위치는 example.py이며 확인 대상은 check입니다."
                    )
                    before = deepcopy(graph)
                    prepared = s2s.prepare(graph, self.source)
                    page = s2s.render(prepared)
                    self.assertEqual(graph, before)
                    self.assertEqual(prepared["evidence"][0]["file"], "example.py")
                    self.assertEqual(prepared["evidence"][0]["startLine"], 1)
                    self.assertEqual(prepared["evidence"][0]["endLine"], 4)
                    self.assertEqual(prepared["evidence"][0]["locationStatus"], "passed")
                    self.assertIn(graph["summary"]["purpose"], page)
                    self.assertNotIn("anchorText", json.dumps(prepared))
                    self.assertNotIn("def check(shipped):", page)
                    self.assertEqual(graph["evidence"][0]["anchorText"], "def check(shipped):")

    def test_parenthetical_natural_language_is_not_treated_as_a_function_call(self):
        for language, purpose in (
            ("ko", "OAuth(인증 프로토콜)로 사용자 인증을 설명합니다."),
            ("en", "OAuth(authentication protocol) describes how users authenticate."),
        ):
            with self.subTest(language=language):
                _, graph, _, _ = story_case(language)
                graph["summary"]["purpose"] = purpose
                prepared = s2s.prepare(graph, self.source)
                self.assertEqual(prepared["summary"]["purpose"], purpose)
                self.assertIn(purpose, s2s.render(prepared))

    def test_locations_with_parentheses_or_route_brackets_remain_supported(self):
        for filename in ("README(old).md", "src/routes/user[id].tsx"):
            source_file = self.source / filename
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text(SOURCE, encoding="utf-8")
            for original in (self.project, self.behavior, self.logic):
                with self.subTest(filename=filename, layer=original["layer"]):
                    graph = deepcopy(original)
                    graph["evidence"][0]["file"] = filename
                    graph["subject"]["targets"][0]["file"] = filename
                    graph["analysis"]["searched"] = [filename]
                    graph["summary"]["purpose"] = "Read " + filename + " for the reviewed cancellation implementation."
                    if graph.get("structureEntries"):
                        graph["structureEntries"][1]["path"] = filename
                    prepared = s2s.prepare(graph, self.source)
                    self.assertEqual(prepared["evidence"][0]["file"], filename)
                    self.assertEqual(prepared["evidence"][0]["locationStatus"], "passed")
                    self.assertIn(filename, s2s.render(prepared))

    def test_relative_navigation_query_is_not_treated_as_an_assignment(self):
        self.behavior["links"]["logic"]["url"] = "details.html?s2s-node=choose"
        prepared = s2s.prepare(self.behavior, self.source)
        self.assertEqual(prepared["links"]["logic"]["url"], "details.html?s2s-node=choose")
        self.assertIn("details.html?s2s-node=choose", s2s.render(prepared))


if __name__ == "__main__":
    unittest.main()

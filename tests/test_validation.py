"""Dependency-free validation regressions and installed-skill CLI smoke tests."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from validation_cases import atlas_graph, graph, layout, render_graph

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "skills/code-flow"
sys.path.insert(0, str(FLOW / "scripts"))
import schema_validation as validation
import s2s


class ValidationTests(unittest.TestCase):
    def assert_invalid(self, data, path, stage="internal", contract=None):
        with self.assertRaises(validation.InvalidSchemaData) as caught:
            validation.validate(data, contract or s2s.schema(stage), stage)
        self.assertEqual(caught.exception.path, tuple(path))

    def test_valid_graphs_keep_inputs_unchanged(self):
        for stage, data in (("internal", graph()), ("internal", atlas_graph()), ("render", render_graph())):
            before = deepcopy(data)
            self.assertIs(s2s.validate(data, stage), data)
            self.assertEqual(data, before)

    def test_required_property_and_unknown_property_paths(self):
        data = graph()
        del data["snapshot"]["repository"]
        self.assert_invalid(data, ["snapshot"])
        data = graph()
        data["nodes"][0]["unexpected"] = True
        self.assert_invalid(data, ["nodes", 0])

    def test_type_errors_have_stable_paths(self):
        for value in (None, False, 1, [], "text"):
            with self.subTest(value=value):
                self.assert_invalid(value, [])
        data = graph()
        data["evidence"][0]["startLine"] = True
        self.assert_invalid(data, ["evidence", 0, "startLine"])

    def test_integer_accepts_integral_json_numbers(self):
        data = graph()
        data["evidence"][0]["startLine"] = 1.0
        validation.validate(data, s2s.schema("internal"))
        data["evidence"][0]["startLine"] = 1.5
        self.assert_invalid(data, ["evidence", 0, "startLine"])

    def test_patterns_retain_previous_trailing_newline_semantics(self):
        data = graph()
        data["nodes"][0]["id"] += "\n"
        validation.validate(data, s2s.schema("internal"))
        data["nodes"][0]["id"] += "\n"
        self.assert_invalid(data, ["nodes", 0, "id"])

    def test_invalid_hash_reports_anyof_parent(self):
        data = graph()
        data["evidence"][0]["contentHash"] = "not-a-hash"
        self.assert_invalid(data, ["evidence", 0, "contentHash"])

    def test_context_only_node_disallows_claims_and_actions(self):
        for key, value in (("confidence", "exact"), ("actions", [graph()["nodes"][0]["actions"][0]])):
            data = graph()
            data["nodes"][1][key] = value
            self.assert_invalid(data, ["nodes", 1] if key == "confidence" else ["nodes", 1, "actions"])
        data = graph()
        del data["nodes"][0]["confidence"]
        self.assert_invalid(data, ["nodes", 0])

    def test_oneof_requires_exactly_one_step_target(self):
        data = graph()
        data["scenarios"][0]["steps"][0]["nodeId"] = "node-main"
        self.assert_invalid(data, ["scenarios", 0, "steps", 0])
        del data["scenarios"][0]["steps"][0]["edgeId"]
        validation.validate(data, s2s.schema("internal"))
        del data["scenarios"][0]["steps"][0]["nodeId"]
        self.assert_invalid(data, ["scenarios", 0, "steps", 0])

    def test_uniqueness_and_missing_link_command(self):
        data = graph()
        data["rules"][0]["evidenceIds"] *= 2
        self.assert_invalid(data, ["rules", 0, "evidenceIds"])
        data = graph()
        del data["links"]["logic"]["command"]
        self.assert_invalid(data, ["links", "logic"])

    def test_sorted_error_path_includes_referenced_schemas(self):
        data = graph()
        data["nodes"][0]["id"] = ""
        data["evidence"][0]["startLine"] = 0
        data["summary"]["title"] = ""
        self.assert_invalid(data, ["evidence", 0, "startLine"])
        self.assertEqual(data["nodes"][0]["id"], "")

    def test_unknown_graph_references_are_still_rejected(self):
        data = graph()
        data["edges"][0]["to"] = "node-missing"
        with self.assertRaisesRegex(s2s.InvalidGraph, "unknown references"):
            s2s.validate(data)

    def test_render_contract_and_claim_status_remain_enforced(self):
        data = render_graph()
        data["evidence"][0]["anchorText"] = "def check(value):"
        self.assert_invalid(data, ["evidence", 0], "render")
        data = render_graph()
        data["nodes"][0]["displayStatus"] = "uncertain"
        with self.assertRaisesRegex(s2s.InvalidGraph, "display status"):
            s2s.validate(data, "render")

    def test_layout_conditions_and_json_number_equality(self):
        contract = json.loads((ROOT / "skills/visual-primer/references/rule-layout.schema.json").read_text())
        for kind in ("conditions", "states", "comparison"):
            validation.validate(layout(kind), contract, "layout", formats=False)
        data = layout()
        data["version"] = 1.0
        validation.validate(data, contract, "layout")
        data["version"] = True
        self.assert_invalid(data, ["version"], "layout", contract)
        data = layout("states")
        del data["sections"][0]["transitionIds"]
        self.assert_invalid(data, ["sections", 0], "layout", contract)
        data = layout()
        data["sections"][0]["transitionIds"] = ["transition-main"]
        self.assert_invalid(data, ["sections", 0], "layout", contract)
        data = layout("comparison")
        data["sections"][0]["ruleIds"].pop()
        self.assert_invalid(data, ["sections", 0, "ruleIds"], "layout", contract)

    def test_calendar_time_offset_and_format_boundaries(self):
        valid = ["2024-02-29T23:59:59Z", "2026-09-07t12:00:00z",
                 "2026-09-07T12:00:00.123456789+09:00", "2026-09-07T12:00:00-00:00",
                 "0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"]
        invalid = ["", "yesterday", "2026-02-29T12:00:00Z", "2026-04-31T12:00:00Z",
                   "0000-01-01T00:00:00Z", "2026-09-07T24:00:00Z", "2026-09-07T12:60:00Z",
                   "2016-12-31T23:59:60Z", "2026-09-07T12:00:00+24:00", "2026-09-07T12:00:00+09:60",
                   "2026-09-07T12:00:00+0900", "2026-09-07 12:00:00Z", "2026-09-07T12:00:00",
                   "2026-09-07T12:00:00.Z", "2026-09-07T12:00:00Z\n", "２０２６-09-07T12:00:00Z"]
        for value in valid + invalid:
            with self.subTest(value=value):
                data = graph()
                data["snapshot"]["generatedAt"] = value
                if value in valid:
                    s2s.validate(data)
                else:
                    self.assert_invalid(data, ["snapshot", "generatedAt"])

    def test_schema_extensions_cannot_silently_disable_validation(self):
        for key, value in (("unevaluatedProperties", False), ("prefixItems", []), ("format", "email"),
                           ("default", 1), ("required", "name"), ("type", "invalid"), ("minItems", -1),
                           ("pattern", "["), ("items", []), ("uniqueItems", "yes")):
            with self.subTest(key=key):
                with self.assertRaises(validation.InvalidSchema):
                    validation.check_schema({key: value})
        for ref in ("https://example.org/schema", "file:///missing", "#/$defs/missing"):
            with self.assertRaises(validation.InvalidSchema):
                validation.check_schema({"$ref": ref})
        with self.assertRaises(validation.InvalidSchema):
            validation.check_schema({"$ref": "#/$defs/value", "type": "string", "$defs": {"value": {}}})


class InstalledSkillTests(unittest.TestCase):
    def test_three_clis_without_site_packages(self):
        # Copy only the installable skills, with no repository development files.
        # -E -S prevents ambient PYTHONPATH and site-packages from supplying deps.
        with tempfile.TemporaryDirectory(prefix="s2s-runtime-") as temporary:
            root = Path(temporary)
            if os.environ.get("S2S_INSTALLED_SKILLS"):
                installed = Path(os.environ["S2S_INSTALLED_SKILLS"]).resolve(strict=True)
            else:
                installed = root / "installed with spaces" / "skills"
                shutil.copytree(ROOT / "skills", installed, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            source = root / "source"
            source.mkdir()
            (source / "example.py").write_text("def check(value):\n    return bool(value)\n")
            flow = installed / "code-flow/scripts"
            atlas = installed / "codebase-atlas/scripts/atlas.py"
            rules = installed / "visual-primer/scripts/rules.py"

            def run(script, *args, success=True):
                result = subprocess.run([sys.executable, "-E", "-S", "-B", str(script), *map(str, args)],
                                        cwd=source, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                if not success:
                    self.assertNotIn("Traceback", result.stderr)
                return result

            run(flow / "author.py", "doctor")
            run(atlas, "doctor")
            data = graph()
            internal = root / "behavior.json"
            internal.write_text(json.dumps(data))
            behavior = root / "behavior.html"
            run(flow / "author.py", "build", internal, "--source-root", source, "--output", behavior)
            embedded = s2s.read_embedded(behavior)
            self.assertEqual(embedded["nodes"][0]["displayStatus"], "confirmed")
            run(flow / "s2s.py", "inspect", behavior)

            map_input = root / "atlas.json"
            map_input.write_text(json.dumps(atlas_graph()))
            map_output = root / "atlas.html"
            run(atlas, "build", map_input, "--source-root", source, "--output", map_output)
            self.assertEqual(s2s.read_embedded(map_output)["layer"], "atlas")

            logic_input = root / "logic.json"
            run(flow / "author.py", "explain", internal, "--source-root", source, "--output", logic_input)
            logic = json.loads(logic_input.read_text())
            # Simulate the host's required review after explain creates a draft.
            logic["rules"] = deepcopy(data["rules"])
            logic_input.write_text(json.dumps(logic))
            layout_input = root / "layout.json"
            layout_input.write_text(json.dumps(layout()))
            logic_output = root / "rules.html"
            run(rules, "build-pair", "--behavior-input", internal, "--input", logic_input,
                "--layout", layout_input, "--source-root", source,
                "--behavior-output", behavior, "--output", logic_output)
            self.assertEqual(s2s.read_embedded(logic_output)["layer"], "logic")
            self.assertTrue(s2s.read_embedded(behavior)["links"]["logic"]["generated"])
            self.assertTrue(s2s.read_embedded(logic_output)["links"]["behavior"]["generated"])

            # Schema failures through each public CLI remain concise diagnostics.
            data["snapshot"]["generatedAt"] = "invalid"
            internal.write_text(json.dumps(data))
            result = run(flow / "author.py", "build", internal, "--source-root", source,
                         "--output", behavior, success=False)
            self.assertIn("/snapshot/generatedAt", result.stderr)
            map_data = atlas_graph()
            del map_data["subject"]
            map_input.write_text(json.dumps(map_data))
            run(atlas, "build", map_input, "--source-root", source, "--output", map_output, success=False)
            internal.write_text(json.dumps(graph()))
            layout_input.write_text(json.dumps({"version": True, "sections": []}))
            result = run(rules, "build-pair", "--behavior-input", internal, "--input", logic_input,
                         "--layout", layout_input, "--source-root", source,
                         "--behavior-output", behavior, "--output", logic_output, success=False)
            self.assertIn("layout schema", result.stderr)


if __name__ == "__main__":
    unittest.main()

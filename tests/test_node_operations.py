"""Operation semantics retain their reviewed node evidence and public prose."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from operation_cases import SOURCE, operation_case
from validation_cases import graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import s2s


class NodeOperationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="s2s-operations-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "operations.py").write_text(SOURCE, encoding="utf-8")

    def test_business_actions_and_targets_survive_without_changing_graph_meaning(self):
        for language in ("ko", "en"):
            with self.subTest(language=language):
                data = operation_case(language)
                before = deepcopy(data)
                rendered = s2s.prepare(data, self.root)
                self.assertEqual(data, before)
                self.assertEqual([n["operation"] for n in rendered["nodes"]],
                                 [n["operation"] for n in before["nodes"]])
                self.assertEqual([(e["from"], e["to"], e["type"]) for e in rendered["edges"]],
                                 [(e["from"], e["to"], e["type"]) for e in before["edges"]])
                self.assertEqual([s["steps"][0]["condition"] for s in rendered["scenarios"]],
                                 [s["steps"][0]["condition"] for s in before["scenarios"]])
                for node, original in zip(rendered["nodes"], before["nodes"]):
                    self.assertEqual(node["displayStatus"], "confirmed")
                    self.assertEqual(node["evidenceIds"], original["evidenceIds"])
                self.assertNotIn("anchorText", json.dumps(rendered))
                for original, public in zip(before["evidence"], rendered["evidence"]):
                    self.assertEqual(public["file"], original["file"])
                    self.assertEqual(public["startLine"], original["startLine"])
                    self.assertEqual(public["endLine"], original["endLine"])
                    self.assertEqual(public["locationStatus"], "passed")
                page = s2s.render(rendered)
                self.assertNotIn('return request["order_id"]', page)
                self.assertNotIn("database.save_order(order)", page)

    def test_legacy_prose_does_not_fabricate_operation_metadata(self):
        data = graph()
        data["nodes"][0].update(label="Store database API result", roleLabel="Send external payment request",
                                summary="A historical description without reviewed operation metadata.")
        (self.root / "example.py").write_text("def check(value):\n    return value\n", encoding="utf-8")
        rendered = s2s.prepare(data, self.root)
        self.assertTrue(all("operation" not in n for n in rendered["nodes"]))
        self.assertEqual(rendered["nodes"][0]["roleLabel"], data["nodes"][0]["roleLabel"])
        s2s.render(rendered)

    def test_operation_contract_rejects_unknown_or_code_bearing_fields(self):
        invalid = (
            {}, {"kind": "sql-insert"}, {"kind": "write", "targetKind": "postgres"},
            {"kind": "write", "target": ""}, {"kind": "write", "sourceCode": "secret"},
            {"kind": "write", "target": "database.save_order(order)"},
            {"kind": "request", "target": 'http.post("/charge")'},
            {"kind": "read", "target": 'order["status"]'},
        )
        for operation in invalid:
            with self.subTest(operation=operation):
                data = operation_case()
                data["nodes"][0]["operation"] = operation
                before = deepcopy(data)
                with self.assertRaises(s2s.InvalidGraph):
                    s2s.prepare(data, self.root)
                self.assertEqual(data, before)

    def test_context_nodes_cannot_assert_a_reviewed_business_operation(self):
        data = graph()
        data["nodes"][1]["operation"] = {"kind": "request", "targetKind": "api"}
        with self.assertRaises(s2s.InvalidGraph):
            s2s.validate(data)

    def test_direct_render_cannot_bypass_operation_source_checks(self):
        rendered = s2s.prepare(operation_case(), self.root)
        rendered["nodes"][0]["operation"]["target"] = "database.save_order(order)"
        with self.assertRaises(s2s.InvalidGraph):
            s2s.render(rendered)

    def test_operation_uses_own_node_evidence_and_is_pruned_with_unsupported_node(self):
        data = operation_case()
        node = next(n for n in data["nodes"] if n["id"] == "node-payment")
        node["supportStatus"] = "unsupported"
        rendered = s2s.prepare(data, self.root)
        self.assertNotIn("node-payment", [n["id"] for n in rendered["nodes"]])
        self.assertFalse(any(e["from"] == "node-payment" or e["to"] == "node-payment"
                             for e in rendered["edges"]))
        self.assertFalse(any(n.get("operation", {}).get("targetKind") == "api"
                             for n in rendered["nodes"]))
        self.assertEqual([s["id"] for s in rendered["scenarios"]], ["scenario-unavailable"])

    def test_uncertainty_and_source_drift_do_not_become_confirmed_operations(self):
        data = operation_case()
        node = next(n for n in data["nodes"] if n["id"] == "node-payment")
        node.update(supportStatus="uncertain", confidence="inferred")
        rendered = s2s.prepare(data, self.root)
        actual = next(n for n in rendered["nodes"] if n["id"] == node["id"])
        self.assertEqual(actual["displayStatus"], "uncertain")
        self.assertEqual(actual["operation"], node["operation"])
        actual["displayStatus"] = "confirmed"
        with self.assertRaisesRegex(s2s.InvalidGraph, "display status"):
            s2s.validate(rendered, "render")

        data = operation_case()
        evidence = next(e for e in data["evidence"] if e["id"] == "ev-save")
        evidence["anchorText"] = "an outdated source anchor"
        rendered = s2s.prepare(data, self.root)
        statuses = {n["id"]: n["displayStatus"] for n in rendered["nodes"]}
        self.assertEqual(statuses["node-save"], "unverified")
        self.assertEqual(statuses["node-read"], "confirmed")


if __name__ == "__main__":
    unittest.main()

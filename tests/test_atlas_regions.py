"""Region interfaces and ancestry preserve scope without inventing edges."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from authored_cases import SOURCE, story_case

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/code-flow/scripts"))
import s2s


class AtlasRegionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="s2s-regions-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "example.py").write_text(SOURCE, encoding="utf-8")
        self.data = story_case()[0]
        child = self.data["regions"][0]
        parent = deepcopy(child)
        parent.update(id="region-parent", nodeIds=[n["id"] for n in self.data["nodes"]],
                      interface={"inputs": ["A reviewed request"], "activity": "Choose a response", "outputs": ["Decision"]})
        parent["interface"].update(actor="Example program", entryLabel="See how the decision is made", example={
            "kind": "illustrative",
            "input": {"type": "request", "title": "Can I cancel?", "items": ["Illustrative order"]},
            "output": {"type": "record", "title": "Decision", "items": ["Illustrative response"]}})
        child["parentId"] = parent["id"]
        self.data["regions"].append(parent)  # Children need not follow parents in the input.

    def test_nested_interfaces_survive_render_without_new_edges_or_anchors(self):
        before = deepcopy(self.data)
        rendered = s2s.prepare(self.data, self.root)
        self.assertEqual(self.data, before)
        self.assertEqual(rendered["regions"][0]["parentId"], "region-parent")
        self.assertEqual(rendered["regions"][1]["interface"], before["regions"][1]["interface"])
        self.assertEqual([e["id"] for e in rendered["edges"]], [e["id"] for e in before["edges"]])
        self.assertNotIn("anchorText", json.dumps(rendered))
        self.assertTrue(s2s.render(rendered))

    def test_invalid_parent_cycle_membership_and_sibling_overlap_fail(self):
        variants = []
        data = deepcopy(self.data); data["regions"][0]["parentId"] = "missing"; variants.append(data)
        data = deepcopy(self.data); data["regions"][0]["parentId"] = "region-main"; variants.append(data)
        data = deepcopy(self.data); data["regions"][1]["parentId"] = "region-main"; variants.append(data)
        data = deepcopy(self.data); data["regions"][1]["nodeIds"] = ["node-caller"]; variants.append(data)
        data = deepcopy(self.data); sibling = deepcopy(data["regions"][0]); sibling["id"] = "region-sibling"; data["regions"].append(sibling); variants.append(data)
        data = deepcopy(self.data); data.pop("structureEntries"); data["layer"] = "behavior"; variants.append(data)
        for data in variants:
            with self.subTest(regions=data["regions"], layer=data["layer"]):
                with self.assertRaises(s2s.InvalidGraph):
                    s2s.validate(data)

    def test_unsupported_parent_withholds_descendants_without_promoting_them(self):
        self.data["regions"][1]["supportStatus"] = "unsupported"
        rendered = s2s.prepare(self.data, self.root)
        self.assertEqual(rendered["regions"], [])
        self.assertTrue(any(w["kind"] == "coverage-limited" for w in rendered["warnings"]))

    def test_interface_contract_and_uncertainty_are_preserved(self):
        for key, value in (("kind", "executed"), ("input", {"type": "script", "title": "Run", "items": ["code"]})):
            data = deepcopy(self.data); data["regions"][1]["interface"]["example"][key] = value
            with self.subTest(example=value), self.assertRaises(s2s.InvalidGraph):
                s2s.validate(data)
        for value in ({}, {"inputs": "request", "activity": "check", "outputs": []},
                      {"inputs": [], "activity": "", "outputs": []},
                      {"inputs": [], "activity": "check", "outputs": [], "sourceCode": "secret"}):
            data = deepcopy(self.data); data["regions"][1]["interface"] = value
            with self.subTest(value=value), self.assertRaises(s2s.InvalidGraph):
                s2s.validate(data)
        self.data["regions"][1]["supportStatus"] = "uncertain"
        rendered = s2s.prepare(self.data, self.root)
        self.assertEqual(rendered["regions"][1]["displayStatus"], "uncertain")
        rendered["regions"][1]["displayStatus"] = "confirmed"
        with self.assertRaisesRegex(s2s.InvalidGraph, "display status"):
            s2s.validate(rendered, "render")


if __name__ == "__main__":
    unittest.main()

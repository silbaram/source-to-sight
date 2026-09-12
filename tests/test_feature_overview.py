"""Capability previews reuse exact checked child graphs, never shared-owner traces."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from authored_cases import SOURCE, story_case

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import s2s

spec = importlib.util.spec_from_file_location("feature_atlas", ROOT / "skills/codebase-atlas/scripts/atlas.py")
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)


class FeatureOverviewTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="s2s-features-")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        (self.root / "example.py").write_text(SOURCE, encoding="utf-8")
        self.output = self.root / "output/project.html"
        self.project, self.child, _, _ = story_case()
        self.project["composition"] = {"regionIds": [self.project["regions"][0]["id"]], "edgeIds": []}
        self.page = {"behavior": self.child, "output": self.output.parent / "behavior.html"}

    def build(self, pages):
        return atlas.build_site(self.project, self.root, self.output, pages=pages)[self.output]

    def test_shared_owner_keeps_each_capabilitys_exact_scope_and_graph(self):
        second = deepcopy(self.child)
        second["subject"]["id"] = second["regeneration"]["subjectId"] = "cap-second"
        second["subject"]["scope"]["includes"].append("Separate synthetic capability")
        second["nodes"][0]["label"] = "SECOND ONLY"
        cap = deepcopy(self.project["subjects"][0])
        cap.update(id="cap-second", scope=deepcopy(second["subject"]["scope"]))
        cap["link"]["url"] = "second.html"
        self.project["subjects"].append(cap)
        before = deepcopy(self.project)
        result = self.build([self.page, {"behavior": second, "output": self.output.parent / "second.html"}])
        self.assertEqual(self.project, before)
        self.assertEqual(len(result["featureDetails"]), 2)
        first, other = result["featureDetails"]
        self.assertEqual(first["subject"], self.child["subject"])
        self.assertNotIn("SECOND ONLY", json.dumps(first))
        self.assertEqual(other["nodes"][0]["label"], "SECOND ONLY")
        self.assertEqual([e["id"] for e in first["edges"]], [e["id"] for e in self.child["edges"]])
        self.assertNotIn("anchorText", json.dumps(result))
        self.assertNotIn("featureDetails", json.loads((self.output.parent / "_internal/project/atlas.internal.json").read_text(encoding="utf-8")))

    def test_map_only_refresh_reuses_checked_child_and_omits_stale_preview(self):
        first = self.build([self.page])
        before = self.page["output"].read_bytes()
        refreshed = self.build([])
        self.assertEqual(refreshed["featureDetails"], first["featureDetails"])
        self.assertEqual(self.page["output"].read_bytes(), before)
        (self.root / "example.py").write_text(SOURCE + "# changed\n", encoding="utf-8")
        stale = self.build([])
        self.assertEqual(stale["featureDetails"], [])
        self.assertFalse(stale["subjects"][0]["link"]["generated"])

    def test_composition_references_and_preview_identity_are_checked(self):
        bad = deepcopy(self.project); bad["composition"]["regionIds"] = ["missing"]
        with self.assertRaises(s2s.InvalidGraph):
            s2s.validate(bad)
        bad = deepcopy(self.project); bad["composition"]["edgeIds"] = [bad["edges"][0]["id"]]
        with self.assertRaises(s2s.InvalidGraph):
            s2s.validate(bad)  # An endpoint is outside the displayed region.
        rendered = self.build([self.page])
        for change in ("scope", "duplicate", "source-body", "snapshot"):
            bad = deepcopy(rendered); child = bad["featureDetails"][0]
            if change == "scope": child["subject"]["scope"]["includes"] = ["wrong capability"]
            if change == "duplicate": bad["featureDetails"].append(deepcopy(child))
            if change == "source-body": child["nodes"][0]["sourceCode"] = SOURCE
            if change == "snapshot": child["snapshot"]["commit"] = "a" * 40
            with self.subTest(change=change), self.assertRaises(s2s.InvalidGraph):
                s2s.validate(bad, "render")
        self.project["regions"][0]["supportStatus"] = "unsupported"
        pruned = s2s.prepare(self.project, self.root)
        self.assertEqual(pruned["composition"], {"regionIds": [], "edgeIds": []})

    def test_responsibility_summary_keeps_exact_members_and_checked_evidence(self):
        group = deepcopy(self.child["regions"][0])
        group.update(id="summary-handling", role="primary", nodeIds=[n["id"] for n in self.child["nodes"]])
        self.child["regions"] = [group]
        result = self.build([self.page])["featureDetails"][0]
        self.assertEqual(result["regions"][0]["nodeIds"], group["nodeIds"])
        self.assertEqual(result["regions"][0]["displayStatus"], "confirmed")
        self.assertEqual(len(result["nodes"]), 2)  # Detail is not replaced by summary boxes.
        self.child["regions"][0]["supportStatus"] = "unsupported"
        pruned = s2s.prepare(self.child, self.root)
        self.assertEqual(pruned["regions"], [])
        self.assertEqual(len(pruned["nodes"]), 2)

    def test_summary_members_cannot_overlap_or_reference_unrelated_nodes(self):
        group = self.child["regions"][0]
        group["role"] = "primary"
        duplicate = deepcopy(group); duplicate["id"] = "summary-other"
        self.child["regions"].append(duplicate)
        with self.assertRaisesRegex(s2s.InvalidGraph, "disjoint"):
            s2s.validate(self.child)
        duplicate["nodeIds"] = ["unrelated-node"]
        with self.assertRaisesRegex(s2s.InvalidGraph, "unknown references"):
            s2s.validate(self.child)


if __name__ == "__main__":
    unittest.main()

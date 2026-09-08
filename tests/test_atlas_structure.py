"""Package containment is reviewed data, not an inferred call graph."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from authored_cases import SOURCE, story_case

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/code-flow/scripts"))
import s2s


class AtlasStructureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="s2s-structure-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "example.py").write_text(SOURCE, encoding="utf-8")
        self.data = story_case()[0]

    def test_optional_structure_is_backward_compatible(self):
        self.data.pop("structureEntries")
        rendered = s2s.prepare(self.data, self.root)
        self.assertNotIn("structureEntries", rendered)
        self.assertIn('id="atlas-entry"', s2s.render(rendered))

    def test_structure_is_verified_without_edges_or_source_bodies(self):
        before = deepcopy(self.data)
        rendered = s2s.prepare(self.data, self.root)
        self.assertEqual(self.data, before)
        self.assertEqual(rendered["structureEntries"][0]["displayStatus"], "confirmed")
        self.assertEqual(len(rendered["edges"]), len(before["edges"]))
        self.assertNotIn("anchorText", json.dumps(rendered))
        self.assertNotIn("def check(shipped):", s2s.render(rendered))

    def test_language_tags_remain_compatible_with_the_ir_contract(self):
        for language in ("en-GB-oed", "en-foo", "ko-foo", "en-US", "ko-KR"):
            with self.subTest(language=language):
                data = deepcopy(self.data)
                data["language"] = data["regeneration"]["language"] = language
                rendered = s2s.prepare(data, self.root)
                self.assertEqual(rendered["language"], language)
                self.assertEqual(rendered["regeneration"]["language"], language)
                self.assertTrue(s2s.render(rendered))

    def test_nested_unicode_package_requires_local_code_or_config(self):
        directory = self.root / "패키지" / "注文"
        directory.mkdir(parents=True)
        (directory / "example.py").write_text(SOURCE, encoding="utf-8")
        self.data["evidence"][0]["file"] = "패키지/注文/example.py"
        self.data["structureEntries"][0].update({"path": "패키지/注文", "kind": "package"})
        self.data["structureEntries"][1]["path"] = "패키지/注文/example.py"
        rendered = s2s.prepare(self.data, self.root)
        self.assertTrue(all(e["displayStatus"] == "confirmed" for e in rendered["structureEntries"]))

    def test_invalid_paths_duplicates_refs_and_layer_fail(self):
        for path in ("../escape", "/root", "C:/root", "a/../b", "./example.py",
                     "a//b", "a/", "%2e%2e/escape", "a\\b", "a\n"):
            with self.subTest(path=path):
                data = deepcopy(self.data)
                data["structureEntries"][1]["path"] = path
                with self.assertRaises(s2s.InvalidGraph):
                    s2s.validate(data)
        for field, value in (("id", "node-main"), ("nodeIds", ["missing"]), ("evidenceIds", ["missing"]),
                             ("path", "."), ("unexpected", True)):
            with self.subTest(field=field):
                data = deepcopy(self.data)
                data["structureEntries"][1][field] = value
                with self.assertRaises(s2s.InvalidGraph):
                    s2s.validate(data)
        self.data["layer"] = "behavior"
        with self.assertRaises(s2s.InvalidGraph):
            s2s.validate(self.data)

    def test_directory_names_alone_cannot_prove_a_role(self):
        self.data["structureEntries"][0]["path"] = "unread"
        with self.assertRaisesRegex(s2s.InvalidGraph, "code/config"):
            s2s.validate(self.data)
        self.data["structureEntries"][0]["path"] = "."
        self.data["evidence"][0]["kind"] = "documentation"
        with self.assertRaises(s2s.InvalidGraph):
            s2s.validate(self.data)

    def test_stale_missing_and_external_symlink_are_unverified(self):
        path = self.root / "example.py"
        for mutation in ("changed", "deleted", "symlink"):
            with self.subTest(mutation=mutation):
                path.write_text(SOURCE, encoding="utf-8")
                data = deepcopy(self.data)
                s2s.verify_locations(data, self.root)
                if mutation == "changed":
                    path.write_text(SOURCE + "# changed\n", encoding="utf-8")
                else:
                    path.unlink()
                    if mutation == "symlink":
                        outside = tempfile.TemporaryDirectory(prefix="s2s-outside-")
                        self.addCleanup(outside.cleanup)
                        target = Path(outside.name) / "example.py"
                        target.write_text(SOURCE, encoding="utf-8")
                        try:
                            path.symlink_to(target)
                        except (OSError, NotImplementedError):
                            self.skipTest("File symlinks are unavailable on this platform.")
                rendered = s2s.prepare(data, self.root)
                self.assertTrue(all(e["displayStatus"] == "unverified" for e in rendered["structureEntries"]))
                self.assertEqual(rendered["analysis"]["status"], "partial")
                if path.is_symlink():
                    path.unlink()

    def test_unsupported_entries_and_owner_refs_are_pruned(self):
        self.data["structureEntries"][1]["supportStatus"] = "unsupported"
        self.data["nodes"][0]["supportStatus"] = "unsupported"
        rendered = s2s.prepare(self.data, self.root)
        self.assertEqual(len(rendered["structureEntries"]), 1)
        self.assertEqual(rendered["structureEntries"][0]["nodeIds"], [])
        self.assertEqual(len(self.data["structureEntries"]), 2)

    def test_render_cannot_forge_structure_status(self):
        rendered = s2s.prepare(self.data, self.root)
        rendered["structureEntries"][0]["displayStatus"] = "unverified"
        with self.assertRaisesRegex(s2s.InvalidGraph, "display status"):
            s2s.validate(rendered, "render")


if __name__ == "__main__":
    unittest.main()

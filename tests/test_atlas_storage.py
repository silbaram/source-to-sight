"""Reusable atlas authoring inputs remain private, complete and scope-safe."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote

from authored_cases import SOURCE, story_case

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import author
import s2s

spec = importlib.util.spec_from_file_location("storage_atlas", ROOT / "skills/codebase-atlas/scripts/atlas.py")
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)


class AtlasStorageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="s2s-storage-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "example.py").write_text(SOURCE, encoding="utf-8")
        self.output = self.root / "output" / "project.html"
        self.internal = self.output.parent / "_internal" / "project"
        self.map, self.behavior, self.logic, self.layout = story_case()
        self.page = {"behavior": self.behavior, "output": self.output.parent / "behavior.html",
                     "logic": self.logic, "layout": self.layout, "logicOutput": self.output.parent / "logic.html"}

    def read(self, name, root=None):
        return json.loads(((root or self.internal) / name).read_text(encoding="utf-8"))

    def build(self, pages=(), **options):
        return atlas.build_site(self.map, self.source, self.output, pages=pages, **options)

    def files(self):
        return {p.relative_to(self.output.parent): p.read_bytes()
                for p in self.output.parent.rglob("*") if p.is_file()}

    def test_map_only_retains_unpruned_evidence_without_mutating_inputs(self):
        self.map["nodes"][0]["supportStatus"] = "uncertain"
        original = deepcopy(self.map)
        self.build(data_output=self.internal / "atlas.render.json")
        saved = self.read("atlas.internal.json")
        self.assertEqual(saved["evidence"], original["evidence"])
        self.assertEqual(saved["nodes"], original["nodes"])
        self.assertEqual(self.map, original)
        self.assertEqual(self.read("pages.json"), [])
        for name in ("atlas.render.json",):
            self.assertNotIn("anchorText", json.dumps(self.read(name)))
        self.assertNotIn("anchorText", self.output.read_text(encoding="utf-8"))
        self.assertEqual(set(self.files()), {Path("project.html"), Path("_internal/project/atlas.internal.json"),
                                           Path("_internal/project/pages.json"), Path("_internal/project/atlas.render.json")})

    def test_saved_inputs_rebuild_all_three_pages_after_originals_are_gone(self):
        original = deepcopy((self.map, self.behavior, self.logic, self.layout))
        self.build([self.page])
        entry = self.read("pages.json")[0]
        self.assertEqual(self.read(entry["layout"]), self.layout)
        self.assertEqual(self.read(entry["behavior"])["evidence"], self.behavior["evidence"])
        self.assertEqual((self.map, self.behavior, self.logic, self.layout), original)
        # Copy only the retained bundle into a new output folder, without any HTML.
        restored_output = self.root / "restored" / "project.html"
        restored_internal = restored_output.parent / "_internal" / "project"
        shutil.copytree(self.internal, restored_internal)
        pages, _ = atlas.read_pages(restored_internal / "pages.json", restored_output)
        result = atlas.build_site(self.read("atlas.internal.json", restored_internal), self.source,
                                  restored_output, pages=pages)
        self.assertEqual(len(result), 3)
        self.assertTrue(result[restored_output]["subjects"][0]["link"]["generated"])
        for path, kind in ((pages[0]["output"], "logic"), (pages[0]["logicOutput"], "behavior")):
            self.assertTrue(result[path]["links"][kind]["generated"])
            self.assertTrue(result[path]["links"]["atlas"]["generated"])

    def test_map_only_refresh_keeps_saved_children_and_does_not_render_them(self):
        self.build([self.page])
        before = self.files()
        result = self.build()
        self.assertEqual(len(result), 1)
        for path, content in before.items():
            if path not in (Path("project.html"), Path("_internal/project/atlas.internal.json")):
                self.assertEqual(self.files()[path], content, path)
        self.assertTrue(result[self.output]["subjects"][0]["link"]["generated"])

    def test_adding_one_capability_preserves_other_saved_inputs_and_html(self):
        self.build([self.page])
        before = self.files()
        behavior = deepcopy(self.behavior)
        behavior["subject"]["id"] = behavior["regeneration"]["subjectId"] = "second-capability"
        entry = deepcopy(self.map["subjects"][0])
        entry["id"] = "second-capability"
        entry["link"]["url"] = "second.html"
        self.map["subjects"].append(entry)
        self.build([{"behavior": behavior, "output": self.output.parent / "second.html"}])
        self.assertEqual(len(self.read("pages.json")), 2)
        for path, content in before.items():
            if path not in (Path("project.html"), Path("_internal/project/atlas.internal.json"), Path("_internal/project/pages.json")):
                self.assertEqual(self.files()[path], content, path)

    def test_behavior_only_refresh_keeps_existing_rules_and_layout(self):
        self.build([self.page])
        entry = self.read("pages.json")[0]
        before = {key: (self.internal / entry[key]).read_bytes() for key in ("logic", "layout")}
        self.build([{key: self.page[key] for key in ("behavior", "output")}])
        self.assertEqual(self.read("pages.json")[0], entry)
        for key, content in before.items():
            self.assertEqual((self.internal / entry[key]).read_bytes(), content)

    def test_custom_directory_and_nested_unicode_output_paths_are_reusable(self):
        destination = self.output.parent / "상세 # 100%" / "동작.html"
        self.map["subjects"][0]["link"]["url"] = quote("상세 # 100%/동작.html")
        self.page["output"] = destination
        custom = self.root / "private work" / "원본"
        self.build([self.page], internal_dir=custom)
        self.assertFalse(self.internal.exists())
        pages, _ = atlas.read_pages(custom / "pages.json", self.output)
        self.assertEqual(pages[0]["output"], destination)
        self.assertEqual(pages[0]["layout"], self.layout)
        atlas.build_site(self.read("atlas.internal.json", custom), self.source, self.output,
                         pages=pages, internal_dir=custom)

    def test_invalid_layout_leaves_html_and_internal_bundle_unchanged(self):
        self.build([self.page])
        before = self.files()
        self.layout["sections"][0]["claimIds"] = ["missing-claim"]
        with self.assertRaises(ValueError):
            self.build([self.page])
        self.assertEqual(self.files(), before)

    def test_subject_ids_do_not_become_windows_device_names_or_raw_control_characters(self):
        for index, identifier in enumerate(("CON", "subject-with-newline\n")):
            with self.subTest(identifier=identifier):
                self.map["subjects"][0]["id"] = identifier
                self.behavior["subject"]["id"] = self.behavior["regeneration"]["subjectId"] = identifier
                folder = self.root / f"identifier-{index}"
                atlas.build_site(self.map, self.source, folder / "project.html", pages=[{
                    "behavior": self.behavior, "output": folder / "behavior.html"}])
                internal = folder / "_internal" / "project"
                name = self.read("pages.json", internal)[0]["behavior"]
                self.assertNotEqual(name.split(".")[0].upper(), "CON")
                self.assertFalse(any(ord(character) < 32 for character in name))
                self.assertEqual(self.read(name, internal)["subject"]["id"], identifier)

    def test_foreign_internal_identity_is_rejected_even_without_existing_html(self):
        self.build()
        for change in ("repository", "language", "scope"):
            with self.subTest(change=change):
                foreign = deepcopy(self.map)
                if change == "repository":
                    foreign["snapshot"]["repository"] = "another-repository"
                elif change == "language":
                    foreign["language"] = foreign["regeneration"]["language"] = "ko"
                else:
                    foreign["subject"]["scope"]["includes"].append("another scope")
                output = self.root / change / "project.html"
                with self.assertRaisesRegex(ValueError, "internal JSON belongs"):
                    atlas.build_site(foreign, self.source, output, internal_dir=self.internal)
                self.assertFalse(output.exists())

    def test_public_outputs_cannot_overwrite_saved_or_unrequested_inputs(self):
        self.build([self.page])
        entry = self.read("pages.json")[0]
        before = self.files()
        for name in ("atlas.internal.json", "pages.json", entry["behavior"], entry["logic"], entry["layout"]):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.build(data_output=self.internal / name)
            self.assertEqual(self.files(), before)

    def test_manifest_escape_does_not_write_outside_internal_directory(self):
        self.build([self.page])
        entry = self.read("pages.json")[0]
        entry["behavior"] = "../outside.json"
        (self.internal / "pages.json").write_text(json.dumps([entry]), encoding="utf-8")
        before = self.files()
        with self.assertRaisesRegex(ValueError, "inside the internal directory"):
            self.build()
        self.assertEqual(self.files(), before)

    def test_symlink_does_not_write_outside_internal_directory(self):
        outside = self.root / "outside.json"
        outside.write_text("private unrelated data", encoding="utf-8")
        other = self.root / "symlink-internal"
        other.mkdir()
        try:
            (other / "atlas.internal.json").symlink_to(outside)
        except OSError as error:
            self.skipTest(f"Test symlinks are unavailable on this host: {error}")
        with self.assertRaisesRegex(ValueError, "inside the internal directory"):
            self.build(internal_dir=other)
        self.assertEqual(outside.read_text(encoding="utf-8"), "private unrelated data")

    def test_saved_inputs_do_not_bypass_source_commit_verification(self):
        self.build()
        saved = self.read("atlas.internal.json")
        saved["snapshot"]["commit"] = "a" * 40
        before = self.files()
        with self.assertRaisesRegex(ValueError, "source commit changed"):
            atlas.build_site(saved, self.source, self.output)
        self.assertEqual(self.files(), before)

    def test_saved_evidence_still_detects_source_drift(self):
        evidence = author.capture_evidence(self.source, "ev-main", "example.py", "check", 1, 4)
        self.map["evidence"] = [evidence]
        self.build()
        saved = self.read("atlas.internal.json")
        (self.source / "example.py").write_text(SOURCE + "\n# changed\n", encoding="utf-8")
        result = atlas.build_site(saved, self.source, self.output)
        self.assertEqual(result[self.output]["evidence"][0]["locationStatus"], "failed")
        self.assertEqual(self.read("atlas.internal.json")["evidence"], [evidence])

    def test_installed_cli_rebuilds_from_only_saved_bundle_in_both_languages(self):
        installed = self.root / "installed skills"
        shutil.copytree(ROOT / "skills", installed, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for language in ("ko", "en"):
            with self.subTest(language=language):
                self.map, self.behavior, self.logic, self.layout = story_case(language)
                folder = self.root / language
                output = folder / "지도.html"
                atlas.build_site(self.map, self.source, output, pages=[{
                    "behavior": self.behavior, "output": folder / "behavior.html", "logic": self.logic,
                    "layout": self.layout, "logicOutput": folder / "logic.html"}])
                internal = folder / "_internal" / "지도"
                result = subprocess.run([sys.executable, "-E", "-S", "-B", str(ROOT / "tests/locale_runner.py"),
                                         str(installed / "codebase-atlas/scripts/atlas.py"), "build", str(internal / "atlas.internal.json"),
                                         "--pages", str(internal / "pages.json"), "--source-root", str(self.source), "--output", str(output)],
                                        cwd=self.source, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(str(internal), result.stdout)
                self.assertTrue(s2s.read_embedded(output)["subjects"][0]["link"]["generated"])
                self.assertTrue(s2s.read_embedded(folder / "logic.html")["links"]["atlas"]["generated"])


if __name__ == "__main__":
    unittest.main()

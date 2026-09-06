import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import author
import s2s


def draft(root):
    return author.draft(root, "Explain the conversion", "Conversion", "package", "convert",
                        ["String conversion"], ["External callers"], ["cli-utility"], "en")


def supported_graph(root):
    data = draft(root)
    data = author.capture_into(data, root, identifier="ev-convert", file="convert.py",
                               symbol="convert", start=1, end=2)
    data["nodes"] = [{"id": "convert", "kind": "component", "label": "Convert text",
                      "roleLabel": "Public function", "summary": "Returns upper-case text.",
                      "importance": "core", "contextOnly": False, "actions": [],
                      "confidence": "exact", "supportStatus": "supported",
                      "verificationNote": "Read the function body: the input's upper-case result is returned.",
                      "evidenceIds": ["ev-convert"]}]
    data["analysis"].update(status="complete", unresolved=[], nextAttempts=[])
    return data


class AuthorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        (self.source / "convert.py").write_text("def convert(text):\n    return text.upper()\n")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True).strip()

    def init_git(self):
        self.git("init", "--quiet")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--quiet", "-m", "source")

    def test_draft_is_insufficient_and_identity_depends_on_scope(self):
        data = draft(self.source)
        self.assertEqual(data["analysis"]["status"], "insufficient")
        self.assertEqual(data["nodes"], [])
        self.assertFalse(data["provenance"]["humanReviewed"])
        self.assertEqual(data["subject"]["id"], draft(self.source)["subject"]["id"])
        other = author.subject_key("other", "convert", ["String conversion"], ["External callers"])
        self.assertNotEqual(data["subject"]["id"], other)
        self.assertNotEqual(other, author.subject_key("other", "convert", ["Another path"], []))

    def test_capture_records_exact_content_but_does_not_endorse_claims(self):
        data = draft(self.source)
        result = author.capture_into(data, self.source, identifier="ev-convert", file="convert.py",
                                     symbol="convert", start=1, end=2, anchor_line=2)
        self.assertEqual(result["evidence"][0]["anchorText"], "    return text.upper()")
        self.assertEqual(result["nodes"], [])
        self.assertEqual(result["analysis"]["status"], "insufficient")
        self.assertEqual(data["evidence"], [])
        with self.assertRaisesRegex(ValueError, "already exists"):
            author.capture_into(result, self.source, identifier="ev-convert", file="convert.py",
                                symbol="convert", start=1, end=2)

    def test_capture_rejects_escape_symlinks_and_invalid_ranges(self):
        outside = self.base / "outside.py"
        outside.write_text("private content\n")
        (self.source / "link.py").symlink_to(outside)
        for file, start, end, anchor in [("../outside.py", 1, 1, None), ("link.py", 1, 1, None),
                                         ("convert.py", 2, 1, None), ("convert.py", 1, 3, None),
                                         ("convert.py", 1, 1, 2)]:
            with self.subTest(file=file, start=start, end=end), self.assertRaises(ValueError):
                author.capture_evidence(self.source, "ev", file, "symbol", start, end, anchor)

    def test_repository_identity_does_not_leak_remote_credentials(self):
        self.assertEqual(author.repository_name("https://user:secret@github.com/owner/repo.git", "fallback"), "owner/repo")
        self.assertEqual(author.repository_name("git@github.com:owner/repo.git", "fallback"), "owner/repo")
        self.assertEqual(author.repository_name("/private/local/repo", "fallback"), "fallback")

    def test_ignored_archive_does_not_inherit_parent_commit(self):
        self.init_git()
        (self.source / ".git/info/exclude").write_text("archive/\n")
        archive = self.source / "archive"
        archive.mkdir()
        (archive / "input.py").write_text("value = 1\n")
        observed = author.snapshot(archive)
        self.assertIsNone(observed["commit"])
        self.assertIsNone(observed["workingTreeClean"])

    def test_build_rejects_different_commit_without_overwriting_output(self):
        self.init_git()
        data = supported_graph(self.source)
        output = self.base / "output.html"
        author.build(data, self.source, output)
        previous = output.read_bytes()
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "--quiet", "-m", "changed")
        with self.assertRaisesRegex(ValueError, "commit changed"):
            author.build(data, self.source, output)
        self.assertEqual(output.read_bytes(), previous)

    def test_dirty_source_is_rechecked_and_changed_claim_is_not_confirmed(self):
        self.init_git()
        data = supported_graph(self.source)
        (self.source / "convert.py").write_text("def convert(text):\n    return text.lower()\n")
        result = author.build(data, self.source, self.base / "output.html")
        self.assertIs(result["snapshot"]["workingTreeClean"], False)
        self.assertEqual(result["nodes"][0]["displayStatus"], "unverified")
        self.assertEqual(result["analysis"]["status"], "partial")
        self.assertNotEqual(result["evidence"][0]["contentHash"], result["evidence"][0]["observedContentHash"])

    def test_output_collision_and_alias_do_not_destroy_files(self):
        data = supported_graph(self.source)
        output = self.base / "output.html"
        author.build(data, self.source, output)
        original = output.read_bytes()
        wrong = copy.deepcopy(data)
        wrong["subject"]["scope"]["includes"] = ["Another scope"]
        with self.assertRaisesRegex(ValueError, "another subject"):
            author.build(wrong, self.source, output)
        with self.assertRaisesRegex(ValueError, "different paths"):
            author.build(data, self.source, output, output)
        self.assertEqual(output.read_bytes(), original)

    def test_linked_ignored_evidence_is_reread_even_with_a_clean_commit(self):
        (self.source / ".gitignore").write_text("generated/\n")
        settings = self.source / "generated/settings.txt"
        settings.parent.mkdir()
        self.init_git()
        original_settings = "operation mode: uppercase\n"
        outside = self.base / "outside.txt"
        outside.write_text(original_settings)
        for mutation in ("change", "delete", "escape"):
            with self.subTest(mutation=mutation):
                settings.write_text(original_settings)
                old = supported_graph(self.source)
                old["layer"] = "logic"
                old["evidence"] = [author.capture_evidence(
                    self.source, "ev-convert", "generated/settings.txt", "mode", 1, 1, kind="config")]
                old["analysis"]["searched"] = ["generated/settings.txt"]
                # Existing pages without observedContentHash remain supported.
                old_render = author.build(old, self.source, self.base / mutation / "logic.html")
                for evidence in old_render["evidence"]:
                    del evidence["observedContentHash"]
                target = self.base / mutation / "logic.html"
                target.write_text(s2s.render(old_render))
                previous = target.read_bytes()
                current = supported_graph(self.source)
                current["links"] = {"logic": {"url": "logic.html", "generated": True}}
                output = self.base / mutation / "behavior.html"
                before = author.build(current, self.source, output)
                self.assertIs(before["snapshot"]["workingTreeClean"], True)
                self.assertTrue(before["links"]["logic"]["generated"])
                self.assertFalse(any(w["kind"] == "snapshot-mismatch" for w in before["warnings"]))
                if mutation == "change":
                    settings.write_text("operation mode: lowercase\n")
                else:
                    settings.unlink()
                    if mutation == "escape":
                        settings.symlink_to(outside)
                result = author.build(current, self.source, output)
                self.assertIs(result["snapshot"]["workingTreeClean"], True)
                self.assertEqual(result["snapshot"]["commit"], old_render["snapshot"]["commit"])
                self.assertEqual(result["nodes"][0]["displayStatus"], "confirmed")
                self.assertTrue(result["links"]["logic"]["generated"])
                warnings = [w for w in result["warnings"] if w["kind"] == "snapshot-mismatch"]
                self.assertEqual(len(warnings), 1)
                self.assertIn("logic.html", warnings[0]["message"])
                self.assertEqual(target.read_bytes(), previous)
                settings.unlink(missing_ok=True)

    def test_matching_tracked_evidence_keeps_disjoint_page_links_verified(self):
        (self.source / "usage.txt").write_text("Convert text using the public function.\n")
        self.init_git()
        logic = supported_graph(self.source)
        logic["layer"] = "logic"
        logic["evidence"] = [author.capture_evidence(
            self.source, "ev-convert", "usage.txt", "usage", 1, 1, kind="documentation")]
        author.build(logic, self.source, self.base / "logic.html")
        current = supported_graph(self.source)
        current["links"] = {"logic": {"url": "logic.html", "generated": True}}
        result = author.build(current, self.source, self.base / "behavior.html")
        self.assertTrue(result["links"]["logic"]["generated"])
        self.assertFalse(any(w["kind"] == "snapshot-mismatch" for w in result["warnings"]))

    def test_output_collision_checks_repository_but_allows_reviewed_revision_updates(self):
        self.init_git()
        self.git("remote", "add", "origin", "https://github.com/example/first.git")
        data = supported_graph(self.source)
        output = self.base / "shared.html"
        author.build(data, self.source, output)
        original = output.read_bytes()
        # A fork can have the same commit, module, symbol, scope, and subject ID.
        other = self.base / "second"
        shutil.copytree(self.source, other)
        subprocess.run(["git", "-C", str(other), "remote", "set-url", "origin",
                        "https://github.com/example/second.git"], check=True)
        other_data = supported_graph(other)
        self.assertEqual(data["subject"]["id"], other_data["subject"]["id"])
        with self.assertRaisesRegex(ValueError, "repository"):
            author.build(other_data, other, output)
        self.assertEqual(output.read_bytes(), original)
        # A freshly reviewed revision of the original repository is legitimate.
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "--quiet", "-m", "reviewed update")
        updated = supported_graph(self.source)
        author.build(updated, self.source, output)
        self.assertEqual(s2s.read_embedded(output)["snapshot"]["commit"], self.git("rev-parse", "HEAD"))

    def test_skill_installs_and_builds_without_repository_helpers_or_sibling_skills(self):
        installed = self.base / "installed/code-flow"
        shutil.copytree(ROOT / "skills/code-flow", installed, ignore=shutil.ignore_patterns("__pycache__"))
        script = installed / "scripts/author.py"
        def run(*args):
            return subprocess.run([sys.executable, str(script), *map(str, args)], cwd=self.base,
                                  text=True, capture_output=True)
        self.assertEqual(run("doctor").returncode, 0)
        graph = self.base / "graph.json"
        init_args = ("init", "--source-root", self.source, "--question", "Explain conversion",
                     "--title", "Conversion", "--module", "package", "--target", "convert",
                     "--include", "String conversion", "--profile", "cli-utility", "--language", "en", "--output", graph)
        self.assertEqual(run(*init_args).returncode, 0)
        self.assertNotEqual(run(*init_args).returncode, 0)
        result = run("capture", graph, "--source-root", self.source, "--id", "ev-convert",
                     "--file", "convert.py", "--symbol", "convert", "--start", 1, "--end", 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(graph.read_text())
        data["nodes"] = supported_graph(self.source)["nodes"]
        data["analysis"].update(status="complete", unresolved=[], nextAttempts=[])
        author.write_json(graph, data)
        html, render_json = self.base / "flow.html", self.base / "render.json"
        result = run("build", graph, "--source-root", self.source, "--output", html, "--data-output", render_json)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("anchorText", html.read_text())
        self.assertNotIn("return text.upper()", html.read_text())
        self.assertEqual(s2s.read_embedded(html)["analysis"]["status"], "complete")
        self.assertEqual(json.loads(render_json.read_text())["subject"]["id"], data["subject"]["id"])
        result = run("build", graph, "--source-root", self.source, "--output", graph)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(graph.read_text()), data)


if __name__ == "__main__":
    unittest.main()

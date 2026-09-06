import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_m1_sources", ROOT / "scripts/fetch_m1_sources.py")
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


class FetchSourcesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.origin = self.base / "local-origin"
        self.origin.mkdir()
        self.git = fetcher.git
        self.git(self.origin, "init", "--quiet")
        (self.origin / "source.txt").write_text("pinned source\n")
        self.git(self.origin, "add", ".")
        self.git(self.origin, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "-m", "source")
        self.source = {"id": "sample", "repository": "test/sample",
                       "commit": self.git(self.origin, "rev-parse", "HEAD")}
        self.target = self.base / ".cache/m1-sources/sample"
        self.fetches = 0
        self.fail_fetch = False
        root_patch = patch.object(fetcher, "ROOT", self.base)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        git_patch = patch.object(fetcher, "git", side_effect=self.local_git)
        git_patch.start()
        self.addCleanup(git_patch.stop)

    def local_git(self, root, *args):
        if args[0] == "fetch":
            self.fetches += 1
            if self.fail_fetch:
                raise subprocess.CalledProcessError(128, ["git", *args])
            # Exercise real fetch/checkout without depending on network access.
            args = tuple(self.origin.as_uri() if arg == "origin" else arg for arg in args)
        return self.git(root, *args)

    def init_unfinished(self):
        self.target.mkdir(parents=True)
        self.git(self.target, "init", "--quiet")

    def test_failed_fetch_can_resume_and_completed_fetch_is_reused(self):
        self.fail_fetch = True
        with self.assertRaises(subprocess.CalledProcessError):
            fetcher.fetch(self.source)
        self.assertTrue((self.target / ".git").is_dir())
        self.fail_fetch = False
        fetcher.fetch(self.source)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.source["commit"])
        self.assertEqual((self.target / "source.txt").read_text(), "pinned source\n")
        self.assertEqual(self.git(self.target, "status", "--porcelain"), "")
        fetcher.fetch(self.source)
        self.assertEqual(self.fetches, 2)

    def test_failure_after_init_before_origin_can_resume(self):
        self.init_unfinished()
        fetcher.fetch(self.source)
        self.assertEqual(self.git(self.target, "remote", "get-url", "origin"), "https://github.com/test/sample.git")
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.source["commit"])

    def test_unfinished_checkout_with_local_files_is_preserved(self):
        self.init_unfinished()
        (self.target / "notes.txt").write_text("local work\n")
        # Even ignored files must not be overwritten by recovery.
        (self.target / ".git/info/exclude").write_text("notes.txt\n")
        with self.assertRaisesRegex(ValueError, "local files"):
            fetcher.fetch(self.source)
        self.assertEqual((self.target / "notes.txt").read_text(), "local work\n")
        self.assertEqual(self.fetches, 0)

    def test_unfinished_checkout_with_another_origin_is_preserved(self):
        self.init_unfinished()
        self.git(self.target, "remote", "add", "origin", "https://github.com/test/another.git")
        with self.assertRaisesRegex(ValueError, "another origin"):
            fetcher.fetch(self.source)
        self.assertEqual(self.git(self.target, "remote", "get-url", "origin"), "https://github.com/test/another.git")
        self.assertEqual(self.fetches, 0)

    def test_completed_checkout_with_edits_or_another_commit_is_preserved(self):
        fetcher.fetch(self.source)
        (self.target / "source.txt").write_text("local change\n")
        with self.assertRaisesRegex(ValueError, "changed or at another commit"):
            fetcher.fetch(self.source)
        self.assertEqual((self.target / "source.txt").read_text(), "local change\n")
        self.git(self.target, "add", "source.txt")
        self.git(self.target, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "-m", "local revision")
        head = self.git(self.target, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "changed or at another commit"):
            fetcher.fetch(self.source)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), head)
        self.assertEqual(self.fetches, 1)


if __name__ == "__main__":
    unittest.main()

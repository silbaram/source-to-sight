import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate as ev


def reference(identifier):
    case = next(c for c in ev.read(ROOT / "eval/cases.json")["cases"] if c["id"] == identifier)
    return ev.read(ROOT / "eval" / case["expectation"])


def rendered(identifier):
    """Supply display fields for matcher tests; source rechecking has separate integration tests."""
    case = next(c for c in ev.read(ROOT / "eval/cases.json")["cases"] if c["id"] == identifier)
    g = ev.read(ROOT / "eval" / case["candidate"])
    for item in ev.s2s.claims(g):
        item["displayStatus"] = "context" if item.get("contextOnly") else "uncertain" if item["supportStatus"] == "uncertain" else "confirmed"
    return g


class EvaluationTests(unittest.TestCase):
    def test_manifest_covers_twenty_four_cases_and_preserves_original_eighteen(self):
        suite, sources = ev.load_suite(ROOT / "eval/cases.json")
        self.assertEqual(len(suite["cases"]), 24)
        self.assertEqual(len(sources), 6)
        legacy, _ = ev.load_suite(ROOT / "eval/cases-m15.json")
        self.assertEqual(suite["cases"][:18], legacy["cases"])
        prior = ev.read(ROOT / "eval/runs/2026-09-06-flow-animation.json")
        self.assertEqual(ev.digest(legacy), prior["manifestHash"])
        for c in suite["cases"]:
            self.assertEqual(ev.check_graph(rendered(c["id"]), reference(c["id"]))["errors"], [])

    def test_duplicate_case_or_missing_profile_is_rejected(self):
        suite = ev.read(ROOT / "eval/cases.json")
        actual = ev.read
        for cases in (suite["cases"][:-1], suite["cases"] + [suite["cases"][0]]):
            changed = {**suite, "cases": cases}
            with patch.object(ev, "read", side_effect=lambda p: changed if Path(p).name == "cases.json" else actual(p)):
                with self.assertRaises(ValueError):
                    ev.load_suite(ROOT / "eval/cases.json")

    def test_reference_cannot_forbid_unknown_role(self):
        ref = reference("web-lookup")
        ref["forbiddenEdges"] = [{"fromRole": "missing", "toRole": "tree", "type": "invokes", "status": "confirmed"}]
        with self.assertRaises(ValueError):
            ev.validate_reference(ref, "web-lookup")

    def test_duplicate_repository_cannot_inflate_coverage(self):
        sources = ev.read(ROOT / "eval/m1/sources.json")
        sources[-1]["repository"] = sources[0]["repository"]
        actual = ev.read
        with patch.object(ev, "read", side_effect=lambda p: sources if Path(p).name == "sources.json" else actual(p)):
            with self.assertRaisesRegex(ValueError, "distinct repositories"):
                ev.load_suite(ROOT / "eval/cases.json")

    def test_paths_reject_traversal_absolute_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            (root / "outside").symlink_to(Path(tmp), target_is_directory=True)
            for path in ("../input.json", "/input.json", "outside/input.json"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    ev.within(root, path)

    def test_renamed_ids_and_labels_match_the_same_source_roles(self):
        g = rendered("library-peek")
        names = {n["id"]: f"renamed-{i}" for i, n in enumerate(g["nodes"])}
        for n in g["nodes"]:
            n["id"] = names[n["id"]]
            n["label"] = "다르게 쓴 제목"
        for e in g["edges"]:
            e["from"], e["to"] = names[e["from"]], names[e["to"]]
        self.assertEqual(ev.check_graph(g, reference("library-peek"))["errors"], [])

    def test_identical_name_in_wrong_file_does_not_match(self):
        g = rendered("utility-strip")
        g["evidence"][0]["file"] = "different.js"
        self.assertEqual(ev.check_graph(g, reference("utility-strip"))["missingNodes"], ["strip"])

    def test_missing_and_ambiguous_nodes_fail(self):
        g = rendered("library-peek")
        g["nodes"].pop()
        result = ev.check_graph(g, reference("library-peek"))
        self.assertEqual(result["matchedNodes"], 1)
        self.assertEqual(result["matchedEdges"], 0)
        g = rendered("utility-strip")
        g["nodes"].append({**g["nodes"][0], "id": "duplicate"})
        self.assertIn("role-ambiguous:strip", ev.check_graph(g, reference("utility-strip"))["errors"])

    def test_reversing_an_edge_fails_required_relationship(self):
        g = rendered("library-peek")
        g["edges"][0]["from"], g["edges"][0]["to"] = g["edges"][0]["to"], g["edges"][0]["from"]
        self.assertEqual(ev.check_graph(g, reference("library-peek"))["matchedEdges"], 0)

    def test_registration_disguised_as_invocation_is_critical(self):
        g = rendered("plugin-hooks")
        g["edges"][0]["type"] = "invokes"
        self.assertTrue(ev.check_graph(g, reference("plugin-hooks"))["criticalErrors"])

    def test_dynamic_target_and_relationship_cannot_become_confirmed(self):
        g = rendered("plugin-hooks")
        for n in g["nodes"]:
            if n["kind"] == "boundary":
                n["displayStatus"] = "confirmed"
        g["edges"][-1]["displayStatus"] = "confirmed"
        self.assertEqual(len(ev.check_graph(g, reference("plugin-hooks"))["criticalErrors"]), 2)

    def test_unordered_event_cannot_invent_playback(self):
        g = rendered("event-receivers")
        g["scenarios"] = [{"id": "made-up-order"}]
        self.assertIn("invented-ordered-scenario", ev.check_graph(g, reference("event-receivers"))["errors"])

    def test_additional_claims_are_visible_for_manual_review(self):
        g = rendered("utility-strip")
        g["nodes"].append({**g["nodes"][0], "id": "new", "codeName": "other"})
        self.assertEqual(ev.check_graph(g, reference("utility-strip"))["additionalNodes"], ["new"])

    def test_failed_location_is_not_automatic_success(self):
        g = rendered("utility-strip")
        g["evidence"][0]["locationStatus"] = "failed"
        self.assertIn("evidence-location-failed", ev.check_graph(g, reference("utility-strip"))["errors"])

    def test_human_review_cannot_be_inferred_from_provenance(self):
        g, ref = rendered("utility-strip"), reference("utility-strip")
        g["provenance"]["humanReviewed"] = True
        self.assertEqual(ev.review_status(None, g, ref, "engine")[0], "pending")
        blank = ev.review_template(g, ref, "engine")
        self.assertEqual(ev.review_status(blank, g, ref, "engine")[0], "pending")

    def approved_review(self, graph, ref):
        review = ev.review_template(graph, ref, "engine")
        for key in ("reference", "candidate"):
            review[key].update(decision="pass", reviewer="Unit test fixture", reviewedAt="2026-09-06T10:00:00+09:00")
        for group in ("axes", "facts", "forbidden"):
            review["candidate"][group] = dict.fromkeys(review["candidate"][group], "pass")
        return review

    def test_review_requires_all_axes_facts_and_forbidden_checks(self):
        g, ref = rendered("utility-strip"), reference("utility-strip")
        review = self.approved_review(g, ref)
        self.assertEqual(ev.review_status(review, g, ref, "engine")[0], "passed")
        review["candidate"]["facts"]["fact-1"] = "pending"
        self.assertEqual(ev.review_status(review, g, ref, "engine")[0], "pending")
        review["candidate"]["facts"]["fact-1"] = "fail"
        self.assertEqual(ev.review_status(review, g, ref, "engine")[0], "failed")

    def test_reviews_stale_after_candidate_reference_or_renderer_change(self):
        g, ref = rendered("utility-strip"), reference("utility-strip")
        review = self.approved_review(g, ref)
        for key in ("candidateHash", "expectationHash", "engineHash"):
            changed = {**review, key: "different"}
            self.assertEqual(ev.review_status(changed, g, ref, "engine")[0], "stale")

    def test_critical_manual_finding_blocks_pass(self):
        g, ref = rendered("utility-strip"), reference("utility-strip")
        review = self.approved_review(g, ref)
        review["candidate"]["criticalErrors"] = ["Condition reversed in explanation"]
        state, _, critical = ev.review_status(review, g, ref, "engine")
        self.assertEqual(state, "failed")
        self.assertEqual(len(critical), 1)

    def test_invalid_review_shapes_and_unsigned_approval_fail_closed(self):
        g, ref = rendered("utility-strip"), reference("utility-strip")
        review = self.approved_review(g, ref)
        for changed in ([], {**review, "candidate": None},
                        {**review, "reference": {**review["reference"], "reviewer": None}},
                        {**review, "candidate": {**review["candidate"], "axes": {"rules": []}}}):
            self.assertEqual(ev.review_status(changed, g, ref, "engine")[0], "invalid")

    def test_range_count_uses_union_and_handles_large_values(self):
        self.assertEqual(ev.evidence_line_count({("a", 1, 10), ("a", 5, 15), ("b", 3, 4)}), 17)
        self.assertEqual(ev.evidence_line_count({("a", 1, 10**12)}), 10**12)

    def report(self):
        row = dict(id="case", profile="cli-utility", variant="typical", expectationHash="fixed",
                   autoStatus="passed", status="pending-review", errors=[], criticalErrors=[],
                   requiredNodes=1, matchedNodes=1, requiredEdges=0, matchedEdges=0)
        return dict(version=1, manifestHash="manifest", sources=[], results=[row])

    def test_compare_flags_missing_cases_even_if_averages_improve(self):
        before, after = self.report(), self.report()
        after["results"] = []
        self.assertEqual(ev.compare(before, after)["status"], "regressed")

    def test_compare_flags_critical_errors_and_new_failed_cases(self):
        before, after = self.report(), self.report()
        after["results"][0]["criticalErrors"] = ["false relationship"]
        self.assertEqual(ev.compare(before, after)["status"], "regressed")
        after = self.report()
        after["results"].append({**after["results"][0], "id": "new", "status": "failed"})
        self.assertEqual(ev.compare(before, after)["status"], "regressed")

    def test_compare_does_not_call_changed_answers_improvement(self):
        before, after = self.report(), self.report()
        after["results"][0]["expectationHash"] = "changed"
        self.assertEqual(ev.compare(before, after)["status"], "incomparable")

    def test_compare_preserves_loss_of_prior_human_acceptance(self):
        before, after = self.report(), self.report()
        before["results"][0]["status"] = "passed"
        self.assertEqual(ev.compare(before, after)["status"], "regressed")


class EvaluationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        (self.source / "api.py").write_text("def entry():\n    return 1\n")
        (self.source / ".gitignore").write_text("extra.py\n")
        self.git("init", "--quiet")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--quiet", "-m", "fixture")
        self.graph = ev.author.draft(self.source, "What happens?", "Entry", "fixture", "entry",
                                     ["entry"], ["callers"], ["cli-utility"], repository="test/fixture")
        self.graph = ev.author.capture_into(self.graph, self.source, identifier="ev-entry", file="api.py", symbol="entry", start=1, end=2)
        self.graph["analysis"].update(status="complete", unresolved=[], nextAttempts=[])
        self.graph["nodes"] = [dict(id="entry", kind="component", label="Entry", roleLabel="API", summary="Returns one.",
                                    codeName="entry", importance="core", contextOnly=False, actions=[], confidence="exact",
                                    supportStatus="supported", verificationNote="Read the return expression.", evidenceIds=["ev-entry"])]
        self.ref = dict(version=1, caseId="fixture", identity={k: copy.deepcopy(self.graph[k]) for k in ("layer", "language", "subject")},
                        profiles=["cli-utility"], statuses=["complete"], nodes=[dict(key="entry", file="api.py", line=1,
                        codeNames=["entry"], kind="component", status="confirmed")], edges=[], forbiddenEdges=[],
                        noScenarios=True, requiredFacts=["Returns one"], forbiddenClaims=["Calls HTTP"])
        self.case = dict(id="fixture", profile="cli-utility", variant="typical")
        self.source_spec = dict(repository="test/fixture", commit=self.git("rev-parse", "HEAD"))
        self.candidate = self.base / "candidate.json"
        self.output = self.base / "output"
        self.output.mkdir()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True).strip()

    def run_case(self, save=True):
        if save:
            ev.author.write_json(self.candidate, self.graph)
        return ev.evaluate_case(self.case, self.source_spec, self.ref, self.candidate, self.source, self.output, "engine")

    def test_real_source_is_rechecked_and_review_remains_pending(self):
        result = self.run_case()
        self.assertEqual(result["autoStatus"], "passed")
        self.assertEqual(result["status"], "pending-review")
        self.assertIsNone(result["metrics"]["inputTokens"])
        self.assertIsNone(result["metrics"]["costUSD"])
        data = ev.s2s.read_embedded(self.output / "fixture.html")
        self.assertNotIn("anchorText", data["evidence"][0])
        self.assertNotIn("def entry():", (self.output / "fixture.html").read_text())

    def test_missing_candidate_reduces_recall_instead_of_disappearing(self):
        result = self.run_case(save=False)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(ev.summarize([result])["cli-utility"]["nodeRecall"], 0)

    def test_dirty_source_and_wrong_commit_are_rejected(self):
        (self.source / "api.py").write_text("changed\n")
        self.assertIn("source-checkout-must-be-clean-at-pin", self.run_case()["errors"][0])
        self.source_spec["commit"] = "0" * 40
        self.assertIn("candidate-source-mismatch", self.run_case()["errors"][0])

    def test_changed_ignored_evidence_is_detected_despite_clean_git(self):
        (self.source / "extra.py").write_text("original = 1\n")
        self.graph = ev.author.capture_into(self.graph, self.source, identifier="ev-extra", file="extra.py", symbol="original", start=1, end=1)
        self.graph["nodes"][0]["evidenceIds"].append("ev-extra")
        (self.source / "extra.py").write_text("changed = 2\n")
        self.assertTrue(ev.author.snapshot(self.source)["workingTreeClean"])
        result = self.run_case()
        self.assertEqual(result["autoStatus"], "failed")
        self.assertIn("evidence-location-failed", result["errors"])

    def test_wrong_scope_is_rejected(self):
        self.graph["subject"]["scope"]["includes"] = ["some other function"]
        self.assertIn("candidate-target-scope-profile-mismatch", self.run_case()["errors"][0])

    def test_existing_output_directory_and_answers_are_preserved(self):
        answer = self.output / "answer.json"
        answer.write_text("keep my answer")
        self.assertEqual(ev.main(["run", "--output", str(self.output)]), 2)
        self.assertEqual(answer.read_text(), "keep my answer")

    def test_run_exit_codes_distinguish_automatic_success_from_strict_acceptance(self):
        ev.author.write_json(self.candidate, self.graph)
        ev.author.write_json(self.base / "reference.json", self.ref)
        case = {**self.case, "source": "source", "candidate": "candidate.json", "expectation": "reference.json"}
        suite = dict(version=1, cases=[case])
        # Full manifest breadth is tested separately; this isolates real CLI gate logic on a local Git fixture.
        for strict, expected in ((False, 0), (True, 1)):
            args = SimpleNamespace(manifest=str(self.base / "manifest.json"), case=None,
                                   output=str(self.base / f"run-{strict}"), candidates=None,
                                   source_cache=str(self.base), reviews=None, strict=strict)
            with patch.object(ev, "load_suite", return_value=(suite, {"source": self.source_spec})):
                self.assertEqual(ev.run(args), expected)
            self.assertEqual(ev.read(Path(args.output) / "results.json")["status"], "pending-review")


if __name__ == "__main__":
    unittest.main()

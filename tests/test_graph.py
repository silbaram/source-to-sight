import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"skills/code-flow/scripts"))
import s2s


def fixture(name="cli-transform"):
    return json.loads((ROOT/"fixtures"/(name+".json")).read_text())


class GraphContractTests(unittest.TestCase):
    def render_cli(self, source, output, data_output=None):
        command = [sys.executable, str(ROOT/'skills/code-flow/scripts/s2s.py'), 'render', str(source),
                   '--source-root', str(ROOT), '--output', str(output)]
        if data_output is not None:
            command += ['--data-output', str(data_output)]
        return subprocess.run(command, capture_output=True, text=True)

    def test_render_cli_preserves_internal_input_and_outputs_on_path_collisions(self):
        for mode in ('input-html', 'input-json', 'same-outputs', 'symlink', 'hardlink'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);source=root/'internal.json';output=root/'flow.html';data_output=root/'flow.json'
                source.write_text(json.dumps(fixture()))
                output.write_text('Keep the previous HTML.')
                data_output.write_text('Keep the previous render JSON.')
                before={p:p.read_bytes() for p in (source,output,data_output)}
                if mode=='input-html':output=source
                elif mode=='input-json':data_output=source
                elif mode=='same-outputs':data_output=output
                else:
                    data_output=root/'alias.json'
                    if mode=='symlink':data_output.symlink_to(source)
                    else:os.link(source,data_output)
                result=self.render_cli(source,output,data_output)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertRegex(result.stderr,'separate|different paths')
                for path,content in before.items():self.assertEqual(path.read_bytes(),content)

    def test_render_cli_refreshes_matching_html_but_preserves_another_subject(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'internal.json';output=root/'flow.html';data_output=root/'flow.json'
            data=fixture();source.write_text(json.dumps(data));original=source.read_bytes()
            for _ in range(2):
                result=self.render_cli(source,output,data_output)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(s2s.read_embedded(output),json.loads(data_output.read_text()))
                self.assertEqual(source.read_bytes(),original)
            before={p:p.read_bytes() for p in (output,data_output)}
            data['subject']['scope']['includes']=['Another explanation scope.']
            source.write_text(json.dumps(data))
            result=self.render_cli(source,output,data_output)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('another subject',result.stderr)
            for path,content in before.items():self.assertEqual(path.read_bytes(),content)

    def test_all_fixture_contracts_and_render_boundary(self):
        repos={r["repository"]:r["id"] for r in json.loads((ROOT/"fixtures/source-repositories.json").read_text())}
        for path in (ROOT/"fixtures").glob("*.json"):
            if path.name=="source-repositories.json":continue
            with self.subTest(path=path.name):
                data=json.loads(path.read_text())
                repo=repos.get(data["snapshot"]["repository"])
                source=ROOT/".cache/sources"/repo if repo else ROOT
                s2s.validate(data)
                prepared=s2s.prepare(data,source)
                page=s2s.render(prepared)
                self.assertNotIn("anchorText",page)
                for evidence in data["evidence"]:
                    self.assertNotIn(evidence["anchorText"],page)

    def test_small_static_utility_is_complete(self):
        data=s2s.prepare(fixture("utility-minimum"),ROOT/".cache/sources/strip-ansi")
        self.assertEqual(data["analysis"]["status"],"complete")
        self.assertEqual(len(data["nodes"]),1)
        self.assertEqual(data["scenarios"],[])
        self.assertEqual(data["nodes"][0]["displayStatus"],"confirmed")

    def test_duplicate_ids_are_rejected(self):
        data=fixture();data["edges"][0]["id"]=data["nodes"][0]["id"]
        with self.assertRaisesRegex(s2s.InvalidGraph,"unique"):s2s.validate(data)

    def test_dangling_edge_is_rejected(self):
        data=fixture();data["edges"][0]["to"]="missing"
        with self.assertRaisesRegex(s2s.InvalidGraph,"unknown references"):s2s.validate(data)

    def test_step_must_reference_exactly_one_target(self):
        data=fixture();data["scenarios"][0]["steps"][0]["nodeId"]="input"
        with self.assertRaises(s2s.InvalidGraph):s2s.validate(data)

    def test_extra_code_field_is_rejected(self):
        data=fixture();data["nodes"][0]["sourceCode"]="secret source"
        with self.assertRaises(s2s.InvalidGraph):s2s.validate(data)

    def test_unknown_semantic_type_is_rejected(self):
        data=fixture();data["edges"][0]["type"]="spring-only-call"
        with self.assertRaises(s2s.InvalidGraph):s2s.validate(data)

    def test_context_has_no_fabricated_verification(self):
        data=fixture()
        context={"id":"actor","kind":"actor","label":"사용자","roleLabel":"문맥",
                 "summary":"설명을 위한 사용자입니다.","importance":"core","contextOnly":True,"actions":[]}
        data["nodes"].append(context)
        prepared=s2s.prepare(data,ROOT)
        self.assertEqual(prepared["nodes"][-1]["displayStatus"],"context")
        context["confidence"]="exact"
        with self.assertRaises(s2s.InvalidGraph):s2s.validate(data)

    def test_changed_file_does_not_keep_confirmed_status(self):
        data=fixture()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/data["evidence"][0]["file"];path.parent.mkdir(parents=True)
            original=(ROOT/data["evidence"][0]["file"]).read_text()
            path.write_text(original+"Changed body, unchanged anchors.\n")
            result=s2s.prepare(data,directory)
        self.assertEqual(result["nodes"][0]["confidence"],"exact")
        self.assertEqual(result["nodes"][0]["displayStatus"],"unverified")
        self.assertEqual(result["analysis"]["status"],"partial")
        self.assertTrue(any(w["kind"]=="evidence-unverified" for w in result["warnings"]))
        self.assertEqual(data["evidence"][0]["locationStatus"],"passed")
        self.assertEqual(result["evidence"][0]["contentHash"],data["evidence"][0]["contentHash"])
        self.assertEqual(result["evidence"][0]["observedContentHash"],
                         hashlib.sha256((original+"Changed body, unchanged anchors.\n").encode()).hexdigest())

    def test_wrong_range_cannot_be_overridden_by_input_badge(self):
        data=fixture();data["evidence"][0]["endLine"]=999999
        result=s2s.prepare(data,ROOT)
        self.assertEqual(result["nodes"][0]["displayStatus"],"unverified")

    def test_semantic_rejection_prunes_dependents(self):
        data=fixture();data["nodes"][1]["supportStatus"]="unsupported"
        result=s2s.prepare(data,ROOT)
        self.assertNotIn("convert",[n["id"] for n in result["nodes"]])
        self.assertEqual(result["edges"],[])
        self.assertEqual(result["scenarios"],[])
        self.assertTrue(any(w["kind"]=="claim-unsupported" for w in result["warnings"]))

    def test_numerical_rule_requires_confirmed_evidence_even_if_flag_lies(self):
        data=fixture()
        data["rules"]=[{"id":"numeric-rule","plainText":"최대 3회 시도합니다.",
            "condition":"실패","outcome":"3회 후 종료","numeric":False,"nodeIds":["convert"],
            "confidence":"inferred","supportStatus":"uncertain","evidenceIds":[data["evidence"][0]["id"]],
            "verificationNote":"확인되지 않은 규칙입니다."}]
        result=s2s.prepare(data,ROOT)
        self.assertEqual(result["rules"],[])
        self.assertTrue(any(w["kind"]=="claim-unsupported" for w in result["warnings"]))

    def test_forged_display_state_is_rejected(self):
        data=s2s.prepare(fixture("adversarial"),ROOT)
        data["nodes"][0]["displayStatus"]="confirmed"
        with self.assertRaisesRegex(s2s.InvalidGraph,"disagrees"):s2s.validate(data,"render")

    def test_source_path_must_stay_within_repository(self):
        data=fixture();data["evidence"][0]["file"]="../outside.py"
        with self.assertRaises(s2s.InvalidGraph):s2s.validate(data)

    def test_symlink_escape_is_unverified(self):
        data=fixture()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/data["evidence"][0]["file"];path.parent.mkdir(parents=True)
            path.symlink_to(ROOT/data["evidence"][0]["file"])
            result=s2s.prepare(data,root)
        self.assertEqual(result["evidence"][0]["locationStatus"],"failed")

    def test_executable_and_absolute_links_are_rejected(self):
        for url in ["javascript:alert(1)","//example.org/page","%6aavascript:alert(1)","/absolute.html","\\\\host\\page"]:
            with self.subTest(url=url):
                data=fixture();data["links"]["atlas"]={"url":url,"generated":True}
                with self.assertRaises(s2s.InvalidGraph):s2s.validate(data)

    def test_injection_stays_data_and_template_markers_are_not_reexpanded(self):
        data=fixture()
        payload='</script><script>globalThis.injected=true</script> __S2S_LAYOUT__'
        data["summary"]["purpose"]=payload
        result=s2s.prepare(data,ROOT)
        page=s2s.render(result)
        self.assertNotIn('</script><script>globalThis.injected',page)
        self.assertIn('\\u003c/script\\u003e',page)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"page.html";path.write_text(page)
            self.assertEqual(s2s.read_embedded(path)["summary"]["purpose"],payload)

    def test_anchor_copied_to_plain_text_is_rejected(self):
        data=fixture();data["summary"]["purpose"]=data["evidence"][0]["anchorText"]
        with self.assertRaisesRegex(s2s.InvalidGraph,"anchor"):s2s.prepare(data,ROOT)

    def test_whole_source_block_is_rejected(self):
        data=fixture();data["summary"]["purpose"]="```python\ndef secret(): pass\n```"
        with self.assertRaises(s2s.InvalidGraph):s2s.prepare(data,ROOT)

    def test_output_contract_forbids_verification_anchors(self):
        original=fixture();data=s2s.prepare(original,ROOT)
        data["evidence"][0]["anchorText"]=original["evidence"][0]["anchorText"]
        with self.assertRaises(s2s.InvalidGraph):s2s.validate(data,"render")

    def test_missing_target_is_not_an_active_link(self):
        data=fixture();data["links"]["logic"]={"url":"missing.html","generated":True}
        with tempfile.TemporaryDirectory() as directory:
            result=s2s.prepare(data,ROOT,Path(directory)/"flow.html")
        self.assertFalse(result["links"]["logic"]["generated"])
        self.assertIn("--explain",result["links"]["logic"]["command"])

    def test_wrong_subject_is_not_activated_and_refresh_activates_matching_pair(self):
        data=fixture()
        data["links"]["logic"]={"url":"logic.html","generated":False,"command":"$code-flow --explain"}
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/"logic.html"
            other=copy.deepcopy(data);other["layer"]="logic"
            other["subject"]["id"]="other";other["regeneration"]["subjectId"]="other"
            target.write_text(s2s.render(s2s.prepare(other,ROOT)))
            self.assertFalse(s2s.prepare(data,ROOT,Path(directory)/"flow.html")["links"]["logic"]["generated"])
            other["subject"]["id"]=data["subject"]["id"]
            other["regeneration"]["subjectId"]=data["subject"]["id"]
            target.write_text(s2s.render(s2s.prepare(other,ROOT)))
            self.assertTrue(s2s.prepare(data,ROOT,Path(directory)/"flow.html")["links"]["logic"]["generated"])

    def test_snapshot_ignores_generation_time_but_checks_source_content(self):
        left=s2s.prepare(fixture(),ROOT);right=copy.deepcopy(left)
        right["snapshot"]["generatedAt"]="2026-09-07T00:00:00Z"
        self.assertTrue(s2s.source_matches(left,right))
        right["evidence"][0]["contentHash"]="a"*64
        self.assertFalse(s2s.source_matches(left,right))

    def test_changed_or_missing_source_warns_about_previous_paired_page(self):
        for mutation in ("change", "delete"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                data=fixture();data["snapshot"].update(commit="a"*40,workingTreeClean=True)
                root=Path(directory)/"source"
                source=root/data["evidence"][0]["file"];source.parent.mkdir(parents=True)
                source.write_bytes((ROOT/data["evidence"][0]["file"]).read_bytes())
                logic=copy.deepcopy(data);logic["layer"]="logic";logic["links"]={}
                old=s2s.prepare(logic,root)
                (Path(directory)/"logic.html").write_text(s2s.render(old))
                if mutation=="change":source.write_text(source.read_text()+"Changed after capture.\n")
                else:source.unlink()
                data["snapshot"]["workingTreeClean"]=False
                data["links"]={"logic":{"url":"logic.html","generated":True}}
                new=s2s.prepare(data,root,Path(directory)/"flow.html")
                self.assertTrue(new["links"]["logic"]["generated"])
                self.assertFalse(s2s.source_matches(new,old))
                self.assertFalse(s2s.source_matches(old,new))
                warnings=[w for w in new["warnings"] if w["kind"]=="snapshot-mismatch"]
                self.assertEqual(len(warnings),1)
                self.assertIn("logic.html",warnings[0]["message"])
                self.assertTrue(all(e["locationStatus"]=="failed" for e in new["evidence"]))
                if mutation=="delete":
                    self.assertTrue(all(e["observedContentHash"] is None for e in new["evidence"]))

    def test_dirty_or_unknown_snapshot_requires_the_whole_evidence_file_set(self):
        left=s2s.prepare(fixture(),ROOT)
        for clean in (False,None):
            with self.subTest(workingTreeClean=clean):
                left["snapshot"]["workingTreeClean"]=clean
                right=copy.deepcopy(left)
                self.assertTrue(s2s.source_matches(left,right))
                extra=copy.deepcopy(right["evidence"][0])
                extra.update(id="extra-file",file="additional.txt")
                right["evidence"].append(extra)
                self.assertFalse(s2s.source_matches(left,right))
                self.assertFalse(s2s.source_matches(right,left))

    def test_clean_shared_commit_needs_a_reread_for_different_evidence_files(self):
        left=s2s.prepare(fixture(),ROOT)
        left["snapshot"].update(commit="a"*40,workingTreeClean=True)
        right=copy.deepcopy(left)
        for e in right["evidence"]:e["file"]="another-file.txt"
        self.assertFalse(s2s.source_matches(left,right))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=ROOT/left["evidence"][0]["file"]
            source=root/left["evidence"][0]["file"];source.parent.mkdir(parents=True)
            source.write_bytes(original.read_bytes())
            (root/"another-file.txt").write_bytes(original.read_bytes())
            self.assertTrue(s2s.source_matches(left,right,root))
            self.assertTrue(s2s.source_matches(right,left,root))
            (root/"another-file.txt").write_text("Changed since the linked page was built.\n")
            self.assertFalse(s2s.source_matches(left,right,root))
            self.assertFalse(s2s.source_matches(right,left,root))
        right["evidence"][0]["locationStatus"]="failed"
        self.assertFalse(s2s.source_matches(left,right))

    def test_passed_output_rejects_missing_or_conflicting_observed_hashes(self):
        original=s2s.prepare(fixture(),ROOT)
        for value in (None,"a"*64):
            with self.subTest(observedContentHash=value):
                data=copy.deepcopy(original);data["evidence"][0]["observedContentHash"]=value
                with self.assertRaisesRegex(s2s.InvalidGraph,"captured and observed"):
                    s2s.validate(data,"render")

    def test_older_pages_without_observed_hash_remain_readable(self):
        current=s2s.prepare(fixture(),ROOT);legacy=copy.deepcopy(current)
        for e in legacy["evidence"]:del e["observedContentHash"]
        s2s.validate(legacy,"render")
        self.assertTrue(s2s.source_matches(current,legacy))


if __name__=="__main__":
    unittest.main()

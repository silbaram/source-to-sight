import copy
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/codebase-atlas/scripts'))
sys.path.insert(0,str(ROOT/'scripts'))
import atlas
import evaluate
import evaluate_atlas

s2s,author=atlas.companion()


class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'api.py').write_text('def convert(value):\n    return str(value)\n\ndef inspect(value):\n    return type(value).__name__\n')
        subprocess.run(['git','init','-q',str(self.source)],check=True)
        subprocess.run(['git','-C',str(self.source),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.source),'-c','user.name=Atlas Test','-c','user.email=atlas@example.invalid','commit','-qm','fixture'],check=True)
        self.behavior=author.draft(self.source,'Explain conversion','Conversion','pkg','convert',['String conversion'],['Callers'],['cli-utility'],language='en')
        evidence=author.capture_evidence(self.source,'ev-api','api.py','convert',1,2)
        claim=dict(confidence='exact',evidenceIds=['ev-api'],supportStatus='supported',verificationNote='The public function converts a supplied value.')
        self.behavior['evidence']=[evidence]
        self.behavior['nodes']=[dict(id='converter',kind='component',label='Convert a value',roleLabel='Public function',summary='Produce a string.',codeName='convert',importance='core',contextOnly=False,actions=[],**claim)]
        self.behavior['analysis'].update(status='complete',searched=['api.py'],unresolved=[],nextAttempts=[])
        self.map=copy.deepcopy(self.behavior)
        self.map['layer']='atlas';self.map['subject'].update(id='package-map',kind='project',title='Package',question='Explain the package')
        self.map['regeneration'].update(subjectId='package-map',question='Explain the package',command='$codebase-atlas Explain the package')
        self.map['subjects']=[dict(**{k:copy.deepcopy(self.behavior['subject'][k]) for k in ('id','kind','question','module','targets','scope')},
                                   label='Convert input',summary='Convert one value.',nodeId='converter',link=dict(url='details/convert.html',generated=False,command='$code-flow convert'),**claim)]
        self.map['subjects'][0]['targets']=[dict(label='convert',file='api.py',symbol='convert')]
        self.behavior['subject']['targets']=copy.deepcopy(self.map['subjects'][0]['targets'])
        self.output=self.root/'site/project.html';self.child=self.output.parent/'details/convert.html'

    def build(self,**kwargs):
        return atlas.build_site(self.map,self.source,self.output,**kwargs)

    def test_map_only_is_lazy_and_commands_resolve_target_scope_and_locations(self):
        result=self.build()[self.output]
        self.assertFalse(self.child.exists())
        command=result['subjects'][0]['link']['command']
        for value in ('convert','api.py','String conversion','Callers','language=en','locations='):self.assertIn(value,command)
        self.assertFalse(result['subjects'][0]['link']['generated'])

    def test_pair_links_match_both_directions_and_source_bodies_stay_internal(self):
        result=self.build(pages=[dict(behavior=self.behavior,output=self.child)])
        self.assertTrue(result[self.output]['subjects'][0]['link']['generated'])
        self.assertEqual(result[self.child]['links']['atlas']['url'],'../project.html')
        self.assertTrue(result[self.child]['links']['atlas']['generated'])
        for path in result:
            html=path.read_text();self.assertNotIn('def convert(value):',html)
            self.assertNotIn('anchorText',s2s.read_embedded(path)['evidence'][0])

    def test_existing_detail_without_a_matching_active_return_stays_pending(self):
        self.build()
        for parent in (None,dict(url='../other-map.html',generated=True),dict(url='../project.html',generated=False)):
            with self.subTest(parent=parent):
                child=s2s.prepare(self.behavior,self.source)
                if parent:child['links']['atlas']={**parent,'command':'$codebase-atlas Explain the package'}
                self.child.parent.mkdir(parents=True,exist_ok=True)
                self.child.write_text(s2s.render(child))
                before=self.child.read_bytes()
                result=self.build()[self.output]
                self.assertFalse(result['subjects'][0]['link']['generated'])
                self.assertEqual(self.child.read_bytes(),before)
        self.build(pages=[dict(behavior=self.behavior,output=self.child)])
        before=self.child.read_bytes()
        result=self.build()[self.output]
        self.assertTrue(result['subjects'][0]['link']['generated'])
        self.assertTrue(s2s.read_embedded(self.child)['links']['atlas']['generated'])
        self.assertEqual(self.child.read_bytes(),before)

    def test_three_layers_build_from_explicit_pages_without_fabricating_new_rules(self):
        logic=copy.deepcopy(self.behavior);logic['layer']='logic'
        logic['rules']=[dict(id='rule-output',plainText='Conversion produces a string.',condition='A value is supplied',outcome='Return its string representation',numeric=False,nodeIds=['converter'],rationale='The implementation uses the string conversion function.',
                             confidence='exact',evidenceIds=['ev-api'],supportStatus='supported',verificationNote='Checked the conversion expression.')]
        layout=dict(version=1,sections=[dict(id='contract',title='Conversion result',kind='conditions',ruleIds=['rule-output'])])
        detail=self.output.parent/'rules/convert.html'
        result=self.build(pages=[dict(behavior=self.behavior,output=self.child,logic=logic,layout=layout,logicOutput=detail)])
        self.assertTrue(result[self.child]['links']['logic']['generated'])
        self.assertTrue(result[detail]['links']['behavior']['generated'])
        self.assertTrue(result[detail]['links']['atlas']['generated'])
        self.assertIn('Conversion result',detail.read_text())

    def test_wrong_scope_target_owner_or_language_cannot_replace_pages(self):
        self.build(pages=[dict(behavior=self.behavior,output=self.child)])
        before={p:p.read_bytes() for p in (self.output,self.child)}
        for field,value in [('scope',dict(includes=['Other behavior'],excludes=[])),('targets',[dict(label='convert',file='another.py',symbol='convert')]),('module','another')]:
            with self.subTest(field=field):
                wrong=copy.deepcopy(self.behavior);wrong['subject'][field]=value
                with self.assertRaisesRegex(ValueError,'target and scope'):self.build(pages=[dict(behavior=wrong,output=self.child)])
        wrong=copy.deepcopy(self.behavior);wrong['language']=wrong['regeneration']['language']='ko'
        with self.assertRaisesRegex(ValueError,'language'):self.build(pages=[dict(behavior=wrong,output=self.child)])
        for path,content in before.items():self.assertEqual(path.read_bytes(),content)

    def test_unrelated_existing_detail_or_parent_is_not_a_navigation_link(self):
        other=copy.deepcopy(self.behavior);other['subject']['scope']['includes']=['Different scope']
        author.build(other,self.source,self.child)
        result=self.build()[self.output]
        self.assertFalse(result['subjects'][0]['link']['generated'])
        self.map['subjects']=[];self.build()
        self.behavior['links']['atlas']=dict(url='../project.html',generated=False,command='$codebase-atlas pkg')
        result=author.prepare_build(self.behavior,self.source,self.root/'site/details/new.html')
        self.assertFalse(result['links']['atlas']['generated'])

    def test_changed_evidence_disables_existing_atlas_navigation(self):
        self.build(pages=[dict(behavior=self.behavior,output=self.child)])
        (self.source/'api.py').write_text('def convert(value):\n    return value\n')
        result=self.build()[self.output]
        self.assertFalse(result['subjects'][0]['link']['generated'])
        self.assertEqual(result['subjects'][0]['displayStatus'],'unverified')

    def test_refused_child_or_output_collision_leaves_all_existing_outputs_intact(self):
        self.build();before=self.output.read_bytes()
        with self.assertRaisesRegex(ValueError,'distinct'):self.build(pages=[dict(behavior=self.behavior,output=self.output)])
        with self.assertRaisesRegex(ValueError,'distinct'):self.build(data_output=self.output)
        with self.assertRaisesRegex(ValueError,'catalog URL'):self.build(pages=[dict(behavior=self.behavior,output=self.root/'other.html')])
        self.assertEqual(self.output.read_bytes(),before)

    def test_capability_is_pruned_or_downgraded_by_its_own_evidence(self):
        self.map['subjects'][0]['supportStatus']='unsupported'
        result=self.build()[self.output];self.assertEqual(result['subjects'],[])
        self.map['subjects'][0]['supportStatus']='uncertain'
        result=self.build()[self.output];self.assertEqual(result['subjects'][0]['displayStatus'],'uncertain')
        self.assertEqual(result['nodes'][0]['displayStatus'],'confirmed')

    def test_regions_cannot_assign_the_same_node_to_different_responsibilities(self):
        claim={k:self.map['subjects'][0][k] for k in ('confidence','evidenceIds','supportStatus','verificationNote')}
        self.map['regions']=[dict(id=id,label=id,summary='Conversion responsibility.',nodeIds=['converter'],**claim) for id in ('one','two')]
        with self.assertRaisesRegex(ValueError,'disjoint'):self.build()

    def test_new_atlas_authoring_requires_scoped_source_backed_capabilities(self):
        legacy={k:self.map['subjects'][0][k] for k in ('id','label','nodeId','link')}
        self.map['subjects']=[legacy]
        s2s.validate(self.map) # Existing pages remain compatible.
        with self.assertRaisesRegex(ValueError,'resolved targets'):self.build()

    def test_separately_installed_skills_build_and_cli_protects_manifest_inputs(self):
        installed=self.root/'installed';flow=installed/'flow';maps=installed/'maps'
        shutil.copytree(ROOT/'skills/code-flow',flow,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT/'skills/codebase-atlas',maps,ignore=shutil.ignore_patterns('__pycache__'))
        internal=self.root/'atlas.json';child_input=self.root/'child.json';pages=self.root/'pages.json'
        author.write_json(internal,self.map);author.write_json(child_input,self.behavior)
        author.write_json(pages,[dict(behavior='child.json',output='details/convert.html')])
        command=[sys.executable,str(maps/'scripts/atlas.py'),'--code-flow-root',str(flow)]
        result=subprocess.run(command+['doctor'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        result=subprocess.run(command+['build',str(internal),'--pages',str(pages),'--source-root',str(self.source),'--output',str(self.output)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(self.child.is_file())
        before=internal.read_bytes()
        result=subprocess.run(command+['build',str(internal),'--source-root',str(self.source),'--output',str(internal)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertEqual(internal.read_bytes(),before)


class AtlasEvaluationTests(unittest.TestCase):
    def test_late_review_template_write_failure_fails_the_case_and_run(self):
        write_json=author.write_json
        def fail_review_template(path,data,**kwargs):
            if Path(path).name=='agent-project.review-template.json':
                raise OSError('simulated review-template write failure')
            return write_json(path,data,**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'evaluation'
            args=SimpleNamespace(manifest=str(ROOT/'eval/atlas-cases.json'),source_cache=str(ROOT/'.cache/m1-sources'),
                                 output=str(output),reviews=None,strict=False)
            with patch.object(author,'write_json',side_effect=fail_review_template),contextlib.redirect_stdout(io.StringIO()):
                exit_code=evaluate_atlas.run(args)
            report=evaluate.read(output/'results.json')
            result=next(r for r in report['results'] if r['id']=='agent-project')
            self.assertIn('evaluation-error:simulated review-template write failure',result['errors'])
            self.assertEqual(result['autoStatus'],'failed')
            self.assertEqual(result['status'],'failed')
            self.assertEqual(report['status'],'failed')
            self.assertEqual(exit_code,1)
            self.assertEqual(sum(r['autoStatus']=='passed' for r in report['results']),35)

    def prepared(self):
        graph=evaluate.read(ROOT/'eval/m5/graphs/agent-project.json')
        ref=evaluate.read(ROOT/'eval/m5/expectations/agent-project.json')
        return s2s.prepare(graph,ROOT/'.cache/m1-sources/smolagents'),ref

    def test_reference_detects_missing_region_members_and_capability_scope_drift(self):
        graph,ref=self.prepared()
        self.assertEqual(evaluate_atlas.check_atlas(graph,ref)['errors'],[])
        graph['regions'][0]['nodeIds'].pop()
        graph['subjects'][0]['scope']['includes']=['Another scope']
        graph['subjects'][0]['nodeId']='memory'
        errors=evaluate_atlas.check_atlas(graph,ref)['errors']
        self.assertIn('responsibility-membership',errors);self.assertIn('capability-target-scope',errors)
        self.assertIn('capability-owner',errors)

    def test_evaluation_roles_do_not_depend_on_map_node_ids(self):
        graph,ref=self.prepared();renames={n['id']:'new-'+n['id'] for n in graph['nodes']}
        for node in graph['nodes']:node['id']=renames[node['id']]
        for edge in graph['edges']:
            edge['from']=renames[edge['from']];edge['to']=renames[edge['to']]
        for region in graph['regions']:region['nodeIds']=[renames[id] for id in region['nodeIds']]
        for subject in graph['subjects']:subject['nodeId']=renames[subject['nodeId']]
        self.assertEqual(evaluate_atlas.check_atlas(graph,ref)['errors'],[])

    def test_review_identity_binds_supplied_detail_and_map(self):
        graph,ref=self.prepared();bundle=dict(atlas=graph,behavior={'question':'first'})
        review=evaluate.review_template(bundle,ref,'engine')
        bundle['behavior']['question']='changed'
        state,errors,_=evaluate.review_status(review,bundle,ref,'engine')
        self.assertEqual(state,'stale');self.assertTrue(errors)


if __name__=='__main__':unittest.main()

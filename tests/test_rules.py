import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/code-flow/scripts'))
sys.path.insert(0,str(ROOT/'skills/visual-primer/scripts'))
sys.path.insert(0,str(ROOT/'scripts'))
import author
import s2s
import rules
import evaluate
import evaluate_rules
from test_author import supported_graph


class RulePageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'source';self.source.mkdir()
        (self.source/'convert.py').write_text('def convert(text):\n    return text.upper()\n')
        self.base=supported_graph(self.source)
        self.base['provenance'].update(kind='synthetic',description='Synthetic contract case.')
        self.base['rules']=[dict(id='convert-rule',plainText='Text becomes upper case.',condition='Input is text',
                                  outcome='Return the upper-case text.',nodeIds=['convert'],numeric=False,
                                  confidence='exact',supportStatus='supported',verificationNote='Read the conversion.',evidenceIds=['ev-convert'])]
        self.logic=author.explain_draft(self.base,self.source)
        self.logic['analysis']=copy.deepcopy(self.base['analysis'])
        self.logic['rules'][0].update(supportStatus='supported',rationale='The function returns the upper-case conversion.',exceptions=['Other input types are outside this example.'])
        self.layout=dict(version=1,sections=[dict(id='conversion',title='What does the input become?',kind='conditions',ruleIds=['convert-rule'])])
        self.parent=self.root/'pages'/'behavior.html'
        self.child=self.root/'pages'/'why # example.html'

    def build(self,logic=None,layout=None):
        return rules.build_pair(self.base,logic or self.logic,layout or self.layout,self.source,self.parent,self.child)

    def test_rules_draft_keeps_facts_and_requires_a_new_review(self):
        draft=author.explain_draft(self.base,self.source)
        self.assertEqual(draft['layer'],'logic')
        for key in ('subject','nodes','edges','scenarios','stateTransitions','evidence'):
            self.assertEqual(draft[key],self.base[key])
        self.assertEqual(draft['rules'][0]['supportStatus'],'uncertain')
        self.assertEqual(draft['analysis']['status'],'partial')
        self.assertFalse(draft['provenance']['humanReviewed'])
        self.assertEqual(self.base['rules'][0]['supportStatus'],'supported')
        with self.assertRaises(ValueError):
            author.explain_draft(s2s.prepare(self.base,self.source),self.source)

    def test_pair_links_use_the_new_pages_and_safe_relative_urls(self):
        result=self.build()
        base,logic=result['behavior'],result['logic']
        self.assertTrue(base['links']['logic']['generated'])
        self.assertTrue(logic['links']['behavior']['generated'])
        self.assertEqual(unquote(base['links']['logic']['url']),self.child.name)
        self.assertIn('%23',base['links']['logic']['url'])
        self.assertFalse(any(w['kind']=='snapshot-mismatch' for page in (base,logic) for w in page['warnings']))
        self.assertEqual(base['nodes'],logic['nodes'])
        self.assertIn('data-viewer="primer"',self.child.read_text())
        self.assertIn('data-viewer="canvas"',self.parent.read_text())
        for p in (self.parent,self.child):
            s2s.validate(s2s.read_embedded(p),'render')
            self.assertNotIn('anchorText',p.read_text())
            self.assertNotIn('return text.upper()',p.read_text())

    def test_fact_drift_and_wrong_target_do_not_replace_either_page(self):
        self.build()
        before=[p.read_bytes() for p in (self.parent,self.child)]
        for mutate in (lambda g:g['nodes'][0].update(summary='A different effect.'),
                       lambda g:g['subject']['scope'].update(includes=['Another scope']),
                       lambda g:g['rules'][0].update(outcome='Return lower-case text.'),
                       lambda g:g.update(language='ko')):
            changed=copy.deepcopy(self.logic);mutate(changed)
            with self.assertRaises(ValueError):self.build(changed)
            self.assertEqual(before,[p.read_bytes() for p in (self.parent,self.child)])
        wrong=s2s.read_embedded(self.child);wrong['subject']['scope']['includes']=['Another subject']
        self.child.write_text(s2s.render(wrong))
        bad_bytes=self.child.read_bytes()
        with self.assertRaisesRegex(ValueError,'another subject'):self.build()
        self.assertEqual(self.child.read_bytes(),bad_bytes)
        self.assertEqual(self.parent.read_bytes(),before[0])

    def test_quantities_in_reasons_or_exceptions_are_removed_with_their_figure(self):
        for field,value in (('rationale','The limit is 7 attempts.'),('exceptions',['The exception allows 7 attempts.'])):
            with self.subTest(field=field):
                graph=copy.deepcopy(self.logic)
                graph['rules'][0].update(supportStatus='uncertain',**{field:value})
                result=self.build(graph)
                self.assertEqual(result['logic']['rules'],[])
                self.assertEqual(result['omittedSections'],['conversion'])
                self.assertNotIn('7 attempts',self.child.read_text())
                self.assertIn('withheld',self.child.read_text())

    def test_source_changes_cannot_keep_a_rules_page_confirmed(self):
        self.build()
        (self.source/'convert.py').write_text('def convert(text):\n    return text.lower()\n')
        result=self.build()
        self.assertEqual(result['logic']['rules'][0]['displayStatus'],'unverified')
        self.assertTrue(any(w['kind']=='snapshot-mismatch' for w in result['logic']['warnings']))

    def test_layout_references_reasons_and_source_body_guard(self):
        self.build();before=self.child.read_bytes()
        for mutate in (lambda l:l['sections'][0].update(ruleIds=['missing']),
                       lambda l:l['sections'].append(copy.deepcopy(l['sections'][0])),
                       lambda l:l['sections'][0].update(title='def convert(text):')):
            layout=copy.deepcopy(self.layout);mutate(layout)
            with self.assertRaises((ValueError,rules.ValidationError)):self.build(layout=layout)
            self.assertEqual(self.child.read_bytes(),before)
        missing=copy.deepcopy(self.logic);del missing['rules'][0]['rationale']
        with self.assertRaisesRegex(ValueError,'rationale'):self.build(missing)

    def test_additional_unillustrated_rules_and_output_aliases_are_rejected(self):
        graph=copy.deepcopy(self.logic)
        graph['rules'].append(dict(graph['rules'][0],id='another-rule'))
        with self.assertRaisesRegex(ValueError,'Every new rule'):self.build(graph)
        with self.assertRaisesRegex(ValueError,'different output paths'):
            rules.build_pair(self.base,self.logic,self.layout,self.source,self.parent,self.parent)
        self.assertFalse(self.parent.exists())

    def test_installed_pair_builder_needs_no_repository_helpers_and_protects_inputs(self):
        code=self.root/'separate/code-flow';primer=self.root/'installed/visual-primer'
        for source,target in ((ROOT/'skills/code-flow',code),(ROOT/'skills/visual-primer',primer)):
            shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__'))
        base,logic,layout=[self.root/name for name in ('behavior.json','logic.json','layout.json')]
        for path,data in ((base,self.base),(logic,self.logic),(layout,self.layout)):
            author.write_json(path,data)
        command=[sys.executable,str(primer/'scripts/rules.py'),'build-pair','--code-flow-root',str(code),
                 '--behavior-input',str(base),'--input',str(logic),'--layout',str(layout),
                 '--source-root',str(self.source),'--behavior-output',str(self.parent),'--output',str(self.child)]
        result=subprocess.run(command,cwd=self.root,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        before=logic.read_bytes()
        command[-1]=str(logic)
        result=subprocess.run(command,cwd=self.root,text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(logic.read_bytes(),before)


class RuleEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.graph=json.loads((ROOT/'eval/m3/graphs/agent-parallel-tools-rules.json').read_text())
        self.graph=s2s.prepare(self.graph,ROOT/'.cache/m1-sources/smolagents')
        self.layout=json.loads((ROOT/'eval/m3/layouts/agent-parallel-tools-rules.json').read_text())
        self.reference=json.loads((ROOT/'eval/m3/expectations/agent-parallel-tools-rules.json').read_text())

    def test_rule_ids_are_not_the_fact_criteria(self):
        renamed=copy.deepcopy(self.graph);layout=copy.deepcopy(self.layout)
        mapping={r['id']:'renamed-'+str(i) for i,r in enumerate(renamed['rules'])}
        for r in renamed['rules']:r['id']=mapping[r['id']]
        for section in layout['sections']:section['ruleIds']=[mapping[r] for r in section['ruleIds']]
        self.assertEqual(evaluate_rules.check_rules(renamed,layout,self.reference)['matchedRules'],5)

    def test_missing_rule_cannot_reuse_another_claim_to_pass(self):
        graph=copy.deepcopy(self.graph)
        graph['rules']=[r for r in graph['rules'] if r['id']!='configured-budget']
        result=evaluate_rules.check_rules(graph,self.layout,self.reference)
        self.assertEqual(result['matchedRules'],4)
        self.assertTrue(result['errors'])

    def test_changed_quantity_or_missing_reason_fails_coverage(self):
        for field,value in (('outcome','Use the limit 30.'),('outcome','Use the limit -20.'),('rationale','')):
            graph=copy.deepcopy(self.graph)
            rule=next(r for r in graph['rules'] if r['id']=='configured-budget')
            rule[field]=value
            self.assertTrue(evaluate_rules.check_rules(graph,self.layout,self.reference)['errors'])

    def test_review_binds_the_composition_and_behavior_as_well_as_rules(self):
        candidate=dict(graph=self.graph,layout=self.layout,behaviorHash='a'*64)
        template=evaluate.review_template(candidate,self.reference,'b'*64)
        changed=copy.deepcopy(candidate);changed['layout']['sections'].reverse()
        self.assertNotEqual(template['candidateHash'],evaluate.review_template(changed,self.reference,'b'*64)['candidateHash'])
        changed=copy.deepcopy(candidate);changed['behaviorHash']='c'*64
        self.assertNotEqual(template['candidateHash'],evaluate.review_template(changed,self.reference,'b'*64)['candidateHash'])


if __name__=='__main__':
    unittest.main()

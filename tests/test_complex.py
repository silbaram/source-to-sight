import copy
import unittest

from test_evaluate import ev, reference, rendered, ROOT


class ComplexBehaviorTests(unittest.TestCase):
    def test_missing_behavior_collections_fail_even_when_graph_relationships_remain(self):
        for case in ev.read(ROOT/'eval/cases.json')['cases'][18:]:
            for collection in ('rules', 'stateTransitions', 'scenarios'):
                with self.subTest(case=case['id'], collection=collection):
                    graph = rendered(case['id'])
                    graph[collection] = []
                    result = ev.check_graph(graph, reference(case['id']))
                    self.assertTrue(result['missingBehaviors'])
                    self.assertEqual(result['missingNodes'], [])
                    self.assertEqual(result['missingEdges'], [])

    def test_parallel_relabeling_or_removed_guard_is_detected(self):
        for change in ('sequential', None):
            graph = rendered('agent-parallel-tools')
            step = graph['scenarios'][0]['steps'][3]
            if change:
                step['execution'] = change
            else:
                del step['condition']
            self.assertIn('parallel-group', ev.check_graph(graph, reference('agent-parallel-tools'))['missingBehaviors'])

    def test_path_order_and_kind_are_checked_without_using_ids_or_captions(self):
        graph, ref = rendered('library-resize-callbacks'), reference('library-resize-callbacks')
        steps = graph['scenarios'][0]['steps']
        steps[3], steps[4] = steps[4], steps[3]
        self.assertIn('release-before-notify', ev.check_graph(graph, ref)['missingPaths'])
        graph = rendered('library-resize-callbacks')
        for scenario in graph['scenarios']:
            scenario['id'] += '-renamed'
            scenario['title'] = 'Alternative wording'
            for step in scenario['steps']:
                step['id'] += '-renamed'
                step['caption'] = 'Alternative wording; semantic review remains required'
        self.assertEqual(ev.check_graph(graph, ref)['errors'], [])
        graph['scenarios'][0]['kind'] = 'error'
        self.assertIn('release-before-notify', ev.check_graph(graph, ref)['missingPaths'])

    def test_rule_cannot_borrow_an_unrelated_evidence_location(self):
        graph = rendered('utility-retry-budget')
        graph['rules'][0]['evidenceIds'] = ['ev-predicate']
        self.assertIn('total-budget', ev.check_graph(graph, reference('utility-retry-budget'))['missingBehaviors'])

    def test_new_execution_metadata_retains_claim_validation_and_output_boundary(self):
        graph = ev.read(ROOT/'eval/m2/graphs/agent-parallel-tools.json')
        ev.s2s.validate(graph)
        source = ROOT/'.cache/m1-sources/smolagents'
        prepared = ev.s2s.prepare(graph, source)
        self.assertEqual(prepared['scenarios'][0]['steps'][3]['execution'], 'parallel')
        self.assertNotIn('anchorText', ev.s2s.render(prepared))
        graph['scenarios'][0]['steps'][3]['execution'] = 'all-finish-together'
        with self.assertRaises(ev.s2s.InvalidGraph):
            ev.s2s.validate(graph)

    def test_invalid_behavior_reference_is_rejected(self):
        for patch in ({'role':'unknown'}, {'execution':'always'}, {'line':0}, {'condition':'yes'}):
            ref = reference('agent-parallel-tools')
            ref['behaviors'][2].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                ev.validate_reference(ref, ref['caseId'])

    def test_cannot_hide_failure_paths_by_shrinking_denominators(self):
        ref = reference('agent-parallel-tools')
        # Missing candidate execution reports all required claims/paths, as it does roles.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            case = next(c for c in ev.read(ROOT/'eval/cases.json')['cases'] if c['id']==ref['caseId'])
            source = next(s for s in ev.read(ROOT/'eval/m1/sources.json') if s['id']==case['source'])
            result = ev.evaluate_case(case, source, ref, Path(tmp)/'absent.json', Path(tmp), Path(tmp), 'engine')
        self.assertEqual(result['requiredBehaviors'], len(ref['behaviors']))
        self.assertEqual(result['requiredPaths'], len(ref['paths']))
        self.assertEqual(result['matchedBehaviors'], 0)
        self.assertEqual(result['autoStatus'], 'failed')


class SuiteExtensionTests(unittest.TestCase):
    def reports(self):
        before = ev.read(ROOT/'eval/runs/2026-09-06-flow-animation.json')
        after = copy.deepcopy(before)
        after['manifestHash'] = 'expanded'
        after['suiteSize'] += 1
        after['results'].append({**copy.deepcopy(after['results'][0]), 'id':'added'})
        return before, after

    def test_extension_is_explicit_and_reports_added_cases(self):
        before, after = self.reports()
        self.assertEqual(ev.compare(before, after)['status'], 'incomparable')
        compared = ev.compare(before, after, True)
        self.assertEqual(compared['status'], 'no-regression')
        self.assertEqual(compared['comparedCases'], 18)
        self.assertEqual(compared['addedCases'], ['added'])

    def test_extension_cannot_hide_changed_references_sources_or_incomplete_coverage(self):
        for change in ('reference', 'source', 'coverage'):
            before, after = self.reports()
            if change == 'reference':
                after['results'][0]['expectationHash'] = 'changed'
            elif change == 'source':
                after['sources'][0]['commit'] = 'a'*40
            else:
                after['suiteSize'] += 1
            self.assertEqual(ev.compare(before, after, True)['status'], 'incomparable')

    def test_added_failure_missing_case_or_lost_behavior_fails(self):
        for change in ('added', 'missing', 'behavior'):
            before, after = self.reports()
            if change == 'added':
                after['results'][-1]['status'] = 'failed'
            elif change == 'missing':
                after['results'].pop(0)
            else:
                before['results'][0]['matchedBehaviors'] = 2
                after['results'][0]['matchedBehaviors'] = 1
            self.assertEqual(ev.compare(before, after, True)['status'], 'regressed')

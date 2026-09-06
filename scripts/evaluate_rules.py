#!/usr/bin/env python3
"""Evaluate the 24 behavior cases and six paired rules explanations together."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys
import time

import evaluate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/visual-primer/scripts'))
import rules


def validate_requirements(reference):
    evaluate.validate_reference(reference, reference['caseId'])
    expected = reference['ruleRequirements']
    roles = {n['key'] for n in reference['nodes']}
    if not expected or len({r['key'] for r in expected}) != len(expected):
        raise ValueError('Rule requirements need unique keys.')
    for item in expected:
        if (item['role'] not in roles or not evaluate.s2s.relative_path(item['file']) or
                type(item['line']) is not int or item['line'] < 1 or
                type(item['numeric']) is not bool or item['status'] not in {'confirmed','uncertain','unverified'} or
                any(type(item[k]) is not bool for k in ('rationale','exceptions')) or
                not isinstance(item['values'], list) or
                any(not isinstance(v,str) or not re.fullmatch(r'[+-]?\d+(?:\.\d+)?',v) for v in item['values'])):
            raise ValueError('Invalid rule source/contract criterion.')
    if not reference['figureKinds'] or not set(reference['figureKinds']) <= {'comparison','conditions','states'}:
        raise ValueError('Invalid required figure kinds.')


def check_rules(graph, layout, reference):
    """One-to-one source/role/quantity coverage, independent of authored rule IDs."""
    validate_requirements(reference)
    roles = evaluate.match_roles(graph, reference)
    owners = {key: matches[0]['id'] for key,matches in roles.items() if len(matches) == 1}
    evidence = {e['id']: e for e in graph['evidence']}
    illustrated = {identifier for s in layout['sections'] for identifier in s['ruleIds']}
    choices = []
    for expected in reference['ruleRequirements']:
        found = []
        for i, rule in enumerate(graph['rules']):
            if rule['id'] not in illustrated or owners.get(expected['role']) not in rule['nodeIds']:
                continue
            if evaluate.s2s.numerical_rule(rule) != expected['numeric'] or rule['displayStatus'] != expected['status']:
                continue
            if any(bool(rule.get(k)) != expected[k] for k in ('rationale','exceptions')):
                continue
            prose = ' '.join(evaluate.s2s.strings({k:rule.get(k,'') for k in ('plainText','condition','outcome','rationale','exceptions')}))
            if set(re.findall(r'[+-]?\d+(?:\.\d+)?',prose)) != set(expected['values']):
                continue
            if any(evidence[e]['file'] == expected['file'] and evidence[e]['startLine'] <= expected['line'] <= evidence[e]['endLine'] for e in rule['evidenceIds']):
                found.append(i)
        choices.append(found)
    assigned = {}
    def assign(expected, seen):
        for candidate in choices[expected]:
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate not in assigned or assign(assigned[candidate], seen):
                assigned[candidate] = expected
                return True
        return False
    for i in range(len(choices)):
        assign(i,set())
    missing = [r['key'] for i,r in enumerate(reference['ruleRequirements']) if i not in assigned.values()]
    errors = ['rule-missing:'+key for key in missing]
    kinds = {s['kind'] for s in layout['sections']}
    errors += ['figure-kind-missing:'+kind for kind in set(reference['figureKinds'])-kinds]
    return dict(requiredRules=len(choices),matchedRules=len(assigned),missingRules=missing,errors=errors)


def load_manifest(path):
    manifest = evaluate.read(path)
    root = Path(path).resolve().parent
    if manifest['version'] != 1:
        raise ValueError('Unsupported rules manifest version.')
    base_path = evaluate.within(root,manifest['behaviorManifest'])
    base, sources = evaluate.load_suite(base_path)
    if len(base['cases']) != 24:
        raise ValueError('M3 preserves the full 24-case behavior suite.')
    parents = {c['id']:c for c in base['cases']}
    cases = manifest['cases']
    if len(cases) != 6 or {c['profile'] for c in cases} != set(evaluate.author.PROFILES):
        raise ValueError('M3 needs one rules case for each of the six profiles.')
    if len({c['id'] for c in cases}) != len(cases) or len({c['behaviorId'] for c in cases}) != len(cases):
        raise ValueError('Duplicate rule case or parent behavior.')
    for case in cases:
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,95}',case['id']) or case['id'] in parents:
            raise ValueError('Invalid or colliding rules case ID.')
        parent = parents[case['behaviorId']]
        if case['source'] != parent['source'] or case['profile'] != parent['profile'] or case['variant'] != 'rules':
            raise ValueError('Rule case disagrees with its behavior profile/source.')
        for key in ('candidate','expectation','layout'):
            evaluate.within(root,case[key])
        reference = evaluate.read(evaluate.within(root,case['expectation']))
        validate_requirements(reference)
        if reference['caseId'] != case['id'] or reference['identity']['layer'] != 'logic':
            raise ValueError('Rule reference identity mismatch.')
    return manifest, root, base_path, parents, sources


def evaluate_case(case, parent, root, source_cache, output, fingerprint, reviews=None):
    start=time.perf_counter()
    reference=evaluate.read(evaluate.within(root,case['expectation']))
    result=dict(id=case['id'],profile=case['profile'],variant='rules',expectationHash=evaluate.digest(reference),
                candidateHash=None,autoStatus='failed',status='failed',reviewStatus='pending',errors=[],criticalErrors=[],
                requiredRules=len(reference['ruleRequirements']),matchedRules=0,missingRules=[r['key'] for r in reference['ruleRequirements']],
                requiredNodes=len(reference['nodes']),matchedNodes=0,requiredEdges=len(reference['edges']),matchedEdges=0,
                requiredBehaviors=len(reference.get('behaviors',[])),matchedBehaviors=0,requiredPaths=len(reference.get('paths',[])),matchedPaths=0,
                metrics=dict(generationSeconds=None,inputTokens=None,outputTokens=None,costUSD=None,model=None))
    try:
        behavior=evaluate.read(evaluate.within(root,parent['candidate']))
        graph=evaluate.read(evaluate.within(root,case['candidate']))
        layout=evaluate.read(evaluate.within(root,case['layout']))
        candidate=dict(graph=graph,layout=layout,behaviorHash=evaluate.digest(behavior))
        result['candidateHash']=evaluate.digest(candidate)
        expected=reference['identity']
        if any(graph[k] != expected[k] for k in ('language','layer')) or any(graph['subject'][k] != expected['subject'][k] for k in ('id','kind','question','module','targets','scope')) or graph['analysis']['profiles'] != reference['profiles']:
            raise ValueError('candidate-target-scope-profile-mismatch')
        source=evaluate.within(source_cache,case['source'])
        snap=evaluate.author.snapshot(source)
        if snap['commit'] != behavior['snapshot']['commit'] or snap['workingTreeClean'] is not True:
            raise ValueError('source-checkout-must-be-clean-at-pin')
        pair=rules.build_pair(behavior,graph,layout,source,output/(parent['id']+'.html'),output/(case['id']+'.html'),output/(case['id']+'.render.json'))
        evaluate.author.write_json(output/(parent['id']+'.render.json'),pair['behavior'])
        prepared=pair['logic']
        result.update(evaluate.check_graph(prepared,reference))
        checked=check_rules(prepared,layout,reference)
        result['errors'] += checked.pop('errors')
        result.update(checked)
        if pair['omittedSections']:
            result['errors'].append('required-figure-withheld')
        if not pair['logic']['links']['behavior']['generated'] or not pair['behavior']['links']['logic']['generated']:
            result['errors'].append('pair-link-unresolved')
        if any(w['kind']=='snapshot-mismatch' for g in (pair['logic'],pair['behavior']) for w in g['warnings']):
            result['errors'].append('pair-source-mismatch')
        result['analysisStatus']=prepared['analysis']['status']
        review_path=evaluate.within(reviews,case['id']+'.json') if reviews else None
        review=evaluate.read(review_path) if review_path and review_path.exists() else None
        state,human_errors,critical=evaluate.review_status(review,candidate,reference,fingerprint)
        result['autoStatus']='failed' if result['errors'] or result['criticalErrors'] else 'passed'
        result['reviewStatus']=state
        result['errors'] += human_errors
        result['criticalErrors'] += critical
        result['status']='failed' if result['errors'] or result['criticalErrors'] else 'passed' if state=='passed' else 'pending-review'
        ranges={(e['file'],e['startLine'],e['endLine']) for e in graph['evidence']}
        result['metrics'].update(evidenceFiles=len({e['file'] for e in graph['evidence']}),evidenceRanges=len(ranges),
                                 evidenceLines=evaluate.evidence_line_count(ranges),recordedSearchEntries=len(set(graph['analysis']['searched'])),
                                 skillVersion=graph['snapshot']['skillVersion'])
        result['layoutHash']=evaluate.digest(layout)
        result['recordedCandidate']=dict(generatedAt=graph['snapshot']['generatedAt'],provenance=graph['provenance']['description'],origin='m3-source-reading')
        evaluate.author.write_json(output/(case['id']+'.review-template.json'),evaluate.review_template(candidate,reference,fingerprint),exclusive=True)
    except (OSError,ValueError,KeyError,TypeError,rules.ValidationError) as error:
        result['errors'].append('evaluation-error:'+str(error))
        result['autoStatus']=result['status']='failed'
    result['metrics']['evaluationSeconds']=round(time.perf_counter()-start,4)
    return result


def run(args):
    manifest,root,base_path,parents,sources=load_manifest(args.manifest)
    output=Path(args.output).resolve()
    base_args=argparse.Namespace(manifest=base_path,source_cache=args.source_cache,output=output,
                                 candidates=None,reviews=args.reviews,case=None,strict=False)
    evaluate.run(base_args)  # The new directory is reserved before any output.
    report=evaluate.read(output/'results.json')
    behavior_report=copy.deepcopy(report)
    fingerprint=evaluate.engine_hash()
    for case in manifest['cases']:
        result=evaluate_case(case,parents[case['behaviorId']],root,args.source_cache,output,fingerprint,args.reviews)
        report['results'].append(result)
        print(f"{case['id']}: automatic={result['autoStatus']}; rules={result['matchedRules']}/{result['requiredRules']}; gate={result['status']}")
    report['suiteSize']=30
    report['manifestHash']=evaluate.digest(dict(behavior=evaluate.read(base_path),rules=manifest))
    report['profiles']=evaluate.summarize(report['results'])
    report['status']='failed' if any(r['status']=='failed' for r in report['results']) else 'passed' if all(r['status']=='passed' for r in report['results']) else 'pending-review'
    report['behaviorSuiteSize']=24
    report['rulesSuiteSize']=6
    evaluate.author.write_json(output/'behavior-results.json',behavior_report,exclusive=True)
    evaluate.author.write_json(output/'results.json',report)
    detail='\n## Rules and reasons\n\n| Case | Rules matched | Figures |\n| --- | ---: | --- |\n'
    for case in manifest['cases']:
        result=next(r for r in report['results'] if r['id']==case['id'])
        ref=evaluate.read(evaluate.within(root,case['expectation']))
        detail+=f"| {case['id']} | {result['matchedRules']}/{result['requiredRules']} | {', '.join(ref['figureKinds'])} |\n"
    (output/'report.md').write_text(evaluate.markdown(report)+detail,encoding='utf-8')
    return 1 if report['status']=='failed' or (args.strict and report['status']!='passed') else 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default=str(ROOT/'eval/rules-cases.json'))
    parser.add_argument('--source-cache',default=str(ROOT/'.cache/m1-sources'))
    parser.add_argument('--output',required=True)
    parser.add_argument('--reviews')
    parser.add_argument('--strict',action='store_true')
    args=parser.parse_args(argv)
    try:
        return run(args)
    except (OSError,ValueError,KeyError,TypeError,rules.ValidationError) as error:
        parser.exit(2,f'evaluate-rules: {error}\n')


if __name__=='__main__':
    raise SystemExit(main())

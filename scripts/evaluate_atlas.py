#!/usr/bin/env python3
"""Replay the 30 behavior/rules cases and six source-backed project maps."""
import argparse
import copy
from pathlib import Path
import sys
import time
from jsonschema import ValidationError

import evaluate
import evaluate_rules

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/codebase-atlas/scripts'))
import atlas


def check_atlas(graph, reference):
    result=evaluate.check_graph(graph,reference)
    roles=evaluate.match_roles(graph,reference)
    mapped={key:items[0]['id'] for key,items in roles.items() if len(items)==1}
    expected=[frozenset(mapped.get(role, '') for role in group) for group in reference['regions']]
    actual=[frozenset(r['nodeIds']) for r in graph['regions']]
    if sorted(map(sorted,expected))!=sorted(map(sorted,actual)):
        result['errors'].append('responsibility-membership')
    if any(r['displayStatus']!='confirmed' for r in graph['regions']):
        result['errors'].append('responsibility-evidence')
    wanted={s['id']:s for s in reference['capabilities']}
    found={s['id']:s for s in graph['subjects']}
    if set(wanted)!=set(found) or any(not evaluate.s2s.subject_matches(s,found.get(k,{})) for k,s in wanted.items() if k in found):
        result['errors'].append('capability-target-scope')
    if any('scope' not in s or s.get('displayStatus')!='confirmed' for s in graph['subjects']):
        result['errors'].append('capability-evidence')
    if any(s['id'] in found and found[s['id']]['nodeId']!=mapped.get(s['ownerRole']) for s in reference['capabilities']):
        result['errors'].append('capability-owner')
    result['requiredRegions']=len(expected)
    result['matchedRegions']=sum(g in actual for g in expected)
    result['requiredCapabilities']=len(wanted)
    result['matchedCapabilities']=sum(k in found and evaluate.s2s.subject_matches(s,found[k]) for k,s in wanted.items())
    return result


def run(args):
    manifest=evaluate.read(args.manifest)
    root=Path(args.manifest).resolve().parent
    sources={s['id']:s for s in evaluate.read(evaluate.within(root,manifest['sources']))}
    cases=manifest['cases']
    if manifest['version']!=1 or len(cases)!=6 or len({c['id'] for c in cases})!=6 or {c['profile'] for c in cases}!=set(evaluate.author.PROFILES) or len({c['source'] for c in cases})!=6:
        raise ValueError('Atlas evaluation needs six distinct cases, sources and profiles.')
    output=Path(args.output).resolve()
    evaluate_rules.run(argparse.Namespace(manifest=str(ROOT/'eval/rules-cases.json'),source_cache=args.source_cache,
                                          output=str(output),reviews=args.reviews,strict=False))
    report=evaluate.read(output/'results.json')
    # Keep the base suite's report separate; reviewer files are not replaced.
    evaluate.author.write_json(output/'rules-results.json',copy.deepcopy(report),exclusive=True)
    fingerprint=evaluate.engine_hash()
    for case in cases:
        started=time.perf_counter()
        graph=evaluate.read(evaluate.within(root,case['candidate']))
        behavior=evaluate.read(evaluate.within(root,case['behaviorInput']))
        logic=evaluate.read(evaluate.within(root,case['logicInput']))
        layout=evaluate.read(evaluate.within(root,case['layout']))
        additional=[dict(id=item['id'],graph=evaluate.read(evaluate.within(root,item['input'])))
                    for item in case.get('additionalBehaviors',[])]
        reference=evaluate.read(evaluate.within(root,case['expectation']))
        evaluate.validate_reference(reference,case['id'])
        bundle=dict(atlas=graph,behavior=behavior,logic=logic,layout=layout)
        if additional:
            bundle['additionalBehaviors']=additional
        result=dict(id=case['id'],profile=case['profile'],variant='atlas',candidateHash=evaluate.digest(bundle),expectationHash=evaluate.digest(reference),
                    autoStatus='failed',status='failed',reviewStatus='pending',errors=[],criticalErrors=[],requiredNodes=len(reference['nodes']),matchedNodes=0,
                    requiredEdges=len(reference['edges']),matchedEdges=0,requiredBehaviors=0,matchedBehaviors=0,requiredPaths=0,matchedPaths=0,
                    metrics=dict(generationSeconds=None,inputTokens=None,outputTokens=None,costUSD=None,model=None))
        try:
            expected=reference['identity']
            if any(graph[k]!=expected[k] for k in ('layer','language','subject')) or graph['analysis']['profiles']!=reference['profiles']:
                raise ValueError('candidate-target-scope-profile-mismatch')
            source=sources[case['source']]
            source_root=Path(args.source_cache)/case['source']
            snapshot=evaluate.author.snapshot(source_root)
            if any(graph['snapshot'][k]!=source[k] for k in ('repository','commit')) or snapshot['commit']!=source['commit'] or snapshot['workingTreeClean'] is not True:
                raise ValueError('source-checkout-must-be-clean-at-pin')
            target=output/(case['id']+'.html')
            page=dict(behavior=behavior,output=output/(case['behaviorId']+'.html'),logic=logic,layout=layout,logicOutput=output/(case['behaviorId']+'-rules.html'))
            pages=[page]+[dict(behavior=item['graph'],output=evaluate.within(output,item['id']+'.html')) for item in additional]
            built=atlas.build_site(graph,source_root,target,pages=pages,data_output=output/(case['id']+'.render.json'))
            prepared=built[target]
            result.update(check_atlas(prepared,reference))
            result['analysisStatus']=prepared['analysis']['status']
            if any(not any(s['id']==item['behavior']['subject']['id'] and s['link']['generated'] for s in prepared['subjects']) for item in pages):
                result['errors'].append('missing-child-link')
            for path,data in built.items():
                # Adding a parent link changes the child's render data too.
                # Keep the inspection artifact identical to its final HTML.
                if path!=target:
                    evaluate.author.write_json(path.with_suffix('.render.json'),data)
                if path!=target and not data['links']['atlas']['generated']:
                    result['errors'].append('missing-parent-link')
                if data['layer']=='logic' and not data['links']['behavior']['generated']:
                    result['errors'].append('missing-behavior-link')
            if not built[page['output']]['links']['logic']['generated']:
                result['errors'].append('missing-logic-link')
            result['renderedPages']=[path.name for path in built]
            result['availableCapabilities']=sum(s['link']['generated'] for s in prepared['subjects'])
            result['pendingCapabilities']=sum(not s['link']['generated'] for s in prepared['subjects'])
            review_path=evaluate.within(args.reviews,case['id']+'.json') if args.reviews else None
            review=evaluate.read(review_path) if review_path and review_path.exists() else None
            state,errors,critical=evaluate.review_status(review,bundle,reference,fingerprint)
            result['autoStatus']='failed' if result['errors'] or result['criticalErrors'] else 'passed'
            result['reviewStatus']=state
            result['errors']+=errors;result['criticalErrors']+=critical
            result['status']='failed' if result['errors'] or result['criticalErrors'] else 'passed' if state=='passed' else 'pending-review'
            ranges={(e['file'],e['startLine'],e['endLine']) for e in graph['evidence']}
            result['metrics'].update(evidenceFiles=len({e['file'] for e in graph['evidence']}),evidenceLines=evaluate.evidence_line_count(ranges),skillVersion=evaluate.author.VERSION)
            evaluate.author.write_json(output/(case['id']+'.review-template.json'),evaluate.review_template(bundle,reference,fingerprint),exclusive=True)
        except (OSError,ValueError,KeyError,TypeError,ValidationError) as error:
            result['errors'].append('evaluation-error:'+str(error))
            result['autoStatus']=result['status']='failed'
        result['metrics']['evaluationSeconds']=round(time.perf_counter()-started,4)
        report['results'].append(result)
        print(f"{case['id']}: automatic={result['autoStatus']}; {result['errors']}")
    report.update(suiteSize=36,atlasSuiteSize=6,engineHash=fingerprint,profiles=evaluate.summarize(report['results']),
                  manifestHash=evaluate.digest(dict(base=report['manifestHash'],atlas=manifest)))
    report['status']='failed' if any(r['status']=='failed' for r in report['results']) else 'passed' if all(r['status']=='passed' for r in report['results']) else 'pending-review'
    evaluate.author.write_json(output/'results.json',report)
    detail='\n## Project maps\n\n| Map | Regions | Capabilities | Generated / pending details |\n| --- | ---: | ---: | --- |\n'
    for row in report['results'][-6:]:
        detail+=f"| {row['id']} | {row.get('matchedRegions',0)}/{row.get('requiredRegions',0)} | {row.get('matchedCapabilities',0)}/{row.get('requiredCapabilities',0)} | {row.get('availableCapabilities',0)} / {row.get('pendingCapabilities',0)} |\n"
    detail+='\nSix maps connect to explicitly supplied detail inputs, including one behavior/rules pair per map. Additional behavior pages retain their original evaluation cases. The utility rules companion belongs to the utility map case; it is not an independent-generation sample.\n'
    (output/'report.md').write_text(evaluate.markdown(report)+detail,encoding='utf-8')
    return 1 if report['status']=='failed' or (args.strict and report['status']!='passed') else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default=str(ROOT/'eval/atlas-cases.json'))
    parser.add_argument('--source-cache',default=str(ROOT/'.cache/m1-sources'))
    parser.add_argument('--output',required=True)
    parser.add_argument('--reviews')
    parser.add_argument('--strict',action='store_true')
    args=parser.parse_args()
    try:return run(args)
    except (OSError,ValueError,KeyError,TypeError,ValidationError) as error:parser.exit(2,f'evaluate-atlas: {error}\n')


if __name__=='__main__':sys.exit(main())

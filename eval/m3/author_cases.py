"""Replay six reviewed M3 rule additions; this is not automatic discovery.

Read discovery.md and the pinned source before changing these claims. Reference
selectors and human facts below are authored criteria, not extracted from prose.
Existing reference files are preserved until deliberately revised.
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'skills/code-flow/scripts'))
import author
import s2s

OUT = ROOT / 'eval/m3'
SOURCES = {s['repository']: s for s in json.loads((ROOT / 'eval/m1/sources.json').read_text())}
CASES = []


def begin(key, title, purpose):
    base = json.loads((ROOT / f'eval/m2/graphs/{key}.json').read_text())
    source = ROOT / '.cache/m1-sources' / SOURCES[base['snapshot']['repository']]['id']
    graph = author.explain_draft(base, source)
    checked = s2s.verify_locations(copy.deepcopy(base), source)
    assert all(e['locationStatus'] == 'passed' for e in checked['evidence'])
    graph['snapshot'] = author.snapshot(source, base['snapshot']['repository'])
    graph['analysis'] = copy.deepcopy(base['analysis'])
    graph['summary'].update(title=title, purpose=purpose)
    graph['provenance'].update(humanReviewed=False, description='고정 소스를 재독해한 M3 규칙 설명 후보입니다. 계산 예시는 실행 기록이 아닙니다.')
    return graph


def explain(graph, identifier, reason, *exceptions):
    rule = next(r for r in graph['rules'] if r['id'] == identifier)
    rule.update(rationale=reason, exceptions=list(exceptions), supportStatus='supported',
                verificationNote='조건·결과·이유·예외의 적용 범위를 고정 소스에서 재독해했습니다.')


def add(graph, identifier, owner, condition, outcome, reason, evidence, exceptions, numeric=False):
    graph['rules'].append(dict(id=identifier, nodeIds=owner.split(), condition=condition, outcome=outcome,
                               plainText=condition+'이면 '+outcome, rationale=reason, exceptions=exceptions,
                               numeric=numeric, confidence='exact', supportStatus='supported',
                               evidenceIds=evidence.split(), verificationNote='추가 조건과 결과를 호출부·분기·상태 쓰기에서 확인했습니다.'))


def figure(identifier, title, kind, rules, states=None):
    result = dict(id=identifier, title=title, kind=kind, ruleIds=rules.split())
    if states:
        result['transitionIds'] = states.split()
    return result


def requirement(key, role, file, line, numeric=False, values=()):
    return dict(key=key, role=role, file=file, line=line, numeric=numeric, values=list(values),
                rationale=True, exceptions=True, status='confirmed')


def finish(key, graph, sections, requirements, facts, forbidden):
    assert all(r.get('rationale') for r in graph['rules'])
    s2s.validate(graph)
    layout = dict(version=1, sections=sections)
    reference = json.loads((ROOT / f'eval/m2/expectations/{key}.json').read_text())
    identifier = key + '-rules'
    reference['caseId'] = identifier
    reference['identity']['layer'] = 'logic'
    reference['requiredFacts'] += facts
    reference['forbiddenClaims'] += forbidden
    reference['ruleRequirements'] = requirements
    reference['figureKinds'] = sorted({s['kind'] for s in sections})
    for folder, data in (('graphs', graph), ('layouts', layout)):
        author.write_json(OUT / folder / f'{identifier}.json', data)
    reference_path = OUT / 'expectations' / f'{identifier}.json'
    if not reference_path.exists():
        author.write_json(reference_path, reference, exclusive=True)
    source = SOURCES[graph['snapshot']['repository']]
    CASES.append(dict(id=identifier, behaviorId=key, source=source['id'], profile=graph['analysis']['profiles'][0],
                      variant='rules', candidate=f'm3/graphs/{identifier}.json',
                      layout=f'm3/layouts/{identifier}.json', expectation=f'm3/expectations/{identifier}.json'))


def utility():
    key='utility-retry-budget'; f='src/smolagents/utils.py'; m='src/smolagents/models.py'
    g=begin(key,'재시도는 몇 번까지, 어떤 실패에서 계속될까요?','최초 호출도 시도 횟수에 포함합니다. 호출자가 정한 정책과 실패 조건을 함께 비교합니다.')
    explain(g,'attempt-budget','반복의 번호가 최초 호출부터 시작하고, 성공하면 즉시 반환하기 때문에 한계 전체를 반드시 쓰지는 않습니다.','양수 시도 한계에 대한 설명입니다. 함수의 성공과 부작용 복구를 보장하지 않습니다.')
    explain(g,'api-budget','ApiModel은 재시도를 켰을 때 자체 정책 상수를 제어기에 전달합니다. 기본 제어기를 직접 생성한 경우와 정책이 다릅니다.','실패 판정이 재시도를 허용하고 시도가 남아 있을 때만 추가 호출합니다.')
    explain(g,'stop-error','중단 판정이 대기 갱신보다 먼저 실행됩니다. reraise의 두 분기 모두 현재 예외를 다시 발생시킵니다.','판정 함수와 로깅 함수 자체의 실패는 이 설명 범위 밖입니다.')
    explain(g,'wait-update','다음 시도 전에는 이전 지연에 증가 배율과 임의 배율을 먼저 곱하고, 갱신한 값이 양수일 때 기다립니다.','지터가 켜져 있어 실제 대기 시간을 하나의 확정값으로 표시하지 않습니다.')
    add(g,'retry-disabled','config','ApiModel에서 retry를 끈 경우','최초 호출을 포함해 총 1회만 시도합니다. 실패하면 추가 호출 없이 예외를 돌려줍니다.','제어기에 전달하는 총 시도 한계를 1로 바꾸므로 최초 실패가 마지막 실패이기도 합니다.','ev-config ev-call',['함수가 반환한 반복자를 나중에 순회하다 발생한 오류는 이 호출 재시도 범위 밖입니다.'],True)
    sections=[figure('policy','호출 정책에 따라 한계가 어떻게 달라질까요?','comparison','api-budget retry-disabled'),
              figure('stop','한계가 남아 있어도 왜 중단할까요?','conditions','attempt-budget stop-error'),
              figure('wait','다음 대기는 어떻게 정해질까요?','states','wait-update','delay-grows')]
    req=[requirement('attempts','controller',f,555,True,('1',)),requirement('api-enabled','policy',m,1175,True,('1','2','3')),
         requirement('api-disabled','policy',m,1175,True,('1',)),requirement('stop','controller',f,576),requirement('delay','wait',f,592,True,('60',))]
    finish(key,g,sections,req,['최초 호출을 포함한 총 시도와 추가 재시도를 구분한다.','ApiModel의 정책과 직접 만든 제어기의 기본 정책이 다르다.','첫 대기 전 지연을 갱신하고 중단 분기에서는 기다리지 않는 이유를 설명한다.'],['모든 오류가 정해진 횟수만큼 재시도된다고 설명하지 않는다.'])


def framework():
    key='plugin-wrapper-unwind'; f='src/pluggy/_callers.py'
    g=begin(key,'첫 결과가 나와도 래퍼는 왜 다시 실행될까요?','일반 구현의 순회와 이미 진입한 래퍼의 복귀는 서로 다른 조건으로 진행됩니다.')
    explain(g,'first-result','일반 구현의 결과를 모으는 반복만 중단합니다. 이미 저장한 래퍼의 복귀는 뒤의 finally에서 별도로 진행합니다.','래퍼가 결과나 예외를 바꿀 수 있으므로 첫 구현의 반환값이 최종값이라고 보장하지 않습니다.')
    explain(g,'wrapper-result','첫 yield까지 진입한 래퍼를 목록에 저장하고 역순으로 재개합니다. 래퍼의 종료값을 새 결과로 쓰는 분기는 처리 중 예외도 지웁니다.','실제 래퍼 구현이 어떤 결과나 예외를 만들지는 이 범위에서 확정하지 않습니다.')
    add(g,'none-continues','dispatch','firstresult가 켜져 있지만 일반 구현이 None을 반환한 경우','이 반환값 때문에 순회를 중단하지 않습니다. 남은 구현이 있으면 계속 확인합니다.','None이 아닌 반환값을 결과 목록에 넣는 분기 안에서만 첫 결과 중단을 검사합니다.','ev-first',['남은 구현의 예외나 실제 반환값은 별도입니다. 전부 None이면 래퍼 복귀 전 결과도 None입니다.'])
    finish(key,g,[figure('result','어떤 반환값에서 순회를 멈출까요?','comparison','first-result none-continues'),figure('wrapper','래퍼는 어떻게 나중의 복귀를 준비할까요?','states','wrapper-result','wrapper-pushed')],
           [requirement('first','runner',f,128),requirement('none','runner',f,128),requirement('unwind','unwind',f,161)],
           ['None과 None이 아닌 반환값의 첫 결과 중단 조건을 비교한다.','일반 구현 중단 후에도 finally에서 래퍼를 복귀시키는 이유를 설명한다.','래퍼 종료값으로 결과와 예외 상태가 바뀔 수 있다.'],['첫 결과가 생기면 모든 래퍼를 건너뛴다고 설명하지 않는다.'])


def library():
    key='library-resize-callbacks'; f='lru.go'; inner='simplelru/lru.go'
    g=begin(key,'용량을 줄인 뒤 콜백이 실패하면 무엇이 남을까요?','먼저 캐시의 항목과 용량을 바꾸고, 잠금을 해제한 뒤 사용자 콜백을 호출합니다.')
    explain(g,'remove-count','현재 항목 수와 새 용량의 차이가 음수이면 제거 수를 없애고, 필요한 제거 반복을 마친 뒤 용량을 기록합니다.','새 용량이 음수인 입력은 이 수량 계약의 범위 밖입니다.')
    explain(g,'callback-order','내부 제거가 모아 둔 알림을 지역 목록으로 분리하고 새 버퍼를 준비한 뒤 잠금을 해제합니다. 사용자 콜백은 그 다음에 호출합니다.','콜백이 없거나 제거한 항목이 없으면 이 알림 반복을 실행하지 않습니다.')
    explain(g,'callback-panic','콜백 반복 앞에서 캐시 변경과 잠금 해제가 끝났고, 이 함수 안에는 panic 복구나 변경을 되돌리는 경로가 없습니다.','호출자나 콜백 내부에 별도의 복구 처리가 있는지는 설명하지 않습니다.')
    add(g,'shrink-example','inner','계산 예시: 현재 항목 4개, 새 용량 2','오래된 항목 2개를 제거하고 용량을 2로 바꿉니다.','확인한 제거 공식에 입력을 대입한 예시입니다. 현재 항목 수에서 새 용량을 뺀 만큼 제거합니다.','ev-inner ev-remove',['실제 프로그램 실행 결과를 측정한 예시는 아닙니다.'],True)
    add(g,'grow-example','inner','계산 예시: 현재 항목 2개, 새 용량 4','제거 수는 0이며 용량을 4로 바꿉니다. 항목을 새로 채우지는 않습니다.','현재 항목 수보다 용량이 크면 차이를 0으로 보정해 제거 반복을 건너뜁니다.','ev-inner',['용량을 늘리는 것과 항목을 추가하는 것은 별개입니다.'],True)
    finish(key,g,[figure('size','줄이거나 늘리면 항목은 어떻게 될까요?','comparison','shrink-example grow-example'),figure('capacity','새 용량은 언제 기록될까요?','states','remove-count','size-updated'),figure('callback','콜백 실행과 실패는 무엇을 바꿀까요?','conditions','callback-order callback-panic')],
           [requirement('count','resize',inner,157,True,('0',)),requirement('shrink','resize',inner,157,True,('2','4')),requirement('grow','resize',inner,157,True,('0','2','4')),requirement('callback','api',f,195),requirement('panic','notify',f,198)],
           ['입력 계산 예시는 실제 실행 기록이 아니라 확인한 수식의 적용이다.','제거 반복 뒤 용량 기록, 잠금 해제 뒤 콜백이라는 순서가 실패 후 남는 상태를 설명한다.'],['콜백 실패가 용량 변경과 제거를 자동으로 되돌린다고 설명하지 않는다.'])


def agent():
    key='agent-parallel-tools'; f='src/smolagents/agents.py'
    g=begin(key,'에이전트는 어떤 한계를 쓰고, 실패 뒤에는 어떻게 될까요?','실행별 한계 선택, 오류 처리, 병렬 도구 결과의 기록 규칙을 비교합니다.')
    explain(g,'effective-budget','run이 호출별 한계를 선택해 반복기에 전달합니다. 반복기는 단계 번호를 기준으로 한계를 확인하므로 한 단계 안의 도구 개수와 구분됩니다.','양수 호출별 한계에 대한 설명입니다. 생성자에서 기본 한계를 바꾼 경우도 있습니다.')
    explain(g,'batch-order','완료된 작업에서 결과를 수집한 뒤, 정상적으로 수집을 끝낸 구간에서 호출 ID를 정렬해 관찰 문자열을 덧붙입니다.','수집 중 오류가 전파되면 이 마지막 묶음 기록에 도달하지 못할 수 있습니다.')
    explain(g,'step-error','일반 AgentError를 단계의 오류로 기록하고 finally에서 단계를 마무리합니다. 이후 반복 조건을 다시 확인합니다.','다음 모델 판단이 같은 도구를 다시 호출할지는 확정하지 않습니다. 남은 단계 한계도 적용됩니다.')
    add(g,'configured-budget','run','호출별 max_steps를 생략한 경우','생성자에서 저장한 한계를 사용합니다. 생성자 설정도 생략했다면 기본값은 20입니다.','호출별 값이 없으면 객체의 max_steps를 선택하고, 생성자가 그 값을 저장합니다.','ev-budget ev-run',['생성자에서 한계를 바꾸었다면 그 값이 적용됩니다. 양수 한계의 실행을 설명합니다.'],True)
    add(g,'generation-fatal','loop','단계에서 AgentGenerationError가 발생한 경우','예외를 다시 발생시키고 이 실행의 반복을 중단합니다.','일반 AgentError를 기록하는 분기보다 먼저 별도 예외 분기가 이 오류를 다시 발생시킵니다.','ev-loop',['finally의 단계 마무리는 진행됩니다. 마무리나 콜백 자체의 실패는 별도입니다.'])
    finish(key,g,[figure('budget','이번 실행의 한계는 어디에서 정해질까요?','comparison','effective-budget configured-budget'),figure('failure','어떤 오류에서 계속하거나 중단할까요?','comparison','step-error generation-fatal'),figure('observations','완료 순서와 기록 순서는 왜 다를까요?','conditions','batch-order')],
           [requirement('override','entry',f,468,True,('20',)),requirement('default','entry',f,468,True,('20',)),requirement('recoverable','loop',f,594),requirement('fatal','loop',f,593),requirement('recording','group',f,1436)],
           ['생략한 호출별 한계는 생성자의 설정으로 돌아가며 생성자 기본값과 사용자 설정을 구분한다.','일반 AgentError와 AgentGenerationError의 예외 분기 차이가 계속/중단을 결정한다.','완료 순서로 수집한 뒤 ID 순서로 기록하며 실패하면 마지막 묶음 기록을 건너뛸 수 있다.'],['일반 도구 오류가 같은 도구의 자동 재시도를 보장한다고 설명하지 않는다.'])


def events():
    key='event-async-lifecycle'; f='src/blinker/base.py'
    g=begin(key,'수신자 실패와 임시 연결 종료는 어떻게 처리될까요?','수신자의 종류에 따라 호출 방법이 달라집니다. 전달 실패와 연결 해제는 각자의 경계에서 처리됩니다.')
    explain(g,'await-policy','수신자를 고르는 순서와 호출을 기다리는 방식은 별개입니다. 전달 반복 안에서 각각의 await가 끝나야 다음 수신자로 갑니다.','사용자가 수신자 집합의 순서 정책을 바꿀 수 있으며 실제 수신자 내부 동작은 이 범위 밖입니다.')
    explain(g,'missing-adapter','동기 함수를 발견했을 때 변환기를 먼저 검사하고, 없으면 해당 수신자를 호출하기 전에 예외를 발생시킵니다.','음소거 상태에서는 수신자 반복에 들어가기 전에 빈 결과를 반환합니다.')
    explain(g,'receiver-failure','반복 안에서 예외를 잡아 다음 수신자로 넘어가는 처리가 없으므로 정상 결과 목록 반환에도 도달하지 못합니다.','이미 실행된 수신자의 효과를 되돌리는 처리는 여기 없습니다.')
    add(g,'coroutine-receiver','send','음소거가 아니고 선택한 수신자가 비동기 함수인 경우','수신자를 직접 호출해 완료를 기다리고 반환값을 결과 목록에 추가합니다.','비동기 함수 분기는 변환기를 거치지 않고 개별 수신자를 await합니다.','ev-send',['수신자가 예외를 발생시키면 이후 수신자 호출과 정상 결과 반환이 중단됩니다.'])
    add(g,'temporary-release','connect disconnect','connected_to 문맥의 본문이 정상 종료되거나 예외로 끝난 경우','finally에서 해당 수신자를 연결 해제합니다. 문맥 이전 등록을 복원하는 동작은 아닙니다.','강한 참조로 연결한 뒤 본문을 실행하고, finally에서 송신자를 따로 지정하지 않은 disconnect를 호출합니다.','ev-context ev-disconnect',['이미 등록했던 같은 수신자도 영향을 받을 수 있습니다. 정리 함수나 정리 알림 자체의 실패는 별도입니다.'])
    finish(key,g,[figure('receiver','선택한 수신자의 종류에 따라 무엇이 달라질까요?','comparison','coroutine-receiver missing-adapter'),figure('delivery','전달 순서와 실패는 어디에서 정해질까요?','conditions','await-policy receiver-failure'),figure('lifetime','문맥이 끝나면 연결은 어떻게 될까요?','states','temporary-release','temporary-registration registration-released')],
           [requirement('order','send',f,289),requirement('adapter','send',f,291),requirement('failure','send',f,296),requirement('async','send',f,298),requirement('release','disconnect',f,188)],
           ['개별 await와 수신자 순서 미정을 구분한다.','동기 변환기가 없으면 해당 수신자 호출 전에 실패한다.','finally의 disconnect는 이전 등록 상태 복원이 아니며 모든 송신자 연결에 영향을 줄 수 있다.'],['문맥 종료가 이전 등록을 자동 복원한다고 설명하지 않는다.'])


def web():
    key='web-routing-fallbacks'; f='router.go'
    g=begin(key,'경로를 못 찾으면 어떤 응답을 선택할까요?','매칭·경로 보정·허용 메서드 처리가 먼저 기회를 얻고, 반환하지 못한 요청이 마지막 오류 경로로 갑니다.')
    explain(g,'redirect-status','매칭 실패 뒤 경로 보정 조건을 확인하고 리다이렉트 요청 직후 반환합니다. 그래서 뒤의 OPTIONS와 오류 분기로 계속 진행하지 않습니다.','고정 경로 보정, 사용자 오류 핸들러, 클라이언트의 새 요청은 이 설명 범위 밖입니다.')
    explain(g,'method-error','자동 OPTIONS와 다른 분기에서 허용 목록을 검사합니다. 목록이 있으면 현재 메서드의 기본 오류 응답을 요청하고 반환합니다.','사용자 MethodNotAllowed 핸들러가 없는 기본 응답에 대한 설명입니다.')
    explain(g,'options-or-missing','자동 OPTIONS 분기는 허용 목록이 있어야 반환합니다. 목록이 비어 있으면 뒤의 마지막 경로까지 진행합니다.','자동 OPTIONS 분기에 들어간 요청은 같은 조건문의 메서드 오류 분기로 다시 들어가지 않습니다.')
    add(g,'not-found-default','serve','앞선 처리에서 반환하지 못했고 사용자 NotFound 핸들러가 없는 경우','기본 404 응답을 요청합니다.','앞선 매칭·보정·허용 메서드 분기 다음에 최종 NotFound 처리가 배치되어 있습니다.','ev-serve ev-fallback',['사용자 NotFound 핸들러를 지정하면 그 핸들러가 응답을 결정합니다.'],True)
    finish(key,g,[figure('method','허용 메서드를 찾으면 어떻게 응답할까요?','comparison','method-error options-or-missing'),figure('redirect','경로 보정 뒤에는 왜 오류 처리를 멈출까요?','states','redirect-status','slash-updated'),figure('missing','끝까지 처리하지 못한 요청은 어디로 갈까요?','conditions','not-found-default')],
           [requirement('redirect','dispatch',f,489,True,('301','308')),requirement('method','dispatch',f,529,True,('405',)),requirement('options','allowed',f,514,True,('404',)),requirement('missing','dispatch',f,540,True,('404',))],
           ['허용 목록이 없는 자동 OPTIONS가 같은 조건문의 405 분기로 다시 들어가지 않는 이유를 설명한다.','리다이렉트 직후 반환하기 때문에 이후 오류 처리를 하지 않는다.','기본 응답과 사용자 지정 핸들러의 경계를 구분한다.'],['내부 리다이렉트 호출이 같은 요청을 자동으로 다시 라우팅한다고 설명하지 않는다.'])


if __name__ == '__main__':
    for make in (utility,framework,library,agent,events,web):
        make()
    author.write_json(ROOT / 'eval/rules-cases.json',dict(version=1,behaviorManifest='cases.json',cases=CASES))
    print('Recorded six M3 rule candidates and compositions; human review remains pending.')

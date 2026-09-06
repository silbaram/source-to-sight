"""Reproduce six recorded M2 source readings, never target execution or human approval.

Read discovery.md and the pinned source before changing this ledger. References are
maintained separately in reference_cases.py; existing reference files are preserved.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'eval/m1'))
import author_cases as m1

OUT = ROOT / 'eval/m2'
GRAPHS, CASES = {}, []


def new(key, repo, profiles, title, target, includes, excludes, locations):
    g = m1.base(key, repo, title+'?', title, target, profiles, includes, excludes,
                sorted({loc[1] for loc in locations}))
    g['provenance']['description'] = '고정 소스를 읽어 작성한 M2 복합 동작 후보입니다. 대상 실행·독립 생성 평가·사람 검토는 하지 않았습니다.'
    g['summary'].update(purpose=title, inputs=[], outputs=[], limitations=[])
    for eid, file, symbol, first, last in locations:
        m1.evidence(g, repo, eid, file, symbol, first, last)
    GRAPHS[key] = g
    CASES.append(dict(id=key, source=repo, profile=profiles[0], variant='complex',
                      sourceLanguage=m1.SOURCES[repo]['language'], origin='m2-source-reading',
                      candidate=f'm2/graphs/{key}.json', expectation=f'm2/expectations/{key}.json'))
    return g


def node(g, key, code, label, summary, ev, kind='component', uncertain=False):
    return m1.node(g, key, label, '동적 경계' if uncertain else '이 범위의 역할', summary,
                   ev.split(), summary, code, kind, uncertain)


def edge(g, key, start, end, label, ev, kind='invokes'):
    m1.edge(g, key, start, end, label, kind, ev.split(), label+'에 해당하는 호출·조건·대입을 확인했습니다.')


def rule(g, key, owner, condition, outcome, ev, numeric=False):
    g['rules'].append(dict(id=key, nodeIds=[owner], condition=condition, outcome=outcome,
                           plainText=condition+'이면 '+outcome, numeric=numeric,
                           **m1.claim(ev.split(), '표시한 조건과 결과를 해당 소스 분기에서 확인했습니다.')))


def transition(g, key, owner, before, after, trigger, ev):
    g['stateTransitions'].append(dict(id=key, subjectNodeId=owner, **{'from':before, 'to':after},
                                     trigger=trigger, plainText=before+'에서 '+after+'로 바뀝니다.',
                                     **m1.claim(ev.split(), trigger+'에 해당하는 상태 쓰기를 확인했습니다.')))


def step(target, caption, ev, branch='normal', condition=None, execution=None, returns=None):
    item = dict(caption=caption, branch=branch, **m1.claim(ev.split(), caption))
    item['edgeId' if target.startswith('@') else 'nodeId'] = target.lstrip('@')
    for key, value in (('condition',condition), ('execution',execution), ('returns',returns)):
        if value is not None:
            item[key] = value
    return item


def path(g, key, title, kind, *steps):
    g['scenarios'].append(dict(id=key, title=title, kind=kind,
                               steps=[dict(id=f'{key}-{i}', **s) for i,s in enumerate(steps,1)]))


def finish(g, inputs, outputs, limit):
    g['summary'].update(inputs=inputs, outputs=outputs)
    m1.partial(g, limit, '호출 애플리케이션의 설정·구현과 해당 경계의 소스를 별도로 확인합니다.')


def utility():
    f, models = 'src/smolagents/utils.py', 'src/smolagents/models.py'
    g = new('utility-retry-budget', 'smolagents', ['cli-utility','library-sdk'],
            '실패한 함수를 언제 다시 호출하고 언제 중단하는가', 'Retrying.__call__ + ApiModel retry configuration',
            ['양수 시도 한계의 함수 재시도, ApiModel 기본 정책과 retry 설정', '판정 함수와 로그 처리가 정상 수행되는 범위'],
            ['0 이하 시도 설정, 판정·로깅 함수 자체의 실패', '외부 함수·모델 클라이언트 내부와 스트리밍 반복 중의 오류'],
            [('ev-init',f,'Retrying.__init__',531,549), ('ev-call',f,'Retrying.__call__',551,579),
             ('ev-delay',f,'Retrying.__call__ backoff',591,606), ('ev-config',models,'ApiModel.__init__',1161,1183),
             ('ev-defaults',models,'RETRY constants',38,41), ('ev-predicate',models,'is_rate_limit_error',1194,1202)])
    node(g,'config','ApiModel.__init__','호출 정책 설정','기본 정책은 총 세 번까지 시도하도록 구성합니다. retry를 끄면 최초 한 번만 시도합니다.','ev-config ev-defaults')
    node(g,'retry','Retrying','시도와 종료 판단','함수가 정상 반환하면 즉시 끝납니다. 실패 시 재시도 판정과 남은 횟수를 확인하고, 중단 조건이면 같은 예외를 다시 발생시킵니다.','ev-init ev-call')
    node(g,'function','fn','호출자가 넘긴 함수','호출 규칙은 확인했지만 함수의 결과·부작용·성공 여부는 실행 시 정해집니다.','ev-call','boundary',True)
    node(g,'predicate','is_rate_limit_error','오류 문자열 분류','ApiModel 정책은 오류 문자열의 429 또는 rate limit 관련 문구로 재시도 여부를 판단합니다. HTTP 상태 객체를 검사하는 방식은 아닙니다.','ev-config ev-predicate')
    node(g,'delay','Retrying.delay','다음 시도까지 대기','재시도할 때 현재 지연에 증가 배율과 임의 배율을 곱합니다. 갱신한 지연이 양수일 때만 기다립니다.','ev-init ev-delay','state')
    edge(g,'configure','config','retry','재시도 제어기 구성','ev-config','depends-on')
    edge(g,'attempt','retry','function','남은 시도에서 함수 호출','ev-call','dispatches')
    edge(g,'classify','retry','predicate','실패 후 설정된 판정 함수 호출','ev-call ev-config ev-predicate','dispatches')
    edge(g,'backoff','retry','delay','다시 시도할 때 지연 갱신','ev-call ev-delay','writes')
    edge(g,'again','retry','retry','허용된 실패 뒤 다음 시도','ev-call ev-delay','transitions')
    rule(g,'attempt-budget','retry','양수 max_attempts가 N','최초 호출을 포함해 최대 N회 시도하며 재시도는 최대 N−1회입니다. 기본 제어기의 한계는 1입니다.','ev-init ev-call',True)
    rule(g,'api-budget','config','ApiModel의 retry가 켜짐','총 시도 상한은 3, 재시도 상한은 2입니다. 끄면 총 1회로 바뀝니다.','ev-config ev-defaults ev-call',True)
    rule(g,'stop-error','retry','판정이 거짓이거나 마지막 시도에서 실패','추가 대기 없이 예외를 다시 발생시킵니다. 이 구현은 reraise 값이 달라도 같은 예외를 발생시킵니다.','ev-call')
    rule(g,'wait-update','delay','다시 시도하고 초기 대기가 양수','첫 대기 전부터 배율을 적용합니다. ApiModel의 초기값 60초를 그대로 첫 대기 시간이라고 설명하지 않습니다.','ev-defaults ev-config ev-delay',True)
    transition(g,'delay-grows','delay','직전 지연','배율을 곱한 다음 지연','재시도가 허용되고 시도가 남았을 때','ev-call ev-delay')
    path(g,'retry-success','정상 반환하면 종료','typical',
         step('@attempt','남은 시도 안에서 같은 함수와 인자를 호출합니다.','ev-call',condition='양수 시도 한계 안에 있음'),
         step('retry','함수가 정상 반환하면 다음 시도 없이 그 값을 돌려줍니다.','ev-call','stop',condition='호출이 정상 반환',returns='함수의 반환값'))
    path(g,'retry-next','허용된 실패 뒤 다시 시도','retry',
         step('retry','호출 실패를 받아 재시도 가능 여부를 판정합니다.','ev-call','error',condition='함수 호출 중 예외'),
         step('@classify','설정한 판정 함수가 이 오류의 재시도를 허용하는지 확인합니다.','ev-call ev-config ev-predicate','retry'),
         step('delay','지연을 갱신하고 양수이면 기다립니다.','ev-call ev-delay','retry',condition='판정이 참이고 시도가 남아 있음'),
         step('@again','다음 시도로 돌아갑니다. 이 재생 횟수가 실제 반복 횟수는 아닙니다.','ev-call ev-delay','retry'),
         step('@attempt','같은 함수와 인자를 다시 호출합니다.','ev-call','retry'))
    path(g,'retry-exhausted','재시도 불가 또는 한계 도달','error',
         step('retry','재시도 불가이거나 마지막 시도가 실패하면 예외를 다시 발생시킵니다.','ev-call','stop',condition='판정이 거짓 또는 마지막 시도 실패',returns='호출에서 발생한 예외'))
    finish(g,['함수와 인자, 양수 시도 한계, 재시도 판정과 대기 설정'],['함수 반환값 또는 중단 시 예외'],
           '함수 부작용의 되돌리기나 성공은 보장하지 않습니다. 호출에서 반환된 반복자를 나중에 순회하다 발생한 오류까지 이 제어기가 재시도한다고 해석하지 않습니다.')


def framework():
    hooks, manager, f = 'src/pluggy/_hooks.py', 'src/pluggy/_manager.py', 'src/pluggy/_callers.py'
    g = new('plugin-wrapper-unwind','pluggy',['framework-plugin','library-sdk'],
            '훅의 첫 결과와 오류가 래퍼를 거쳐 반환되는 과정','HookCaller.__call__ + _multicall wrappers',
            ['기본 실행기의 비historic 훅, 새 방식 wrapper의 진입과 역순 복귀', 'firstresult와 구현 오류, 래퍼의 결과·예외 변경'],
            ['old-style hookwrapper, 실행기 재정의', '실제 플러그인 구현과 구체적인 우선순위 구성'],
            [('ev-caller',hooks,'HookCaller.__call__',527,542),('ev-manager',manager,'PluginManager._hookexec',95,108),
             ('ev-call',f,'_multicall setup',82,132),('ev-wrapper',f,'_multicall wrapper entry',112,124),
             ('ev-first',f,'_multicall firstresult',125,137),('ev-unwind',f,'_multicall teardown',139,174)])
    node(g,'caller','HookCaller.__call__','훅 실행 요청','훅 설정에서 firstresult를 읽고 구현 목록의 복사본을 실행기에 전달합니다.','ev-caller')
    node(g,'dispatch','_multicall','구현 순회와 결과 판단','전달된 구현 목록을 역순으로 방문합니다. 첫 유효 결과 설정이면 None이 아닌 결과에서 일반 구현 순회를 중단합니다.','ev-call ev-first ev-manager')
    node(g,'wrapper','hook_impl.function (wrapper)','실행을 감싸는 래퍼','진입한 래퍼는 나중에 결과나 예외를 받습니다. 실제 래퍼는 반환값이나 예외를 바꿀 수 있어 최종 결과는 정적으로 확정하지 않습니다.','ev-wrapper ev-unwind','boundary',True)
    node(g,'implementation','hook_impl.function','실행할 훅 구현','실행기가 선택한 구현을 호출합니다. 실제 플러그인 내부와 반환값은 이 범위에서 정해지지 않습니다.','ev-first','boundary',True)
    node(g,'stack','teardowns','복귀할 래퍼 기록','첫 yield까지 진입한 래퍼만 저장하고 나중에 저장 순서의 역순으로 재개합니다.','ev-wrapper ev-unwind','state')
    edge(g,'dispatch-hook','caller','dispatch','기본 실행기로 위임','ev-caller ev-manager')
    edge(g,'enter-wrapper','dispatch','wrapper','래퍼를 첫 yield까지 진행','ev-wrapper','dispatches')
    edge(g,'remember-wrapper','dispatch','stack','진입한 래퍼 저장','ev-wrapper','writes')
    edge(g,'call-implementation','dispatch','implementation','중단 전 일반 구현 호출','ev-first','dispatches')
    edge(g,'resume-wrapper','dispatch','wrapper','진입한 래퍼를 역순으로 재개','ev-unwind','dispatches')
    rule(g,'first-result','dispatch','firstresult가 참이고 구현 반환값이 None이 아님','일반 구현 순회를 중단하지만 이미 진입한 래퍼의 복귀는 수행합니다.','ev-first ev-unwind')
    rule(g,'wrapper-result','stack','저장된 래퍼를 복귀시킴','예외가 있으면 throw로, 없으면 send로 전달합니다. 래퍼 종료값이 결과를 바꾸고 예외를 해소할 수 있습니다.','ev-unwind')
    transition(g,'wrapper-pushed','stack','이 래퍼의 복귀 기록 없음','이 래퍼의 복귀 기록 있음','래퍼가 첫 yield까지 진입했을 때','ev-wrapper')
    transition(g,'error-replaced','dispatch','처리 중 예외 있음','래퍼 반환값과 예외 없음','복귀 중 래퍼가 StopIteration으로 종료했을 때','ev-unwind')
    path(g,'wrapped-result','첫 결과 뒤 래퍼 복귀','lifecycle',
         step('caller','호스트의 훅 요청을 기본 실행기에 전달합니다.','ev-caller ev-manager'),
         step('@enter-wrapper','새 방식 래퍼를 첫 yield까지 실행합니다.','ev-wrapper',condition='이 항목이 wrapper임'),
         step('stack','진입한 래퍼를 복귀 목록에 저장합니다.','ev-wrapper'),
         step('@call-implementation','순회가 계속되는 동안 일반 훅 구현을 호출합니다.','ev-first'),
         step('dispatch','첫 결과 설정에서는 None이 아닌 결과로 일반 순회를 중단합니다.','ev-first','alternate',condition='firstresult이며 None이 아닌 결과'),
         step('@resume-wrapper','진입한 래퍼들을 역순으로 재개합니다. 결과는 이 과정에서 바뀔 수 있습니다.','ev-unwind'),
         step('dispatch','복귀 후 남은 예외가 없으면 최종 결과를 반환합니다.','ev-unwind','stop',condition='래퍼 복귀 후 예외 없음'))
    path(g,'wrapped-error','오류도 래퍼를 통해 복귀','error',
         step('dispatch','구현 호출이나 인자 준비에서 난 예외를 저장합니다.','ev-call','error',condition='구현 순회 중 예외'),
         step('@resume-wrapper','이미 진입한 래퍼에 역순으로 예외를 전달합니다.','ev-unwind','error'),
         step('dispatch','래퍼가 종료값을 반환하면 결과가 바뀌고 예외가 해소될 수 있습니다.','ev-unwind','alternate',condition='래퍼가 StopIteration으로 종료'),
         step('dispatch','마지막에 예외가 남으면 발생시키고, 없으면 변경된 결과를 반환합니다.','ev-unwind','stop'))
    finish(g,['호스트의 훅 호출, 구현 목록, firstresult 설정'],['래퍼 복귀 후 결과 또는 최종 예외'],
           '등록 순서나 파일 순서만으로 실제 플러그인의 총 실행 순서를 정하지 않습니다. 래퍼가 원래 오류를 반드시 보존한다고 가정하지 않습니다.')


def library():
    f, inner = 'lru.go', 'simplelru/lru.go'
    g = new('library-resize-callbacks','golang-lru',['library-sdk','framework-plugin'],
            '캐시 크기를 줄일 때 제거와 알림이 이루어지는 순서','Cache.Resize + simplelru.LRU.Resize',
            ['정상 생성된 캐시의 0 이상 크기 변경, 퇴출 반복과 잠금 해제 후 콜백', '동기 사용자 콜백의 정상 반환 또는 panic'],
            ['음수 크기, 내부 제거·할당 실패', '콜백 내부와 별도 고루틴의 전체 실행 순서'],
            [('ev-setup',f,'NewWithEvict',33,55),('ev-resize',f,'Cache.Resize',185,201),
             ('ev-inner',inner,'LRU.Resize',156,166),('ev-remove',inner,'removeOldest / removeElement',169,182)])
    node(g,'resize','Cache.Resize','크기 변경 요청','잠금을 잡고 내부 크기를 바꿉니다. 알림할 항목을 분리한 뒤 잠금을 풀고 사용자 콜백을 호출합니다.','ev-resize')
    node(g,'inner','simplelru.LRU.Resize','필요한 만큼 제거','현재 항목 수와 새 크기의 차이가 양수이면 그만큼 가장 오래된 항목을 제거하고 새 크기를 저장합니다.','ev-inner')
    node(g,'remove','removeOldest / removeElement','오래된 항목 삭제','목록과 키 조회에서 항목을 제거하고, 설정된 내부 퇴출 콜백을 호출합니다.','ev-remove')
    node(g,'buffer','Cache.evictedKeys / evictedVals','알림할 항목 보관','생성 시 연결한 내부 콜백이 키와 값을 모읍니다. 공개 Resize는 알림 목록을 분리하고 새 버퍼를 준비합니다.','ev-setup ev-resize','state')
    node(g,'callback','onEvictedCB','사용자에게 퇴출 알림','콜백이 있고 실제 퇴출 수가 양수이면 잠금 밖에서 수집한 항목들을 알립니다. 콜백의 부작용은 미확인입니다.','ev-resize','boundary',True)
    edge(g,'resize-inner','resize','inner','잠금 안에서 크기 변경','ev-resize')
    edge(g,'remove-loop','inner','remove','초과한 항목 수만큼 제거','ev-inner')
    edge(g,'buffer-removed','remove','buffer','내부 콜백으로 키와 값 보관','ev-setup ev-remove','writes')
    edge(g,'notify-removed','resize','callback','잠금 해제 후 조건부 알림','ev-resize','dispatches')
    rule(g,'remove-count','inner','새 크기가 0 이상','제거 횟수는 현재 항목 수에서 새 크기를 뺀 값과 0 중 큰 값입니다. 현재 항목 수 이상으로 늘리면 제거하지 않습니다.','ev-inner',True)
    rule(g,'callback-order','resize','사용자 콜백이 있고 퇴출 수가 양수','알림 목록 분리와 새 버퍼 준비, 잠금 해제 뒤 콜백을 호출합니다.','ev-resize')
    rule(g,'callback-panic','callback','동기 콜백에서 panic이 전파됨','이 함수는 나머지 알림을 계속하지 않습니다. 이미 바꾼 캐시 크기와 삭제를 되돌리는 처리는 없습니다.','ev-resize')
    transition(g,'buffer-detached','buffer','공유 버퍼에 퇴출 항목 있음','이전 항목은 지역 목록, 공유 버퍼는 새로 준비됨','콜백이 있고 내부 Resize가 양수 퇴출 수를 반환했을 때','ev-setup ev-resize')
    transition(g,'size-updated','inner','이전 용량','요청한 새 용량','필요한 제거 반복을 마친 뒤','ev-inner')
    path(g,'shrink-notify','항목 제거 후 잠금 밖에서 알림','typical',
         step('resize','잠금을 잡고 내부 Resize를 호출합니다.','ev-resize',condition='정상 생성된 캐시, 0 이상인 새 크기'),
         step('@remove-loop','현재 항목 수가 새 크기보다 많으면 차이만큼 오래된 항목을 제거합니다.','ev-inner'),
         step('buffer','내부 콜백이 제거한 항목을 수집합니다.','ev-setup ev-remove'),
         step('resize','알림 목록을 분리하고 새 버퍼를 준비한 뒤 잠금을 해제합니다.','ev-resize'),
         step('@notify-removed','잠금 밖에서 수집한 항목을 순서대로 알립니다.','ev-resize',condition='콜백 있음, 퇴출 수 양수',execution='sequential'),
         step('resize','콜백이 정상 반환하면 퇴출 수를 반환합니다.','ev-resize','stop'))
    path(g,'grow-without-eviction','제거할 항목이 없는 크기 변경','alternate',
         step('inner','새 크기가 현재 항목 수 이상이면 제거 반복 없이 크기를 저장합니다.','ev-inner','alternate',condition='새 크기 ≥ 현재 항목 수'),
         step('resize','잠금을 풀고 퇴출 알림 없이 0을 반환합니다.','ev-resize ev-inner','stop',returns='퇴출 수 0'))
    path(g,'callback-failure','콜백이 실패한 뒤의 상태','error',
         step('@notify-removed','이미 잠금을 푼 상태에서 사용자 콜백을 호출합니다.','ev-resize'),
         step('resize','콜백 panic이 전파되면 이후 알림은 중단되고 이미 수행한 변경은 남습니다.','ev-resize','error',condition='동기 콜백의 panic이 전파됨'))
    finish(g,['캐시와 0 이상 새 크기, 선택적 퇴출 콜백'],['변경된 용량·항목, 정상 경로의 퇴출 수 또는 콜백 panic'],
           '콜백 내부와 다른 고루틴의 실행 순서는 미확인입니다. 내부 실패에도 항상 잠금이 풀린다는 보장은 이 범위에 포함하지 않습니다.')


def agent():
    f, tools = 'src/smolagents/agents.py', 'src/smolagents/tools.py'
    g = new('agent-parallel-tools','smolagents',['ai-agent','library-sdk','framework-plugin'],
            '도구를 병렬 처리하는 에이전트의 반복과 실패 경계','ToolCallingAgent run + process_tool_calls + Tool.__call__',
            ['양수 단계 한계, 비스트리밍 ToolCallingAgent와 기본 Tool.__call__을 상속한 도구', '고유 호출 ID, 텍스트 결과, 병렬 제출·수집·기록, 단계 오류와 종료'],
            ['계획·최종 답 검사·사용자 단계 콜백 실패, managed agent', '이미지·음성 공유 상태, 중복 호출 ID, 실제 모델·도구 내부, 스레드 실행기 내부'],
            [('ev-budget',f,'MultiStepAgent.__init__ max_steps',296,331),('ev-run',f,'MultiStepAgent.run',468,499),
             ('ev-loop',f,'MultiStepAgent._run_stream',540,612),('ev-fallback',f,'_handle_max_steps_reached',625,637),
             ('ev-step',f,'ToolCallingAgent._step_stream',1276,1359),('ev-batch',f,'process_tool_calls',1361,1442),
             ('ev-execute',f,'execute_tool_call',1453,1518),('ev-tool',tools,'Tool.__call__',231,256)])
    node(g,'run','MultiStepAgent.run','실행 설정과 요청 기록','호출별 양수 max_steps가 있으면 기본 한계보다 우선합니다. 요청을 기록하고 반복을 시작합니다.','ev-budget ev-run')
    node(g,'loop','MultiStepAgent._run_stream','다음 단계와 종료 판단','최종 답이 없고 단계 한계 안이면 단계를 실행합니다. 생성 오류는 전파하고 다른 AgentError는 기록한 뒤 남은 단계로 진행할 수 있습니다.','ev-loop')
    node(g,'step','ToolCallingAgent._step_stream','모델 요청과 도구 처리','메모리를 메시지로 만들고 모델에 요청합니다. 해석한 도구 호출을 처리한 뒤 최종 답 여부를 판단합니다.','ev-step')
    node(g,'model','model.generate','모델 응답 경계','구체적 도구 선택·응답·성공 여부는 모델 실행에 따라 달라집니다.','ev-step','boundary',True)
    node(g,'batch','ToolCallingAgent.process_tool_calls','도구 묶음 제출과 수집','호출이 하나면 직접 처리합니다. 여러 고유 호출은 스레드 실행기에 제출해 완료되는 결과를 수집합니다. 반환 순서는 제출 순서로 고정되지 않습니다.','ev-batch')
    node(g,'execute','ToolCallingAgent.execute_tool_call','도구 선택과 인자 확인','도구를 찾고 상태 값을 인자에 대입한 뒤 검증합니다. 일반 도구는 입출력 변환을 요청하며 호출합니다.','ev-execute')
    node(g,'tool','Tool.__call__','도구 초기화와 입출력 변환','미초기화 도구는 setup을 요청합니다. 입력을 변환해 forward를 호출하고 출력을 변환합니다.','ev-tool')
    node(g,'forward','Tool.forward','도구 구현 경계','호출하는 구체적 도구의 처리·부작용·결과는 이 기본 클래스에서 정해지지 않습니다.','ev-tool','boundary',True)
    node(g,'observations','memory_step.observations','완료한 묶음의 관찰 기록','묶음을 정상적으로 모두 소비한 뒤 호출과 관찰을 ID 정렬 순서로 기록합니다. 완료 순서와 이 정렬 순서는 다릅니다.','ev-batch','state')
    node(g,'fallback','MultiStepAgent._handle_max_steps_reached','한계 도달 후 대체 답변','최종 답 없이 한계에 도달하면 대체 답변을 요청하고 한계 오류와 답변 내용을 기록합니다.','ev-loop ev-fallback')
    # Keep the overview focused; walkthrough selection reveals these actual tool internals.
    for item in g['nodes']:
        if item['id'] in {'execute','tool','forward'}:
            item['importance'] = 'detail'
    for args in [('start','run','loop','설정한 한계로 반복 시작','ev-run'),('decide','loop','step','한 단계 실행','ev-loop'),
                 ('ask-model','step','model','모델 생성 요청','ev-step'),('process-batch','step','batch','해석한 도구 묶음 처리','ev-step'),
                 ('worker-call','batch','execute','각 작업에서 도구 호출','ev-batch'),('call-tool','execute','tool','선택한 일반 도구 호출','ev-execute'),
                 ('run-forward','tool','forward','입력 변환 후 구현 호출','ev-tool'),('at-limit','loop','fallback','최종 답 없이 한계 도달','ev-loop')]:
        edge(g,*args)
    edge(g,'save-observations','batch','observations','정상 수집 후 ID 순서로 기록','ev-batch','writes')
    edge(g,'next-decision','loop','loop','최종 답 없고 단계가 남으면 반복','ev-loop','transitions')
    rule(g,'effective-budget','run','호출별 max_steps가 양수로 제공됨','그 값이 기본값보다 우선합니다. 기본값은 20이며 각 단계는 도구 호출 수와 별개입니다.','ev-budget ev-run ev-loop',True)
    rule(g,'batch-order','batch','고유 호출이 여러 개이고 결과 수집이 정상 완료됨','작업 완료 순서로 결과를 받지만 관찰은 호출 ID 정렬 순서로 기록합니다. 모든 작업이 동시에 시작한다고 보장하지 않습니다.','ev-batch')
    rule(g,'step-error','loop','AgentGenerationError가 아닌 AgentError가 단계에서 발생','오류를 단계에 기록하고 남은 예산에서 다시 판단할 수 있습니다. 같은 도구의 자동 재시도가 확정되는 것은 아닙니다.','ev-loop')
    transition(g,'observations-written','observations','기존 관찰 또는 빈 문자열','정렬된 도구 관찰이 추가됨','도구 묶음의 결과를 정상적으로 모두 소비한 뒤','ev-batch')
    transition(g,'step-recorded','loop','현재 단계를 실행 중','단계 기록을 추가하고 단계 번호 증가','단계 본문의 finally가 정상 수행될 때','ev-loop')
    path(g,'parallel-round','도구 묶음이 정상 완료된 한 단계','typical',
         step('run','요청과 실행별 단계 한계를 준비합니다.','ev-run ev-budget',condition='양수 단계 한계, 비스트리밍 경로'),
         step('loop','최종 답이 없고 단계가 남았으면 모델을 사용하는 한 단계를 시작합니다.','ev-loop'),
         step('step','메모리를 바탕으로 모델에 다음 동작을 요청합니다.','ev-step'),
         step('@process-batch','해석한 도구 묶음을 처리기로 넘겨 여러 호출을 작업으로 제출합니다. 작업 사이 실행 순서는 정해져 있지 않습니다.','ev-step ev-batch',condition='고유 호출이 여러 개',execution='parallel'),
         step('@worker-call','각 작업이 도구 선택과 인자 검증을 수행합니다.','ev-batch ev-execute',execution='parallel'),
         step('@call-tool','각 작업에서 일반 도구를 호출해 초기화·입력 변환·forward·출력 변환 규칙을 따릅니다.','ev-execute ev-tool',execution='parallel'),
         step('@save-observations','도구 묶음의 정상 수집을 마치면 ID 순서로 관찰을 기록합니다.','ev-batch',condition='묶음을 정상적으로 모두 소비함',execution='sequential'),
         step('@next-decision','최종 답이 없고 단계가 남으면 반복 제어에서 다음 판단으로 이어집니다.','ev-loop','alternate',condition='최종 답 없음, 단계가 남음'))
    path(g,'tool-round-failure','도구 실패 후 남은 단계의 판단','error',
         step('batch','결과 수집에서 도구 오류가 전파되면 뒤의 묶음 관찰 기록을 건너뜁니다. 이미 수행한 부작용을 되돌리지는 않습니다.','ev-batch ev-execute','error',condition='도구에서 AgentError가 전파됨',execution='parallel'),
         step('loop','생성 오류가 아닌 AgentError를 현재 단계에 기록합니다.','ev-loop','error'),
         step('loop','단계가 남으면 모델이 다음 동작을 다시 정합니다. 동일 도구 재호출은 확정할 수 없습니다.','ev-loop','alternate',condition='최종 답 없음, 단계 한계 안에 있음'),
         step('fallback','한계까지 최종 답이 없었던 경로에서는 대체 답변을 요청합니다.','ev-loop ev-fallback','stop',condition='최종 답 없이 단계 번호가 한계 다음에 도달함'))
    path(g,'generation-failure','모델 생성 오류는 실행 중단','error',
         step('step','모델 생성 과정의 예외를 AgentGenerationError로 감쌉니다.','ev-step','error',condition='모델 생성 과정의 예외'),
         step('loop','생성 오류는 기록 정리 경로를 거쳐 전파하며 다음 판단 단계로 계속하지 않습니다.','ev-loop','stop'))
    finish(g,['요청, 실행별 또는 기본 단계 한계, 모델·도구 설정'],['단계·관찰 기록, 최종 또는 대체 답변, 전파된 생성 오류'],
           '모델과 도구의 실제 선택·성공·부작용, 스레드 내부 동작은 미확인입니다. 실패한 묶음이 원자적으로 취소되거나 모든 성공 결과가 반드시 기록된다고 보장하지 않습니다.')


def event():
    f = 'src/blinker/base.py'
    g = new('event-async-lifecycle','blinker',['data-event','framework-plugin','library-sdk'],
            '비동기 신호 전달과 임시 수신자의 해제 경계','Signal.connected_to + Signal.send_async',
            ['기존 등록이 없는 수신자의 비중첩 connected_to 문맥', 'send_async의 선택·개별 await·실패 전파와 문맥 종료'],
            ['사용자 수신자·동기 변환기의 내부', '중첩 문맥·기존 등록 복원, 사용자 set_class 재정의'],
            [('ev-context',f,'Signal.connected_to',168,189),('ev-connect',f,'Signal.connect',91,139),
             ('ev-send',f,'Signal.send_async',255,303),('ev-select',f,'Signal.receivers_for',326,362),
             ('ev-disconnect',f,'Signal.disconnect / _disconnect',364,403)])
    node(g,'context','Signal.connected_to','문맥 동안 연결 유지','강한 참조로 임시 수신자를 등록하고, 문맥이 끝나면 finally에서 수신자를 해제합니다. send_async는 문맥 안의 호출자가 별도로 요청합니다.','ev-context')
    node(g,'connect','Signal.connect','수신자 등록','수신자와 발신자의 연결을 저장합니다. 등록 그 자체가 수신자 실행을 뜻하지 않습니다.','ev-connect')
    node(g,'send','Signal.send_async','수신자를 하나씩 기다림','음소거이면 즉시 빈 목록을 반환합니다. 선택한 수신자를 반복문 안에서 각각 await하며 오류가 나면 전파합니다.','ev-send')
    node(g,'select','Signal.receivers_for','발신자에 맞는 수신자 선택','발신자와 ANY에 연결된 수신자를 찾고 죽은 약한 참조를 제거합니다. 기본 집합의 수신자 순서는 고정되지 않습니다.','ev-select')
    node(g,'adapter','_sync_wrapper','동기 수신자 변환 경계','동기 수신자에는 제공된 변환기를 적용하고 그 결과를 기다립니다. 실제 변환기가 스레드를 쓰는지는 미확인입니다.','ev-send','boundary',True)
    node(g,'receiver','receiver','수신자 구현 경계','비동기 수신자를 호출하고 완료를 기다립니다. 구체적 처리·반환값·실패는 애플리케이션이 정합니다.','ev-send','boundary',True)
    node(g,'disconnect','Signal.disconnect','문맥 종료 시 등록 해제','connected_to의 finally는 발신자 인자 없이 disconnect를 호출합니다. 이전 연결 상태를 저장해 복원하는 방식은 아닙니다.','ev-context ev-disconnect')
    edge(g,'temporary-connect','context','connect','문맥 진입 시 등록','ev-context')
    edge(g,'select-receivers','send','select','수신자 반복 대상 조회','ev-send')
    edge(g,'adapt-sync','send','adapter','동기 수신자 변환 후 await','ev-send','dispatches')
    edge(g,'await-receiver','send','receiver','비동기 수신자를 개별 await','ev-send','dispatches')
    edge(g,'temporary-disconnect','context','disconnect','finally에서 해제','ev-context')
    rule(g,'await-policy','send','음소거가 아니고 수신자가 선택됨','각 수신자를 하나씩 기다립니다. 수신자 순서 미정과 병렬 실행은 같은 뜻이 아닙니다.','ev-send ev-select')
    rule(g,'missing-adapter','send','선택한 수신자가 동기 함수이고 _sync_wrapper가 없음','RuntimeError를 발생시키고 이후 수신자는 호출하지 않습니다.','ev-send')
    rule(g,'receiver-failure','send','수신자 또는 변환기의 예외가 전파됨','남은 전달과 정상 결과 반환을 중단합니다. 이미 끝난 수신자의 부작용은 되돌리지 않습니다.','ev-send')
    transition(g,'temporary-registration','connect','이 수신자의 등록 없음','강한 참조의 수신자 등록 있음','connected_to 문맥 진입에서 connect가 정상 완료됨','ev-context ev-connect')
    transition(g,'registration-released','disconnect','문맥의 수신자 등록 있음','수신자 연결 해제됨','connected_to 문맥 종료의 finally가 실행됨','ev-context ev-disconnect')
    path(g,'async-context','임시 등록과 정상 비동기 전달','lifecycle',
         step('@temporary-connect','문맥 진입 시 수신자를 등록합니다.','ev-context'),
         step('send','문맥 안의 호출자가 비동기 전달을 요청합니다. 등록 함수가 자동 호출하는 것은 아닙니다.','ev-context ev-send'),
         step('select','발신자에 맞는 수신자를 선택합니다.','ev-send ev-select',execution='unordered'),
         step('@await-receiver','각 비동기 수신자를 하나씩 await합니다. 구체적인 수신자 방문 순서는 고정되지 않습니다.','ev-send','normal',condition='선택한 수신자가 비동기 함수',execution='unordered'),
         step('send','모두 정상 완료하면 수신자와 반환값의 목록을 돌려줍니다.','ev-send','stop',condition='모든 개별 await가 정상 완료됨'),
         step('@temporary-disconnect','문맥이 끝나면 finally에서 임시 연결을 해제합니다.','ev-context'))
    path(g,'async-error-cleanup','오류가 나도 문맥의 연결 해제','error',
         step('send','동기 수신자에 변환기가 없으면 즉시 오류를 발생시킵니다. 수신자 예외도 전파합니다.','ev-send','error',condition='동기 변환기가 없거나 개별 전달 중 예외'),
         step('@temporary-disconnect','오류가 문맥 밖으로 나가는 경우에도 finally의 해제 요청을 수행합니다.','ev-context','stop'))
    path(g,'async-muted','음소거 중에는 전달 생략','alternate',
         step('send','수신자 선택 전에 빈 목록을 반환합니다.','ev-send','stop',condition='is_muted가 참',returns='빈 목록'))
    finish(g,['임시 수신자, 발신자, 전달 인자와 선택적 동기 변환기'],['정상 결과 목록 또는 전파된 예외, 문맥 종료 시 수신자 해제'],
           '실제 수신자 순서·반환값·변환기 내부는 미확인입니다. 병렬 실행, 전달 보장, 실패 시 재전송이나 이전 등록 상태 복원을 약속하지 않습니다.')


def web():
    f = 'router.go'
    g = new('web-routing-fallbacks','httprouter',['web','framework-plugin'],
            '요청 경로가 맞지 않을 때 리다이렉트와 오류 응답을 고르는 과정','Router.ServeHTTP fallback dispatch',
            ['등록된 메서드별 트리의 요청 처리와 후행 슬래시 보정, OPTIONS·405·404 분기', 'RedirectFixedPath는 꺼짐, 커스텀 OPTIONS·405·404·panic 핸들러 없음'],
            ['등록된 처리 함수 내부, 트리 삽입·탐색 최적화와 Go HTTP 패키지 내부', '고정 경로 보정과 panic 복구, 커스텀 오류 응답, 서버 전체 OPTIONS *'],
            [('ev-serve',f,'Router.ServeHTTP',463,542),('ev-redirect',f,'Router.ServeHTTP trailing slash',479,495),
             ('ev-fallback',f,'Router.ServeHTTP fallback',512,542),('ev-allowed',f,'Router.allowed',409,460),
             ('ev-tree','tree.go','node.getValue',326,431)])
    node(g,'serve','Router.ServeHTTP','요청별 분기 선택','메서드의 경로를 먼저 찾고, 일치하면 처리 함수 실행 후 반환합니다. 불일치하면 설정과 조건에 따라 보정·OPTIONS·오류 경로를 고릅니다.','ev-serve')
    node(g,'tree','node.getValue','경로와 보정 후보 조회','메서드별 트리에서 처리 함수·매개변수·후행 슬래시 보정 후보를 조회합니다. 후보만으로 응답을 보내지는 않습니다.','ev-tree ev-serve')
    node(g,'handler','Handle','등록된 처리 함수','일치한 처리 함수를 호출합니다. 그 함수가 만드는 응답과 내부 처리는 애플리케이션에 따라 달라집니다.','ev-serve','boundary',True)
    node(g,'redirect','http.Redirect','보정한 주소로 안내','로컬 분기가 경로를 수정하고 선택한 상태 코드로 리다이렉트를 요청한 뒤 반환합니다. HTTP 구현 내부는 범위 밖입니다.','ev-redirect','boundary',True)
    node(g,'allowed','Router.allowed','허용 메서드 확인','현재 요청과 OPTIONS를 제외한 메서드에서 같은 경로를 찾습니다. 설정에 따라 OPTIONS를 추가하고 정렬한 목록을 반환합니다.','ev-allowed')
    node(g,'response','http.Error / http.NotFound','기본 오류 응답 요청','405 분기에서는 기본 오류 응답을, 마지막 경로에서는 404 응답을 요청합니다. 구체적인 응답 본문 생성은 HTTP 패키지 경계입니다.','ev-fallback','boundary',True)
    edge(g,'lookup-path','serve','tree','요청 메서드의 경로 조회','ev-serve')
    edge(g,'matched-handler','serve','handler','경로 일치 시 처리 함수 호출','ev-serve','dispatches')
    edge(g,'redirect-slash','serve','redirect','조건을 만족하면 슬래시 보정 응답','ev-redirect')
    edge(g,'find-allowed','serve','allowed','다른 허용 메서드 확인','ev-fallback')
    edge(g,'error-response','serve','response','기본 405 또는 404 요청','ev-fallback')
    rule(g,'redirect-status','serve','메서드 트리가 있고 처리 함수 불일치, CONNECT가 아니며 루트 경로가 아니고 슬래시 보정 후보·설정이 참','GET은 301, 다른 메서드는 308 리다이렉트를 요청하고 이후 OPTIONS·오류 분기를 건너뜁니다.','ev-serve ev-redirect',True)
    rule(g,'method-error','serve','자동 OPTIONS 경로가 아니며 HandleMethodNotAllowed가 참이고 허용 목록이 비어 있지 않음','Allow를 설정하고 기본 405 응답을 요청한 뒤 반환합니다.','ev-fallback',True)
    rule(g,'options-or-missing','allowed','자동 OPTIONS가 켜진 OPTIONS 요청에서 허용 목록이 비어 있지 않음','Allow를 설정하고 반환합니다. 목록이 없으면 이 분기의 뒤인 404 경로로 갑니다.','ev-fallback',True)
    transition(g,'slash-updated','serve','원래 요청 경로','끝 슬래시를 추가하거나 제거한 경로','후행 슬래시 리다이렉트 분기가 선택되었을 때','ev-redirect')
    path(g,'matched-route','일치한 처리 함수로 전달','typical',
         step('serve','요청 메서드에 해당하는 트리에서 경로를 찾습니다.','ev-serve'),
         step('@matched-handler','일치한 처리 함수를 호출하고 정상 반환하면 라우터도 반환합니다.','ev-serve','stop',condition='처리 함수가 일치하고 정상 반환함'))
    path(g,'slash-redirect','끝 슬래시를 보정한 뒤 종료','alternate',
         step('serve','경로 불일치 뒤 후행 슬래시 보정 조건을 검사합니다.','ev-redirect','alternate',condition='해당 메서드 트리 있음, CONNECT·루트 경로 아님, 보정 후보와 설정 참'),
         step('@redirect-slash','GET은 301, 다른 메서드는 308로 리다이렉트를 요청하고 반환합니다.','ev-redirect','stop'))
    path(g,'method-not-allowed','다른 메서드에 경로가 있는 경우','error',
         step('@find-allowed','앞선 일치·보정 경로에서 끝나지 않았으면 허용 메서드를 확인합니다.','ev-fallback','alternate',condition='자동 OPTIONS 분기가 아니고 405 처리가 켜짐'),
         step('@error-response','허용 목록이 있으면 Allow와 기본 405 응답을 요청합니다.','ev-fallback','stop',condition='허용 목록이 비어 있지 않음',returns='405 응답 요청'))
    path(g,'not-found','앞선 분기로 처리되지 않은 경우','error',
         step('serve','경로 일치·보정·자동 OPTIONS·405 분기로 반환하지 못했습니다.','ev-serve','error'),
         step('@error-response','마지막 기본 404 응답을 요청합니다.','ev-fallback','stop',condition='앞선 분기에서 반환하지 않음',returns='404 응답 요청'))
    finish(g,['메서드와 경로, 등록 트리와 라우터 설정'],['처리 함수 호출, 리다이렉트, Allow 설정 또는 기본 오류 응답 요청'],
           '등록된 처리 함수와 Go HTTP 응답 구현은 미확인입니다. 슬래시 보정을 서버 내부 재실행이나 처리 함수의 자동 재호출로 표현하지 않습니다.')


def main():
    for build in (utility, framework, library, agent, event, web):
        build()
    for key, graph in GRAPHS.items():
        m1.s2s.validate(graph)
        m1.author.write_json(OUT / 'graphs' / f'{key}.json', graph)
    legacy = ROOT / 'eval/cases-m15.json'
    if not legacy.exists():
        original = json.loads((ROOT / 'eval/cases.json').read_text())
        if len(original['cases']) != 18:
            raise ValueError('Preserve the original 18-case manifest before expanding it')
        legacy.write_text((ROOT / 'eval/cases.json').read_text())
    manifest = json.loads(legacy.read_text())
    manifest['cases'] += CASES
    m1.author.write_json(ROOT / 'eval/cases.json', manifest)
    print('Wrote six M2 candidates and the expanded 24-case manifest; M1.5 inputs preserved.')


if __name__ == '__main__':
    main()

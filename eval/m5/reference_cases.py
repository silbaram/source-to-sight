"""Source-role acceptance criteria, maintained separately from the map readings.

Existing references are never overwritten. Wording and comprehension need human review.
"""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'skills/code-flow/scripts'))
import author

CAPABILITY_ROLES={
    'utility':['cleaner','cleaner'],
    'framework':['dispatch','registry','registry'],
    'agent':['toolmode','loop','command','execution'],
    'library':['cache','cache','expiration'],
    'event':['signal','signal','names'],
    'web':['router','router','parameters'],
}

CASES={
 'utility': {
  'source':'strip-ansi','profile':'cli-utility','behavior':'utility-strip','behaviorInput':'m1/graphs/utility-strip.json',
  'logicInput':'m5/graphs/utility-strip-rules.json','layout':'m5/layouts/utility-strip-rules.json',
  'nodes':[('cleaner','index.js',5,'stripAnsi')], 'edges':[], 'regions':[],
  'facts':['배포 진입점과 타입 선언은 문자열 정리 함수를 공개한다.','별도 CLI와 스트림 도구를 이 저장소의 구성으로 포함하지 않는다.'],
  'forbidden':['문자열 정리 함수 안에 HTTP 서버나 실행 시나리오가 있다고 설명한다.']},
 'framework': {
  'source':'pluggy','profile':'framework-plugin','behavior':'plugin-wrapper-unwind','behaviorInput':'m2/graphs/plugin-wrapper-unwind.json',
  'nodes':[('marking','src/pluggy/_hooks.py',156,'HookspecMarker / HookimplMarker'),('registry','src/pluggy/_manager.py',149,'PluginManager'),
           ('caller','src/pluggy/_hooks.py',542,'HookCaller'),('dispatch','src/pluggy/_callers.py',126,'_multicall'),
           ('result','src/pluggy/_callers.py',43,'Result'),('tracing','src/pluggy/_manager.py',477,'add_hookcall_monitoring')],
  'edges':[('registry','reads','marking'),('registry','registers','caller'),('caller','invokes','registry'),('registry','invokes','dispatch'),('dispatch','passes-data','result'),('registry','registers','tracing')],
  'regions':[['marking','registry'],['caller','dispatch','result']],
  'facts':['매니저가 표식으로 구현을 찾고 훅 호출기에 등록한다.','호출기는 매니저의 실행 함수를 통해 기본 multicall로 연결된다.','외부 플러그인 내부는 지도에서 확정하지 않는다.'],
  'forbidden':['파일 배치 순서를 플러그인 실행 순서로 표현한다.']},
 'agent': {
  'source':'smolagents','profile':'ai-agent','behavior':'agent-parallel-tools','behaviorInput':'m2/graphs/agent-parallel-tools.json',
  'nodes':[('loop','src/smolagents/agents.py',578,'MultiStepAgent'),('toolmode','src/smolagents/agents.py',1215,'ToolCallingAgent'),
           ('codemode','src/smolagents/agents.py',1505,'CodeAgent'),('models','src/smolagents/models.py',452,'Model'),
           ('tools','src/smolagents/tools.py',246,'Tool'),('execution','src/smolagents/agents.py',1603,'PythonExecutor'),
           ('memory','src/smolagents/memory.py',230,'AgentMemory'),('metrics','src/smolagents/monitoring.py',100,'Monitor'),
           ('command','src/smolagents/cli.py',259,'smolagent / run_smolagent')],
  'edges':[('loop','delegates','toolmode'),('loop','delegates','codemode'),('toolmode','invokes','models'),('codemode','invokes','models'),
           ('toolmode','invokes','tools'),('codemode','invokes','execution'),('loop','writes','memory'),('loop','registers','metrics'),('command','invokes','loop')],
  'regions':[['loop','toolmode','codemode'],['models','tools','execution'],['memory','metrics']],
  'facts':['공통 반복은 선택한 에이전트 방식의 한 단계를 호출한다.','도구 호출과 코드 실행 방식은 서로 다른 구현이다.','모델 응답과 원격 환경 내부는 정적으로 확정하지 않는다.'],
  'forbidden':['두 에이전트 방식이 한 요청에서 반드시 차례로 실행된다고 설명한다.','관찰한 실행 기록 없이 처리 시간이나 사용량을 표시한다.']},
 'library': {
  'source':'golang-lru','profile':'library-sdk','behavior':'library-resize-callbacks','behaviorInput':'m2/graphs/library-resize-callbacks.json',
  'nodes':[('cache','lru.go',42,'Cache'),('frequency','2q.go',68,'TwoQueueCache'),('adaptive','arc/arc.go',36,'ARCCache'),
           ('expiration','expirable/expirable_lru.go',79,'expirable.LRU'),('base','simplelru/lru.go',31,'simplelru.LRU'),('list','internal/list.go',44,'LruList / Entry')],
  'edges':[('cache','invokes','base'),('frequency','invokes','base'),('adaptive','invokes','base'),('base','depends-on','list'),('expiration','depends-on','list')],
  'regions':[['cache','frequency','adaptive','expiration'],['base','list']],
  'facts':['공개 캐시 정책과 기본 저장 구조를 구분한다.','만료 캐시는 내부 목록을 직접 사용한다.','arc 디렉터리는 별도 모듈 선언을 가진다.'],
  'forbidden':['expirable이 simplelru 캐시를 호출한다고 표현한다.','루트 디렉터리에 있다는 이유로 모든 정책이 같은 실행 경로라고 표현한다.']},
 'event': {
  'source':'blinker','profile':'data-event','behavior':'event-async-lifecycle','behaviorInput':'m2/graphs/event-async-lifecycle.json',
  'nodes':[('names','src/blinker/base.py',494,'Namespace / NamedSignal'),('signal','src/blinker/base.py',111,'Signal'),
           ('weak','src/blinker/_utilities.py',60,'make_id / make_ref'),('receiver','src/blinker/base.py',249,'receiver','boundary')],
  'edges':[('names','invokes','signal'),('signal','invokes','weak'),('signal','dispatches','receiver')],
  'regions':[['signal','weak']],
  'facts':['이름 공간은 이름으로 같은 신호를 다시 제공한다.','신호는 등록·전달·약한 참조 정리를 맡는다.','사용자 수신자의 구현과 순서는 지도만으로 알 수 없다.'],
  'forbidden':['등록한 순서대로 모든 수신자가 실행된다고 확정한다.']},
 'web': {
  'source':'httprouter','profile':'web','behavior':'web-routing-fallbacks','behaviorInput':'m2/graphs/web-routing-fallbacks.json',
  'nodes':[('router','router.go',138,'Router'),('tree','tree.go',74,'node'),('path','path.go',21,'CleanPath'),
           ('parameters','router.go',346,'Params / Router.Handler'),('handler','router.go',89,'Handle','boundary')],
  'edges':[('router','registers','tree'),('router','invokes','tree'),('router','invokes','path'),('router','invokes','handler'),('router','passes-data','parameters')],
  'regions':[['router','parameters'],['tree','path']],
  'facts':['요청 메서드별로 저장한 트리에서 경로와 처리 함수를 찾는다.','경로 정리는 설정된 보정 경로에서 호출된다.','앱 처리 함수 내부는 라우터 저장소의 설명 범위 밖이다.'],
  'forbidden':['이 저장소 자체에 앱의 서비스 계층과 데이터베이스가 있다고 설명한다.']}
}


def write():
    manifest=[]
    for name, spec in CASES.items():
        identifier=name+'-project'
        graph=json.loads((ROOT/'eval/m5/graphs'/f'{identifier}.json').read_text())
        ref=dict(version=1, caseId=identifier, identity={k:graph[k] for k in ('layer','language','subject')}, profiles=[spec['profile']],
                 statuses=['complete'] if name=='utility' else ['partial'], noScenarios=True,
                 requiredFacts=spec['facts'], forbiddenClaims=spec['forbidden'], forbiddenEdges=[],
                 nodes=[dict(key=row[0],file=row[1],line=row[2],codeNames=[row[3]],kind=row[4] if len(row)>4 else 'component',status='confirmed') for row in spec['nodes']],
                 edges=[dict(fromRole=a,type=kind,toRole=b,status='confirmed') for a,kind,b in spec['edges']], regions=spec['regions'],
                 capabilities=[dict({k: s[k] for k in ('id','scope','module','targets','kind')},ownerRole=role)
                               for s,role in zip(graph['subjects'],CAPABILITY_ROLES[name],strict=True)])
        if name=='library':ref['forbiddenEdges']=[dict(fromRole='expiration',type='invokes',toRole='base',status='confirmed')]
        path=ROOT/'eval/m5/expectations'/f'{identifier}.json'
        if not path.exists():author.write_json(path,ref,exclusive=True)
        case=dict(id=identifier,source=spec['source'],profile=spec['profile'],variant='atlas',candidate=f'm5/graphs/{identifier}.json',expectation=f'm5/expectations/{identifier}.json',
                  behaviorId=spec['behavior'],behaviorInput=spec['behaviorInput'],logicInput=spec.get('logicInput',f"m3/graphs/{spec['behavior']}-rules.json"),
                  layout=spec.get('layout',f"m3/layouts/{spec['behavior']}-rules.json"))
        manifest.append(case)
    author.write_json(ROOT/'eval/atlas-cases.json',dict(version=1,sources='m1/sources.json',cases=manifest))


if __name__=='__main__':write()

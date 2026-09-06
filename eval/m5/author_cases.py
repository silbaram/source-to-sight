"""Recorded M5 repository readings. This ledger is not a repository analyzer."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/codebase-atlas/scripts"))
import atlas

s2s, author = atlas.companion()
OUT = Path(__file__).resolve().parent
SOURCES = {s["id"]: s for s in json.loads((ROOT / "eval/m1/sources.json").read_text())}


class Reading:
    def __init__(self, source, profile, title, purpose, includes, excludes):
        self.source = source
        self.root = ROOT / ".cache/m1-sources" / source
        if author.snapshot(self.root)["commit"] != SOURCES[source]["commit"]:
            raise ValueError("Reread the pinned source before updating this ledger.")
        self.data = atlas.draft(self.root, question=title+"의 주요 구성과 기능을 설명해 줘", title=title,
                                module=source, target=source, includes=includes, excludes=excludes,
                                profiles=[profile], repository=SOURCES[source]["repository"])
        self.data["summary"].update(purpose=purpose, limitations=excludes)
        self.data["analysis"].update(status="partial", unresolved=["선택한 공개 기능과 관계를 읽었으며 모든 구현 경로를 추적하지 않았습니다."],
                                     nextAttempts=["관심 기능의 미생성 설명을 선택해 해당 범위를 추가로 읽습니다."])
        self.data["provenance"]["description"] = "고정 소스의 프로젝트 구성과 공개 기능을 읽어 작성한 M5 지도입니다."

    def evidence(self, identifier, file, start, end, symbol, kind="code"):
        self.data["evidence"].append(author.capture_evidence(self.root, identifier, file, symbol, start, end, kind=kind))
        if file not in self.data["analysis"]["searched"]:
            self.data["analysis"]["searched"].append(file)
        return identifier

    def claim(self, ids, note="표시한 역할과 관계를 해당 소스 범위에서 확인했습니다.", uncertain=False):
        return dict(confidence="inferred" if uncertain else "resolved", evidenceIds=list(ids),
                    supportStatus="uncertain" if uncertain else "supported", verificationNote=note)

    def node(self, identifier, label, code, summary, evidence, role="구성 요소", detail=False, boundary=False, uncertain=False):
        self.data["nodes"].append(dict(id=identifier, label=label, codeName=code, summary=summary, roleLabel=role,
                                      kind="boundary" if boundary else "component", importance="detail" if detail else "core",
                                      contextOnly=False, actions=[], **self.claim(evidence, uncertain=uncertain)))

    def edge(self, identifier, source, target, label, kind, evidence, derivation="direct-code"):
        self.data["edges"].append(dict(id=identifier, **{"from": source, "to": target}, label=label, type=kind,
                                      derivation=derivation, **self.claim(evidence)))

    def region(self, identifier, label, summary, nodes, evidence):
        self.data["regions"].append(dict(id=identifier, label=label, summary=summary, nodeIds=nodes, **self.claim(evidence)))

    def capability(self, file, owner, label, summary, evidence, output=None):
        graph = json.loads((ROOT / file).read_text())
        subject = graph["subject"]
        self.data["subjects"].append(dict(**{k: copy.deepcopy(subject[k]) for k in ("id", "kind", "question", "module", "targets", "scope")},
                                         label=label, summary=summary, nodeId=owner, **self.claim(evidence),
                                         link=dict(url=output or Path(file).stem+".html", generated=False, command=graph["regeneration"]["command"])))

    def pending(self, owner, label, file, symbol, includes, excludes, evidence, kind="capability"):
        subject = dict(id=author.subject_key(self.source, symbol, includes, excludes), kind=kind, question=label+"을 설명해 줘",
                       module=self.source, targets=[dict(label=symbol, file=file, symbol=symbol)], scope=dict(includes=includes, excludes=excludes))
        self.data["subjects"].append(dict(**subject, label=label, summary=includes[0], nodeId=owner, **self.claim(evidence),
                                         link=dict(url=subject["id"]+".html", generated=False, command=atlas.generation_request(subject, "ko"))))

    def save(self, name):
        atlas.validate_atlas(self.data, s2s)
        author.write_json(OUT / "graphs" / (name+".json"), self.data)
        print(name, len(self.data["nodes"]), "parts;", len(self.data["subjects"]), "capabilities")


def utility():
    r=Reading("strip-ansi", "cli-utility", "strip-ansi · 문자열을 정리하는 작은 도구",
              "문자열의 터미널 색상·서식 표시를 제거하는 공개 함수를 제공합니다.",
              ["배포 진입점, 공개 함수, 타입 선언과 사용 예제"], ["외부 ansi-regex 구현", "별도 CLI와 스트림 저장소"])
    r.evidence("ev-function", "index.js", 1, 19, "stripAnsi")
    r.evidence("ev-package", "package.json", 13, 25, "exports and types", "config")
    r.evidence("ev-types", "index.d.ts", 15, 15, "stripAnsi type")
    r.evidence("ev-purpose", "readme.md", 1, 3, "package purpose", "documentation")
    r.node("strip", "문자열 서식 정리", "stripAnsi", "문자열을 검사하고 ansi-regex 매처를 이용해 서식 표시를 제거합니다. 배포 진입점과 타입 선언이 이 함수를 공개합니다.", ["ev-function", "ev-package", "ev-types"])
    r.capability("eval/m1/graphs/utility-strip.json", "strip", "서식 표시 제거", "입력 검사부터 문자열 반환까지 살펴봅니다.", ["ev-function"])
    r.capability("eval/m15/graphs/utility-invalid-input.json", "strip", "잘못된 입력 처리", "문자열이 아닌 입력의 오류 경계를 살펴봅니다.", ["ev-function"],output="details/utility-invalid-input.html")
    r.data["analysis"].update(status="complete", unresolved=[], nextAttempts=[])
    r.save("utility-project")
    logic=json.loads((ROOT / "eval/m1/graphs/utility-strip.json").read_text())
    logic["layer"]="logic"
    logic["provenance"]["description"]="공개 함수의 입력 검사를 다시 읽어 이유를 덧붙인 M5 동반 설명입니다."
    logic["rules"][0].update(rationale="문자열 메서드를 쓰기 전에 입력 유형을 검사하므로 의도하지 않은 값의 변환을 막습니다.",
                             exceptions=["문자열 입력은 이 오류 조건에 해당하지 않습니다."])
    logic["regeneration"]["command"] += " --explain"
    author.write_json(OUT / "graphs/utility-strip-rules.json", logic)
    author.write_json(OUT / "layouts/utility-strip-rules.json", dict(version=1, sections=[dict(id="input-contract", title="입력의 약속", kind="conditions", ruleIds=["rule-input"])]))


def framework():
    r=Reading("pluggy", "framework-plugin", "pluggy · 등록된 확장을 호출하는 구조",
              "호스트가 정의한 훅에 플러그인을 등록하고, 호출 결과와 래퍼의 복귀를 관리합니다.",
              ["공개 훅 표식, 등록 관리자, 호출기, 결과와 추적 도구"], ["실제 플러그인의 업무 코드", "entry point 배포 검색과 모든 호환성 경로"])
    for args in [("ev-package","pyproject.toml",8,35,"project","config"),("ev-public","src/pluggy/__init__.py",1,29,"public exports"),
                 ("ev-markers","src/pluggy/_hooks.py",147,162,"HookspecMarker"),("ev-impl-marker","src/pluggy/_hooks.py",264,280,"HookimplMarker"),
                 ("ev-manager","src/pluggy/_manager.py",83,108,"PluginManager._hookexec"),("ev-register","src/pluggy/_manager.py",110,184,"PluginManager.register"),
                 ("ev-call","src/pluggy/_hooks.py",527,542,"HookCaller.__call__"),("ev-loop","src/pluggy/_callers.py",82,174,"_multicall"),
                 ("ev-result","src/pluggy/_callers.py",27,57,"run_old_style_hookwrapper"),("ev-trace","src/pluggy/_manager.py",453,491,"add_hookcall_monitoring")]:r.evidence(*args)
    r.node("markers","확장 지점의 약속","HookspecMarker / HookimplMarker","함수에 훅 명세와 구현 옵션을 기록합니다.",["ev-markers","ev-impl-marker"],"공개 표식")
    r.node("manager","플러그인 등록 관리","PluginManager","플러그인을 보관하고 훅에 맞는 구현을 찾아 등록합니다.",["ev-register"])
    r.node("caller","이름으로 훅 호출","HookCaller","인자와 명세를 확인한 뒤 등록된 구현을 실행기에 전달합니다.",["ev-call"])
    r.node("dispatch","구현 실행과 래퍼 복귀","_multicall","등록된 구현을 호출하고 래퍼의 결과 또는 오류를 되돌립니다.",["ev-loop"])
    r.node("result","결과·오류 전달","Result","호환 래퍼와 추적 경로에서 결과 또는 오류를 담아 전달합니다.",["ev-result","ev-trace"],detail=True)
    r.node("trace","호출 전후 관찰","add_hookcall_monitoring","훅 실행을 감싸 호출 전후의 관찰 함수를 연결합니다.",["ev-trace"],detail=True)
    r.edge("read-markers","manager","markers","구현 옵션 읽기","reads",["ev-register","ev-impl-marker"])
    r.edge("register-caller","manager","caller","훅 구현 등록","registers",["ev-register"],"registration-rule")
    r.edge("execute-through-manager","caller","manager","등록 실행기로 전달","invokes",["ev-call","ev-manager"])
    r.edge("default-dispatch","manager","dispatch","기본 훅 실행","invokes",["ev-manager"])
    r.edge("legacy-result","dispatch","result","호환 래퍼 결과 전달","passes-data",["ev-loop","ev-result"])
    r.edge("install-tracing","manager","trace","실행 관찰 연결","registers",["ev-trace"],"registration-rule")
    r.region("registration","등록과 확장 지점","호스트의 훅 약속과 플러그인 등록을 맡습니다.",["markers","manager"],["ev-markers","ev-register"])
    r.region("calling","호출과 결과","훅 호출, 구현 실행과 결과 전달을 맡습니다.",["caller","dispatch","result"],["ev-call","ev-loop","ev-result"])
    r.capability("eval/m2/graphs/plugin-wrapper-unwind.json","dispatch","래퍼를 거쳐 결과 반환","첫 결과와 오류가 래퍼를 통과하는 과정을 살펴봅니다.",["ev-call","ev-loop"])
    r.capability("eval/m1/graphs/plugin-hooks.json","manager","플러그인 등록부터 호출까지","등록과 호출의 연결을 살펴봅니다.",["ev-register","ev-call"])
    r.capability("eval/m15/graphs/plugin-blocked-registration.json","manager","등록 차단 처리","차단된 플러그인 이름의 등록 처리를 살펴봅니다.",["ev-register"])
    r.save("framework-project")


def agent():
    r=Reading("smolagents","ai-agent","smolagents · 모델과 도구가 협력하는 에이전트",
              "요청을 단계별로 해결하면서 모델, 도구와 코드 실행기를 연결하고 진행 기록을 남깁니다.",
              ["주요 에이전트 방식, 모델·도구 인터페이스, 실행기 선택, 메모리와 CLI 연결"],
              ["모델 응답과 외부 도구의 내부", "Gradio·MCP·웹 브라우저·직렬화의 상세 구현", "원격 실행 환경의 내부와 모든 선택 경로"])
    path="src/smolagents/agents.py"
    for args in [("ev-package","pyproject.toml",5,22,"project","config"),("ev-cli-entry","pyproject.toml",139,141,"project scripts","config"),
                 ("ev-public","src/smolagents/__init__.py",19,32,"public exports"),("ev-setup",path,314,351,"MultiStepAgent.__init__"),
                 ("ev-run",path,468,492,"MultiStepAgent.run"),("ev-loop",path,540,607,"MultiStepAgent._run_stream"),
                 ("ev-tool-agent",path,1215,1245,"ToolCallingAgent"),("ev-tool-model",path,1284,1313,"ToolCallingAgent._step_stream"),
                 ("ev-tool-call",path,1464,1488,"ToolCallingAgent.execute_tool_call"),("ev-code-agent",path,1505,1540,"CodeAgent"),
                 ("ev-parallel",path,1361,1448,"ToolCallingAgent.process_tool_calls"),
                 ("ev-executor",path,1598,1618,"CodeAgent.create_python_executor"),("ev-code-model",path,1677,1683,"CodeAgent._step_stream"),
                 ("ev-execute-code",path,1718,1734,"CodeAgent._step_stream"),("ev-model","src/smolagents/models.py",452,473,"Model"),
                 ("ev-tool","src/smolagents/tools.py",228,249,"Tool.__call__"),("ev-memory","src/smolagents/memory.py",214,246,"AgentMemory"),
                 ("ev-monitor","src/smolagents/monitoring.py",81,112,"Monitor"),("ev-monitor-register",path,421,434,"_setup_step_callbacks"),
                 ("ev-cli","src/smolagents/cli.py",219,259,"run_smolagent")]:r.evidence(*args)
    r.node("runner","실행 반복과 종료","MultiStepAgent","선택한 방식의 한 단계를 실행하고 종료 조건을 확인합니다.",["ev-loop"])
    r.node("tool-agent","도구 호출 방식","ToolCallingAgent","모델이 요청한 도구를 호출하고 관찰 결과를 기록합니다.",["ev-tool-agent","ev-tool-call"])
    r.node("code-agent","코드 작성 방식","CodeAgent","모델이 작성한 코드를 선택한 실행기에 전달합니다.",["ev-code-agent","ev-execute-code"])
    r.node("models","모델 연결","Model","메시지·도구 정보와 모델별 생성 구현을 연결하는 공통 인터페이스입니다.",["ev-model"],"확장 지점")
    r.node("tools","사용 가능한 도구","Tool","도구의 입력을 준비하고 구현 함수를 호출해 결과를 돌려줍니다.",["ev-tool"],"확장 지점")
    r.node("executor","코드 실행 환경","PythonExecutor","코드 방식 에이전트가 로컬 또는 원격 실행기를 선택해 사용합니다. 원격 환경 내부는 제외합니다.",["ev-executor","ev-execute-code"],detail=True)
    r.node("memory","요청과 단계 기록","AgentMemory","요청·행동·계획 단계를 보관하고 다시 메시지나 기록으로 읽습니다.",["ev-memory","ev-run"])
    r.node("monitor","단계 관찰","Monitor","단계의 시간과 제공된 사용량 정보를 모읍니다. 이 지도는 실제 실행 통계를 담지 않습니다.",["ev-monitor"],detail=True)
    r.node("cli","명령으로 시작","smolagent / run_smolagent","명령 옵션에 따라 모델·도구·에이전트 방식을 준비하고 실행을 시작합니다.",["ev-cli-entry","ev-cli"],"명령",detail=True)
    for item in [("tool-strategy","runner","tool-agent","선택한 도구 방식","delegates",["ev-loop","ev-tool-agent"]),
                 ("code-strategy","runner","code-agent","선택한 코드 방식","delegates",["ev-loop","ev-code-agent"]),
                 ("tool-request","tool-agent","models","다음 행동 요청","invokes",["ev-tool-model"]),
                 ("code-request","code-agent","models","코드 생성 요청","invokes",["ev-code-model"]),
                 ("invoke-tool","tool-agent","tools","등록 도구 호출","invokes",["ev-tool-call"]),
                 ("invoke-executor","code-agent","executor","코드 실행 요청","invokes",["ev-execute-code"]),
                 ("save-steps","runner","memory","요청·단계 저장","writes",["ev-run","ev-loop"]),
                 ("observe-step","runner","monitor","단계 콜백 등록","registers",["ev-monitor-register"]),
                 ("start-agent","cli","runner","준비한 에이전트 실행","invokes",["ev-cli"])]:r.edge(*item)
    r.region("execution","실행 제어","공통 반복과 선택한 에이전트 방식이 실행을 이끕니다.",["runner","tool-agent","code-agent"],["ev-loop","ev-tool-agent","ev-code-agent"])
    r.region("adapters","행동과 실행 경계","모델·도구·코드 실행기의 연결을 맡습니다.",["models","tools","executor"],["ev-model","ev-tool","ev-executor"])
    r.region("recording","기록과 관찰","요청과 단계, 단계 관찰 정보를 다룹니다.",["memory","monitor"],["ev-memory","ev-monitor"])
    r.capability("eval/m2/graphs/agent-parallel-tools.json","tool-agent","도구 병렬 처리와 실패 경계","도구 묶음의 실행·결과 기록과 에이전트 반복을 살펴봅니다.",["ev-run","ev-parallel","ev-tool-call","ev-loop"])
    r.capability("eval/m15/graphs/agent-max-steps.json","runner","단계 한계에서 종료","최종 답이 나오지 않았을 때의 종료 경계를 살펴봅니다.",["ev-loop"])
    r.pending("cli","명령으로 에이전트 시작","src/smolagents/cli.py","run_smolagent",["명령 옵션에서 모델·도구·에이전트를 준비하고 run을 호출하는 범위"],["모델·도구의 실제 실행 결과"],["ev-cli-entry","ev-cli"])
    r.pending("executor","코드 실행 환경 선택",path,"CodeAgent.create_python_executor",["로컬·원격 실행기 선택과 초기화"],["원격 실행 환경의 내부"],["ev-executor"])
    r.save("agent-project")


def library():
    r=Reading("golang-lru","library-sdk","golang-lru · 캐시 정책과 공통 저장 구조",
              "최근 사용한 값을 보관하는 캐시와 빈도·만료를 고려하는 변형을 제공합니다.",
              ["루트 캐시, simplelru·expirable 패키지와 별도 arc 모듈의 공개 구성"],
              ["각 정책의 모든 퇴출 경로와 동시 실행 결과", "외부 콜백 내부"])
    for args in [("ev-module","go.mod",1,3,"module","config"),("ev-arc-module","arc/go.mod",1,5,"arc module","config"),
                 ("ev-cache","lru.go",17,44,"Cache / NewWithEvict"),("ev-simple","simplelru/lru.go",15,35,"simplelru.LRU / NewLRU"),
                 ("ev-twoq","2q.go",23,91,"TwoQueueCache / New2QParams"),("ev-arc","arc/arc.go",20,62,"ARCCache / NewARC"),
                 ("ev-expirable","expirable/expirable_lru.go",25,94,"expirable.LRU / NewLRU"),("ev-list","internal/list.go",9,47,"LruList / Entry"),
                 ("ev-resize","lru.go",185,201,"Cache.Resize")]:r.evidence(*args)
    r.node("cache","기본 캐시","Cache","공개 캐시가 잠금을 관리하고 기본 LRU 구현을 사용합니다.",["ev-cache"])
    r.node("twoq","최근·빈도 분리","TwoQueueCache","최근 사용과 반복 사용을 구분하는 캐시 정책입니다.",["ev-twoq"])
    r.node("arc","적응형 캐시","ARCCache","별도 arc 모듈에서 최근 사용과 사용 빈도에 적응하는 캐시를 제공합니다.",["ev-arc","ev-arc-module"],"별도 모듈")
    r.node("expirable","만료되는 캐시","expirable.LRU","유효 기간과 정리 작업을 가진 캐시입니다.",["ev-expirable"],"패키지")
    r.node("simple","기본 퇴출 구조","simplelru.LRU","직접 잠금을 제공하지 않는 기본 LRU 구현으로 여러 캐시 정책에서 사용합니다.",["ev-simple"])
    r.node("list","항목의 순서 보관","LruList / Entry","항목과 연결 목록을 보관하는 내부 자료 구조입니다.",["ev-list"],detail=True)
    for source,evidence in [("cache","ev-cache"),("twoq","ev-twoq"),("arc","ev-arc")]:r.edge(source+"-backend",source,"simple","기본 LRU 생성","invokes",[evidence])
    r.edge("simple-list","simple","list","항목 순서 보관","depends-on",["ev-simple"])
    r.edge("expirable-list","expirable","list","만료 항목 보관","depends-on",["ev-expirable"])
    r.region("policies","공개 캐시 정책","사용할 보관·퇴출 정책을 선택합니다.",["cache","twoq","arc","expirable"],["ev-cache","ev-twoq","ev-arc","ev-expirable"])
    r.region("storage","저장과 순서 관리","기본 LRU와 내부 목록이 항목의 보관 순서를 관리합니다.",["simple","list"],["ev-simple","ev-list"])
    r.capability("eval/m2/graphs/library-resize-callbacks.json","cache","크기 변경과 퇴출 알림","캐시를 줄일 때 제거와 사용자 알림 순서를 살펴봅니다.",["ev-resize"])
    r.capability("eval/m1/graphs/library-eviction.json","cache","값 추가와 오래된 값 제거","추가로 용량을 넘을 때의 기본 동작을 살펴봅니다.",["ev-cache","ev-simple"])
    r.pending("expirable","만료 캐시 초기화","expirable/expirable_lru.go","NewLRU",["크기·유효 기간과 정리 작업을 준비하는 초기화"],["백그라운드 실행 시점과 모든 만료 경로"],["ev-expirable"],"lifecycle")
    r.save("library-project")


def event():
    r=Reading("blinker","data-event","Blinker · 신호와 수신자를 연결하는 구조",
              "이름 있는 신호를 만들고 발신자에 맞는 수신자에게 이벤트를 전달합니다.",
              ["공개 신호·이름 공간, 수신자 등록과 전달, 약한 참조 정리"],["사용자 수신자의 내부", "사용자가 바꾼 집합 순서와 비동기 변환기 구현"])
    for args in [("ev-package","pyproject.toml",1,15,"project","config"),("ev-public","src/blinker/__init__.py",3,17,"public exports"),
                 ("ev-names","src/blinker/base.py",464,496,"NamedSignal / Namespace.signal"),("ev-connect","src/blinker/base.py",73,139,"Signal.connect"),
                 ("ev-send","src/blinker/base.py",237,301,"Signal.send / send_async"),("ev-weak","src/blinker/_utilities.py",42,64,"make_id / make_ref"),
                 ("ev-cleanup","src/blinker/base.py",399,428,"Signal cleanup callbacks")]:r.evidence(*args)
    r.evidence("ev-temporary","src/blinker/base.py",168,189,"Signal.connected_to")
    r.node("namespace","이름으로 신호 찾기","Namespace / NamedSignal","같은 이름으로 요청한 신호를 보관하고 다시 제공합니다.",["ev-names"])
    r.node("signal","등록과 이벤트 전달","Signal","발신자별 수신자를 연결하고 동기 또는 비동기로 호출합니다.",["ev-connect","ev-send"])
    r.node("weakrefs","수신자 수명 관리","make_id / make_ref","수신자 식별과 약한 참조를 만들고 정리 콜백을 연결합니다.",["ev-connect","ev-weak","ev-cleanup"],detail=True)
    r.node("receivers","사용자 수신자","receiver","등록된 함수에 발신자와 이벤트 인자를 전달합니다. 함수 내부는 이 저장소에서 결정하지 않습니다.",["ev-send"],"외부 확장",boundary=True)
    r.edge("named-signal","namespace","signal","이름 있는 신호 생성","invokes",["ev-names"])
    r.edge("receiver-lifetime","signal","weakrefs","참조와 정리 연결","invokes",["ev-connect","ev-weak"])
    r.edge("notify-receiver","signal","receivers","이벤트 인자 전달","dispatches",["ev-send"])
    r.region("subscriptions","신호와 구독 수명","등록된 수신자와 발신자, 참조 정리를 관리합니다.",["signal","weakrefs"],["ev-connect","ev-cleanup"])
    r.capability("eval/m2/graphs/event-async-lifecycle.json","signal","비동기 전달과 임시 구독 해제","수신자 await와 문맥 종료의 관계를 살펴봅니다.",["ev-temporary","ev-send"])
    r.capability("eval/m1/graphs/event-receivers.json","signal","이벤트 수신자 선택","발신자에 맞는 수신자를 고르는 방식을 살펴봅니다.",["ev-connect","ev-send"])
    r.pending("namespace","이름으로 신호 재사용","src/blinker/base.py","Namespace.signal",["이름 조회와 NamedSignal 생성·재사용"],["등록 수신자의 업무 처리"],["ev-names"])
    r.save("event-project")


def web():
    r=Reading("httprouter","web","HttpRouter · 요청을 처리 함수에 연결하는 구조",
              "요청 메서드와 경로를 등록된 함수에 연결하고 경로 매개변수와 대체 응답을 처리합니다.",
              ["공개 라우터, 메서드별 트리, 경로 보정과 매개변수 전달"],["사용자 처리 함수와 Go HTTP 서버 내부", "트리 최적화와 모든 경로 보정의 상세 동작"])
    for args in [("ev-module","go.mod",1,3,"module","config"),("ev-router","router.go",136,178,"Router"),
                 ("ev-register","router.go",292,336,"Router.Handle"),("ev-dispatch","router.go",463,539,"Router.ServeHTTP"),
                 ("ev-tree","tree.go",74,117,"node / addRoute"),("ev-path","path.go",8,45,"CleanPath"),
                 ("ev-params","router.go",86,123,"Handle / Params"),("ev-adapter","router.go",340,357,"Router.Handler")]:r.evidence(*args)
    r.node("router","공개 요청 라우터","Router","경로를 등록하고 요청에 맞는 처리 또는 대체 응답을 선택합니다.",["ev-router","ev-register","ev-dispatch"])
    r.node("tree","메서드별 경로 탐색","node","등록 경로와 처리 함수를 트리에 보관해 일치 여부를 찾습니다.",["ev-tree","ev-dispatch"])
    r.node("path","경로 정리","CleanPath","경로 보정 설정이 켜진 탐색에서 중복 구분자와 상대 경로 부분을 정리합니다.",["ev-path","ev-dispatch"])
    r.node("params","경로 매개변수 전달","Params / Router.Handler","매개변수를 이름으로 조회하거나 표준 HTTP 처리기의 요청 문맥으로 전달합니다.",["ev-params","ev-adapter"],detail=True)
    r.node("handler","앱의 처리 함수","Handle","등록 시 받은 함수가 요청과 경로 매개변수를 받습니다. 앱 내부는 이 지도에 포함하지 않습니다.",["ev-params","ev-dispatch"],"외부 확장",boundary=True)
    r.edge("register-path","router","tree","경로·처리 함수 등록","registers",["ev-register"],"registration-rule")
    r.edge("lookup-path","router","tree","요청 경로 탐색","invokes",["ev-dispatch"])
    r.edge("clean-path","router","path","설정 시 경로 보정","invokes",["ev-dispatch"])
    r.edge("dispatch-handler","router","handler","일치한 함수 호출","invokes",["ev-dispatch"])
    r.edge("pass-params","router","params","요청 문맥에 전달","passes-data",["ev-adapter"])
    r.region("routing","공개 라우팅 기능","등록·요청 처리와 공개 매개변수 전달을 제공합니다.",["router","params"],["ev-register","ev-dispatch","ev-adapter"])
    r.region("matching","경로 매칭","트리와 경로 정리 함수가 요청 경로 해소를 돕습니다.",["tree","path"],["ev-tree","ev-path","ev-dispatch"])
    r.capability("eval/m2/graphs/web-routing-fallbacks.json","router","불일치 요청의 대체 응답","후행 슬래시 보정과 OPTIONS·오류 응답의 선택을 살펴봅니다.",["ev-dispatch"])
    r.capability("eval/m1/graphs/web-dispatch.json","router","등록 경로의 요청 처리","등록된 함수로 요청을 전달하는 과정을 살펴봅니다.",["ev-register","ev-dispatch"])
    r.pending("params","표준 HTTP 처리기 연결","router.go","Router.Handler",["표준 처리기 등록과 경로 매개변수의 요청 문맥 전달"],["처리 함수 내부와 서버 실행"],["ev-adapter"])
    r.save("web-project")


if __name__ == "__main__":
    for build in (utility,framework,agent,library,event,web):build()

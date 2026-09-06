"""Reproduce recorded source readings, not discovery or an independent model run.

The criteria below are separately authored review candidates, NOT a human gold set.
Reread pinned source before changing claims or criteria. Never regenerate approvals.
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval/m1"))
import author_cases as m1

OUT = ROOT / "eval/m15"
CASES = []
GRAPHS = {}


def new(identifier, repo, profile, variant, target, question, includes, excludes, locations):
    g = m1.base(identifier, repo, question, question.rstrip("?"), target, [profile],
                includes, excludes, sorted({x[1] for x in locations}))
    g["provenance"]["description"] = "고정 소스를 읽어 작성한 M1.5 평가 후보입니다. 사람 정답 검토와 독립 생성 평가는 아직 진행하지 않았습니다."
    for key, file, symbol, start, end in locations:
        m1.evidence(g, repo, key, file, symbol, start, end)
    CASES.append(dict(id=identifier, source=repo, profile=profile, variant=variant,
                      sourceLanguage=m1.SOURCES[repo]["language"], origin="new-source-reading"))
    GRAPHS[identifier] = g
    return g


def node(g, key, code, label, summary, ev, uncertain=False, kind="component"):
    return m1.node(g, key, label, "동적 경계" if uncertain else "확인한 역할", summary,
                   [ev], "표시한 소스 범위의 분기와 호출을 읽었습니다. " + summary, code, kind, uncertain)


def edge(g, key, start, end, label, ev, kind="invokes"):
    m1.edge(g, key, start, end, label, kind, [ev], "해당 범위에서 호출 또는 데이터 관계를 확인했습니다. " + label)


def rule(g, key, target, condition, outcome, ev, numeric=False):
    g["rules"].append(dict(id=key, plainText=f"{condition}: {outcome}", condition=condition,
                           outcome=outcome, numeric=numeric, nodeIds=[target],
                           **m1.claim([ev], "해당 조건식과 반환·오류 분기를 직접 읽었습니다.")))


def summary(g, purpose, inputs, outputs, limits):
    g["summary"].update(purpose=purpose, inputs=inputs, outputs=outputs, limitations=limits)


def readings():
    for c in json.loads((ROOT / "eval/m1/cases.json").read_text()):
        CASES.append(dict(id=c["id"], source=c["source"], profile=c["profiles"][0],
                          variant="typical", sourceLanguage=c["language"], origin="m1-recorded-reading"))
        GRAPHS[c["id"]] = json.loads((ROOT / "eval/m1" / c["graph"]).read_text())

    g = new("utility-invalid-input", "strip-ansi", "cli-utility", "boundary", "stripAnsi",
            "stripAnsi에 문자열이 아닌 값을 넘기면 어떻게 되나요?", ["문자열이 아닌 입력의 공개 함수 분기"],
            ["문자열 치환과 의존성 매처 내부"], [("ev-input", "index.js", "stripAnsi", 5, 19)])
    node(g, "check", "stripAnsi", "입력 유형 검사", "문자열이 아니면 TypeError를 발생시키고 이후 치환은 실행하지 않습니다.", "ev-input")
    rule(g, "reject", "check", "입력이 문자열이 아님", "TypeError 발생", "ev-input")
    summary(g, "문자열 외 입력을 거부합니다.", ["문자열이 아닌 값"], ["TypeError"], ["호출자가 오류를 처리하는 방식은 범위 밖입니다."])

    g = new("utility-plain-text", "strip-ansi", "cli-utility", "minimal", "stripAnsi",
            "제어 표시가 없는 문자열도 치환하나요?", ["문자열이며 ESC와 CSI가 모두 없는 빠른 반환"],
            ["제어 표시가 있는 입력과 의존성 구현"], [("ev-plain", "index.js", "stripAnsi", 5, 19)])
    node(g, "plain", "stripAnsi", "원문 반환", "ESC와 CSI가 모두 없으면 빈 문자열을 포함해 입력 문자열을 그대로 반환합니다.", "ev-plain")
    rule(g, "early", "plain", "ESC와 CSI가 모두 없음", "치환 없이 입력 반환", "ev-plain")
    summary(g, "불필요한 치환을 생략합니다.", ["제어 표시가 없는 문자열"], ["원래 문자열"], ["모듈 로딩 때 매처를 만드는 초기화는 이 호출 분기와 별개입니다."])

    file = "src/pluggy/_manager.py"
    g = new("plugin-blocked-registration", "pluggy", "framework-plugin", "boundary", "PluginManager.set_blocked + register",
            "차단한 플러그인 이름을 다시 등록하면 어떻게 되나요?", ["기본 관리자에서 이름 차단과 차단된 이름의 등록"],
            ["서브클래스 재정의와 historic 훅", "차단되지 않은 이름의 등록"],
            [("ev-block", file, "PluginManager.set_blocked", 218, 225), ("ev-unregister", file, "PluginManager.unregister", 190, 216),
             ("ev-register", file, "PluginManager.register", 110, 159)])
    node(g, "block", "PluginManager.set_blocked", "이름 차단", "기존 등록을 해제한 다음 이름에 차단 표시를 남깁니다.", "ev-block")
    node(g, "unregister", "PluginManager.unregister", "기존 등록 해제", "이름으로 기존 플러그인을 찾고, 찾았으면 연결된 훅 구현을 제거합니다.", "ev-unregister")
    node(g, "register", "PluginManager.register", "차단 확인", "같은 이름이 차단되어 있으면 구현 탐색 전에 None을 반환합니다.", "ev-register")
    edge(g, "remove-existing", "block", "unregister", "기존 등록 해제 요청", "ev-block")
    rule(g, "blocked", "register", "이름이 존재하고 값이 None", "등록 없이 None 반환", "ev-register")
    summary(g, "차단된 이름으로 재등록되는 것을 막습니다.", ["차단할 이름", "나중의 동일 이름 등록 요청"], ["차단 표시", "등록 요청의 None 반환"], ["차단과 나중의 등록은 호출자가 각각 요청합니다. 두 메서드가 서로 자동 호출되지는 않습니다."])

    g = new("plugin-unblock", "pluggy", "framework-plugin", "minimal", "PluginManager.unblock",
            "플러그인 이름의 차단을 해제하면 자동으로 다시 등록되나요?", ["unblock의 이름 조회, 삭제와 반환값"],
            ["이후의 명시적 등록과 훅 실행"], [("ev-unblock", file, "PluginManager.unblock", 227, 235)])
    node(g, "unblock", "PluginManager.unblock", "차단 표시 해제", "차단된 이름이면 항목을 삭제하고 True를, 아니면 False를 반환합니다. 플러그인을 다시 등록하지 않습니다.", "ev-unblock")
    rule(g, "removed", "unblock", "이름의 값이 None인 차단 상태", "항목 삭제 후 True 반환", "ev-unblock")
    rule(g, "unchanged", "unblock", "차단된 이름이 아님", "변경 없이 False 반환", "ev-unblock")
    summary(g, "차단 표시만 제거합니다.", ["이름"], ["실제로 차단을 해제했는지 나타내는 참·거짓"], ["자동 재등록과 훅 호출은 없습니다."])

    g = new("library-invalid-capacity", "golang-lru", "library-sdk", "boundary", "simplelru.NewLRU",
            "simplelru.NewLRU에 양수가 아닌 용량을 전달하면 어떻게 되나요?", ["simplelru.NewLRU의 용량 검사와 오류 반환"],
            ["바깥 Cache.NewWithEvict의 반환 계약", "정상 캐시 사용"], [("ev-new", "simplelru/lru.go", "NewLRU", 24, 36)])
    node(g, "new", "simplelru.NewLRU", "용량 검사", "용량이 0 이하이면 내부 캐시를 만들기 전에 nil과 오류를 반환합니다.", "ev-new")
    rule(g, "positive", "new", "용량이 0 이하", "nil과 오류 반환", "ev-new", True)
    summary(g, "유효하지 않은 내부 캐시 용량을 거부합니다.", ["0 이하인 정수 용량"], ["nil 캐시와 오류"], ["상위 래퍼의 반환값을 이 내부 생성자와 동일하다고 가정하지 않습니다."])

    g = new("library-peek", "golang-lru", "library-sdk", "minimal", "Cache.Peek",
            "Cache.Peek는 최근 사용 순서를 바꾸나요?", ["공개 Peek의 읽기 잠금과 내부 조회"],
            ["Get, Add, 퇴출과 사용자 콜백"], [("ev-peek", "lru.go", "Cache.Peek", 112, 119),
                                                    ("ev-inner", "simplelru/lru.go", "LRU.Peek", 87, 94)])
    node(g, "peek", "Cache.Peek", "읽기 잠금으로 조회", "읽기 잠금 안에서 내부 Peek를 호출하고 잠금을 해제한 뒤 결과를 반환합니다.", "ev-peek")
    node(g, "lookup", "simplelru.LRU.Peek", "순서 유지 조회", "항목이 있으면 값과 true를, 없으면 제로 값과 false를 반환하며 최근 사용 순서는 바꾸지 않습니다.", "ev-inner")
    edge(g, "read", "peek", "lookup", "내부 Peek 호출", "ev-peek")
    summary(g, "최근 사용 순서를 유지하며 값을 조회합니다.", ["키"], ["값과 존재 여부"], ["값 자체를 이후 변경하는 동작이나 Get의 순서 갱신은 설명하지 않습니다."])

    g = new("web-invalid-registration", "httprouter", "web", "boundary", "Router.Handle",
            "Router.Handle은 어떤 잘못된 등록 입력을 즉시 거부하나요?", ["메서드, 경로와 핸들러의 진입 검사"],
            ["트리 내부 경로 충돌 검사", "ServeHTTP 요청 처리"], [("ev-guard", "router.go", "Router.Handle", 292, 336)])
    node(g, "guard", "Router.Handle", "등록 입력 검사", "빈 메서드, 비어 있거나 슬래시로 시작하지 않는 경로, nil 핸들러를 순서대로 검사하고 해당되면 panic합니다.", "ev-guard")
    for key, condition in [("method", "메서드가 빈 문자열"), ("path", "경로가 비어 있거나 슬래시로 시작하지 않음"), ("handler", "핸들러가 nil")]:
        rule(g, key, "guard", condition, "경로 저장 전에 panic", "ev-guard")
    summary(g, "등록 입력의 기본 계약을 확인합니다.", ["메서드, 경로, 핸들러"], ["잘못된 입력의 panic"], ["이 검사를 통과해도 트리 삽입 단계의 별도 검사가 실패할 수 있습니다."])

    g = new("web-lookup", "httprouter", "web", "minimal", "Router.Lookup",
            "Router.Lookup은 찾은 핸들러를 실행하거나 리다이렉트하나요?", ["Lookup의 트리 조회와 반환 계약"],
            ["ServeHTTP 실행", "트리 탐색 알고리즘 상세"], [("ev-lookup", "router.go", "Router.Lookup", 394, 407),
                                                           ("ev-tree", "tree.go", "node.getValue", 326, 431)])
    node(g, "lookup", "Router.Lookup", "수동 경로 조회", "메서드의 트리가 있으면 경로를 찾고 핸들러, 매개변수, 후행 슬래시 수정 제안을 반환합니다.", "ev-lookup")
    node(g, "tree", "node.getValue", "경로 검색", "경로에 맞는 핸들러와 매개변수 또는 후행 슬래시 수정 가능 여부를 찾습니다.", "ev-tree")
    edge(g, "find", "lookup", "tree", "메서드 트리가 있을 때 검색", "ev-lookup")
    rule(g, "no-method", "lookup", "메서드에 해당하는 트리가 없음", "nil 핸들러, nil 매개변수, false 반환", "ev-lookup")
    summary(g, "호출자가 사용할 경로 조회 결과만 제공합니다.", ["메서드와 경로"], ["핸들러, 매개변수, 후행 슬래시 제안 여부"], ["Lookup은 반환한 핸들러를 실행하거나 실제 리다이렉트 응답을 보내지 않습니다."])

    file = "src/smolagents/agents.py"
    g = new("agent-unknown-tool", "smolagents", "ai-agent", "boundary", "ToolCallingAgent.execute_tool_call",
            "등록되지 않은 도구 이름을 요청하면 무엇을 실행하나요?", ["도구와 관리 에이전트 목록 결합, 없는 이름의 오류"],
            ["유효한 도구 실행", "호출자의 재시도와 오류 처리"], [("ev-tool", file, "ToolCallingAgent.execute_tool_call", 1453, 1488)])
    node(g, "tool", "ToolCallingAgent.execute_tool_call", "도구 이름 확인", "도구와 관리 에이전트를 합친 목록에 이름이 없으면 인자 변환·검사와 대상 호출 전에 AgentToolExecutionError를 발생시킵니다.", "ev-tool")
    rule(g, "unknown", "tool", "요청한 이름이 합친 목록에 없음", "도구 실행 오류 발생", "ev-tool")
    summary(g, "등록되지 않은 실행 대상의 호출을 막습니다.", ["도구 이름과 인자"], ["AgentToolExecutionError"], ["이 메서드 자체는 모델에 다른 도구를 요청하거나 자동 재시도하지 않습니다."])

    g = new("agent-max-steps", "smolagents", "ai-agent", "dynamic", "MultiStepAgent._run_stream max-steps fallback",
            "에이전트가 단계 한계까지 최종 답을 얻지 못하면 어떻게 마무리하나요?", ["양수 단계 한계, 최종 답 없이 한계에 도달한 대체 답변 경로"],
            ["0 이하 단계 설정", "계획, 사용자 콜백 내부와 정상 최종 답 경로"],
            [("ev-loop", file, "MultiStepAgent._run_stream", 540, 612), ("ev-limit", file, "MultiStepAgent._handle_max_steps_reached", 625, 637),
             ("ev-final", file, "MultiStepAgent.provide_final_answer", 810, 854)])
    node(g, "loop", "MultiStepAgent._run_stream", "단계 한계 확인", "최종 답이 없고 단계 번호가 한계 다음에 도달하면 대체 답변 생성을 요청합니다.", "ev-loop")
    node(g, "fallback", "MultiStepAgent._handle_max_steps_reached", "한계 도달 기록", "대체 답변을 요청하고 AgentMaxStepsError와 그 내용을 메모리에 기록한 뒤 내용을 반환합니다.", "ev-limit")
    node(g, "final", "MultiStepAgent.provide_final_answer", "기록으로 답변 요청", "기록과 요청을 메시지로 구성해 모델을 호출합니다. 생성 예외는 오류 설명 메시지로 바꿉니다.", "ev-final")
    node(g, "model", "model.generate", "실행 시 정해지는 답변", "실제 답변 내용과 성공 여부는 모델 실행 결과에 따라 달라집니다.", "ev-final", True, "boundary")
    edge(g, "at-limit", "loop", "fallback", "최종 답 없이 한계 도달", "ev-loop")
    edge(g, "request-final", "fallback", "final", "대체 답변 요청", "ev-limit")
    edge(g, "generate", "final", "model", "구성한 메시지로 생성 요청", "ev-final")
    rule(g, "limit", "loop", "최종 답이 없고 단계 번호가 max_steps + 1", "대체 답변 경로 실행", "ev-loop", True)
    summary(g, "단계 한계에서 기록을 이용한 대체 답변을 시도합니다.", ["양수 단계 한계와 요청, 실행 기록"], ["모델 답변 또는 생성 오류 설명 메시지의 내용", "한계 도달 오류를 포함한 기록"], [])
    m1.partial(g, "정적 소스로 실제 대체 답변 내용이나 올바른 답변 성공을 확정할 수 없습니다.", "실제 모델 설정과 실행 결과를 별도로 확인합니다.")

    file = "src/blinker/base.py"
    g = new("event-muted", "blinker", "data-event", "boundary", "Signal.muted + send",
            "신호를 muted 문맥 안에서 보내면 수신자에게 나중에 전달되나요?", ["중첩하지 않은 muted 문맥과 그 안의 send"],
            ["중첩 muted, 비동기 send_async", "수신자 내부"], [("ev-muted", file, "Signal.muted", 192, 202),
                                                             ("ev-send", file, "Signal.send", 204, 253)])
    node(g, "muted", "Signal.muted", "임시 음소거", "문맥에 들어갈 때 음소거를 켜고 finally에서 끕니다.", "ev-muted")
    node(g, "send", "Signal.send", "음소거 시 반환", "음소거 중이면 수신자를 선택하거나 호출하기 전에 빈 목록을 반환합니다.", "ev-send")
    rule(g, "silent", "send", "is_muted가 참", "즉시 빈 목록 반환", "ev-send")
    summary(g, "문맥 안에서 신호 전달을 일시적으로 생략합니다.", ["중첩하지 않은 음소거 문맥 안의 send 요청"], ["빈 결과 목록"], ["나중에 다시 전달할 큐를 만들지 않습니다. 중첩 문맥의 이전 상태 복원은 보장하지 않습니다."])

    g = new("event-receiver-check", "blinker", "data-event", "minimal", "Signal.has_receivers_for",
            "has_receivers_for가 참이면 살아 있는 수신자의 호출이 보장되나요?", ["등록 정보의 빠른 존재 여부 확인"],
            ["실제 수신자 순회와 호출"], [("ev-check", file, "Signal.has_receivers_for", 305, 324)])
    node(g, "check", "Signal.has_receivers_for", "등록 여부 확인", "등록 정보와 ANY 또는 발신자 항목을 검사해 참·거짓을 반환합니다. 약한 참조가 살아 있는지는 확인하지 않습니다.", "ev-check")
    summary(g, "등록 정보로 빠르게 수신자 유무를 확인합니다.", ["발신자"], ["참·거짓"], ["True가 실제 살아 있는 수신자의 호출을 보장하지 않습니다. 수신자를 실행하지 않습니다."])


# Review selectors are written from source roles/locations, never inferred from graph IDs.
def role(key, file, line, names=(), kind="component", status="confirmed"):
    return dict(key=key, file=file, line=line, codeNames=list(names), kind=kind, status=status)


def rel(start, end, kind="invokes", status="confirmed"):
    return dict(fromRole=start, toRole=end, type=kind, status=status)


def criteria():
    a, p, b = "src/smolagents/agents.py", "src/pluggy/", "src/blinker/base.py"
    R = role
    specs = {
        "utility-strip": ([R("strip", "index.js", 6, ["stripAnsi"])], [], "complete", True,
                          ["문자열 외 입력은 TypeError", "ESC와 CSI가 모두 없으면 원문 반환", "매처 치환은 의존성 내부 검증과 구별"], ["HTTP 요청/응답 계층을 삽입", "모든 터미널 제어 표시를 제거한다고 보장"]),
        "plugin-hooks": ([R("register", p+"_manager.py", 158, ["PluginManager.register"]), R("caller", p+"_hooks.py", 542, ["HookCaller", "HookCaller.__call__"]), R("dispatch", p+"_manager.py", 108, ["PluginManager._hookexec"]), R("multi", p+"_callers.py", 121, ["_multicall"]), R("plugin", p+"_callers.py", 121, kind="boundary", status="uncertain")],
                         [rel("register", "caller", "registers"), rel("caller", "dispatch"), rel("dispatch", "multi"), rel("multi", "plugin", "dispatches", "uncertain")], "partial", False,
                         ["등록과 나중의 일반 훅 호출을 구분", "firstresult는 첫 결과로 종료 가능", "실제 플러그인 구현·결과는 미해소"], ["일반 등록이 훅 구현을 바로 실행한다고 설명"]),
        "agent-tool-loop": ([R("run", a, 500, ["MultiStepAgent.run"]), R("loop", a, 545, ["_run_stream", "MultiStepAgent._run_stream"]), R("step", a, 1338, ["ToolCallingAgent._step_stream"]), R("model", a, 1338, kind="boundary"), R("tools", a, 1467, ["process_tool_calls / execute_tool_call"]), R("tool", a, 1467, kind="boundary", status="uncertain"), R("memory", a, 601, kind="state"), R("answer", a, 609, kind="artifact")],
                            [rel("run", "loop"), rel("loop", "step"), rel("step", "model"), rel("step", "tools"), rel("tools", "tool", "dispatches", "uncertain"), rel("loop", "memory", "writes"), rel("loop", "loop", "transitions"), rel("loop", "answer", "passes-data")], "partial", False,
                            ["최종 답 여부와 단계 한계로 반복 제어", "모델 생성 오류는 전파, 다른 AgentError는 단계에 기록 가능", "모델 응답과 실제 도구는 런타임에 결정"], ["그림을 실제 실행 순서·횟수 기록이라고 주장", "모든 오류가 정상 최종 답으로 변환된다고 설명"]),
        "library-eviction": ([R("add", "lru.go", 81, ["Cache.Add"]), R("insert", "simplelru/lru.go", 63, ["simplelru.LRU.Add"]), R("remove", "simplelru/lru.go", 178, ["removeOldest / removeElement"]), R("buffer", "lru.go", 54, ["Cache.onEvicted"], "state"), R("callback", "lru.go", 89, ["onEvictedCB"], "boundary", "uncertain")],
                             [rel("add", "insert"), rel("insert", "remove"), rel("remove", "buffer"), rel("add", "callback", "dispatches")], "partial", False,
                             ["새 항목 삽입 뒤 용량 초과에서 가장 오래된 항목 제거", "사용자 콜백은 잠금 해제 뒤 호출", "콜백 내용은 미해소"], ["사용자 콜백이 잠금 안에서 실행된다고 설명"]),
        "web-dispatch": ([R("register", "router.go", 322, ["Router.Handle"]), R("tree", "tree.go", 326, ["node.addRoute / node.getValue"]), R("serve", "router.go", 473, ["Router.ServeHTTP"]), R("handler", "router.go", 475, ["Handle"], "boundary", "uncertain")],
                         [rel("register", "tree", "registers"), rel("serve", "tree"), rel("serve", "handler", "dispatches")], "partial", False,
                         ["등록과 요청 처리 구분", "일치한 경로의 핸들러 호출 후 반환", "애플리케이션 핸들러 본문은 미해소"], ["등록 시 핸들러 실행", "범위 밖 404·405까지 모두 분석했다고 설명"]),
        "event-receivers": ([R("connect", b, 117, ["Signal.connect"]), R("registry", b, 117, ["receivers / _by_sender"], "state"), R("send", b, 240, ["Signal.send"]), R("select", b, 340, ["Signal.receivers_for"]), R("receiver", b, 250, ["receiver"], "boundary", "uncertain")],
                            [rel("connect", "registry", "writes"), rel("send", "select"), rel("select", "registry", "reads"), rel("send", "receiver", "dispatches")], "partial", True,
                            ["ANY와 해당 발신자 수신자를 합침", "수신자 호출 순서는 기본적으로 미정", "수신자 예외는 전파", "실제 수신자 구현은 미해소"], ["연결 순서대로 반드시 호출", "connect가 수신자를 즉시 호출"]),
    }
    for case, file, line, code, facts, forbidden in [
        ("utility-invalid-input", "index.js", 6, "stripAnsi", ["비문자열은 TypeError", "치환 전에 중단"], ["입력을 자동 문자열 변환"]),
        ("utility-plain-text", "index.js", 11, "stripAnsi", ["ESC와 CSI가 모두 없는 문자열은 원문 반환", "빈 문자열도 동일", "모듈 초기화와 호출 분기를 구분"], ["빠른 반환 분기에서 replace 실행"]),
        ("plugin-unblock", p+"_manager.py", 232, "PluginManager.unblock", ["None인 차단 항목 삭제 후 True", "비차단이면 False", "자동 재등록 없음"], ["기존 플러그인을 자동 복구"]),
        ("library-invalid-capacity", "simplelru/lru.go", 25, "simplelru.NewLRU", ["size <= 0이면 nil과 오류", "상위 Cache.NewWithEvict 반환과 구분"], ["0을 무제한 용량으로 허용", "상위 래퍼도 반드시 nil 캐시 반환"]),
        ("web-invalid-registration", "router.go", 295, "Router.Handle", ["빈 메서드 검사", "빈 경로 또는 슬래시 없는 경로 검사", "nil 핸들러 검사", "가드 실패는 저장 전 panic"], ["잘못된 경로를 자동 보정", "입력 가드 통과가 모든 등록 성공을 보장"]),
        ("agent-unknown-tool", a, 1467, "ToolCallingAgent.execute_tool_call", ["합친 등록 목록에 없는 이름은 AgentToolExecutionError", "인자 변환·검사·호출 전 중단"], ["이 함수가 자동 재시도나 모델 호출을 수행"]),
        ("event-receiver-check", b, 315, "Signal.has_receivers_for", ["등록 정보로 참·거짓 확인", "약한 참조 생존 확인 없음", "호출 없음"], ["True면 실제 살아 있는 수신자 호출 보장"]),
    ]:
        specs[case] = ([R("entry", file, line, [code])], [], "complete", True, facts, forbidden)
    specs["plugin-blocked-registration"] = ([R("block", p+"_manager.py", 220, ["PluginManager.set_blocked"]), R("unregister", p+"_manager.py", 209, ["PluginManager.unregister"]), R("register", p+"_manager.py", 128, ["PluginManager.register"])], [rel("block", "unregister")], "complete", True,
        ["기존 등록을 해제한 뒤 이름을 None으로 기록", "같은 차단 이름의 register는 탐색 전 None 반환", "두 진입점은 호출자가 각각 실행"], ["set_blocked가 register를 호출", "차단된 이름의 훅 구현을 실행"])
    specs["library-peek"] = ([R("peek", "lru.go", 115, ["Cache.Peek"]), R("inner", "simplelru/lru.go", 89, ["simplelru.LRU.Peek"])], [rel("peek", "inner")], "complete", True,
        ["읽기 잠금과 해제", "존재 시 값/true, 부재 시 제로 값/false", "최근 사용 순서 유지"], ["MoveToFront 실행", "퇴출 콜백 호출"])
    specs["web-lookup"] = ([R("lookup", "router.go", 396, ["Router.Lookup"]), R("tree", "tree.go", 326, ["node.getValue"])], [rel("lookup", "tree")], "complete", True,
        ["메서드 트리 없으면 nil,nil,false", "찾지 못한 경로도 슬래시 수정 제안 가능", "핸들러와 매개변수 반환"], ["핸들러 실행", "실제 HTTP 리다이렉트 응답 전송"])
    specs["agent-max-steps"] = ([R("loop", a, 606, ["MultiStepAgent._run_stream"]), R("fallback", a, 627, ["MultiStepAgent._handle_max_steps_reached"]), R("final", a, 847, ["MultiStepAgent.provide_final_answer"]), R("model", a, 847, ["model.generate"], "boundary", "uncertain")],
        [rel("loop", "fallback"), rel("fallback", "final"), rel("final", "model")], "partial", True,
        ["양수 한계 범위", "최종 답이 없고 step_number == max_steps + 1일 때 대체 경로", "기록을 사용한 추가 모델 호출", "AgentMaxStepsError와 결과 내용 기록", "모델 생성 예외는 오류 설명 메시지로 변환", "실제 내용·성공은 미해소"], ["한계 도달이면 반드시 올바른 최종 답", "모델 재호출 없이 기존 답만 반환"])
    specs["event-muted"] = ([R("muted", b, 198, ["Signal.muted"]), R("send", b, 237, ["Signal.send"])], [], "complete", True,
        ["비중첩 범위", "문맥 진입 시 True, finally에서 False", "음소거 send는 선택·호출 전 빈 목록", "재전송 큐 없음"], ["문맥 종료 뒤 모은 이벤트 재생", "중첩 이전 상태 복원 보장"])
    return specs


def main():
    readings()
    specs = criteria()
    manifest = dict(version=1, sources="m1/sources.json", cases=[])
    for case in CASES:
        identifier = case["id"]
        g = GRAPHS[identifier]
        nodes, edges, status, unordered, facts, forbidden = specs[identifier]
        reference = dict(version=1, caseId=identifier, review=dict(status="pending", reviewer=None, reviewedAt=None),
                         identity={k: copy.deepcopy(g[k]) for k in ("layer", "language", "subject")},
                         profiles=g["analysis"]["profiles"], statuses=[status], nodes=nodes, edges=edges,
                         noScenarios=unordered, requiredFacts=facts, forbiddenClaims=forbidden,
                         forbiddenEdges=[])
        if identifier == "plugin-hooks":
            reference["forbiddenEdges"] = [rel("register", "caller"), rel("register", "plugin", "dispatches")]
        if identifier == "web-dispatch":
            reference["forbiddenEdges"] = [rel("register", "handler", "dispatches"), rel("register", "tree")]
        if identifier == "plugin-blocked-registration":
            reference["forbiddenEdges"] = [rel("block", "register"), rel("register", "unregister")]
        if identifier == "event-muted":
            reference["forbiddenEdges"] = [rel("muted", "send"), rel("send", "muted")]
        m1.s2s.validate(g)
        m1.author.write_json(OUT / "graphs" / f"{identifier}.json", g)
        reference_path = OUT / "expectations" / f"{identifier}.json"
        # Existing reviews/criteria are never overwritten as a side effect of regenerating graphs.
        if not reference_path.exists():
            m1.author.write_json(reference_path, reference, exclusive=True)
        manifest["cases"].append({**case, "candidate": f"m15/graphs/{identifier}.json",
                                  "expectation": f"m15/expectations/{identifier}.json"})
    m1.author.write_json(ROOT / "eval/cases.json", manifest)


if __name__ == "__main__":
    main()

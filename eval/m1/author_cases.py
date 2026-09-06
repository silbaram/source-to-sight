"""Reproduce agent-authored M1 readings, not automatic repository discovery.

Reread the pinned sources and dependent claims before editing this case ledger.
The three earlier cases reuse M0 graph structure after a new scoped source review.
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import author
import s2s

SOURCES = {s["id"]: s for s in json.loads((ROOT / "eval/m1/sources.json").read_text())}
OUTPUT = ROOT / "eval/m1/graphs"
CASES = []


def source_root(repo):
    return ROOT / ".cache/m1-sources" / repo


def base(identifier, repo, question, title, target, profiles, includes, excludes, searched, kind="capability"):
    graph = author.draft(source_root(repo), question, title, repo, target, includes, excludes, profiles,
                         kind=kind, repository=SOURCES[repo]["repository"])
    graph["provenance"]["description"] = "고정 커밋의 소스를 코딩 에이전트가 읽고 조립한 M1 사례입니다. 독립적인 사람 검토 전입니다."
    graph["analysis"].update(status="complete", searched=searched, unresolved=[], nextAttempts=[])
    CASES.append({"id": identifier, "source": repo, "profiles": profiles,
                  "language": SOURCES[repo]["language"], "question": question,
                  "graph": f"graphs/{identifier}.json", "output": f"{identifier}.html"})
    return graph


def evidence(graph, repo, identifier, file, symbol, start, end, anchor=None):
    graph["evidence"].append(author.capture_evidence(source_root(repo), identifier, file, symbol, start, end, anchor))
    return identifier


def claim(ids, note, uncertain=False):
    return {"confidence": "inferred" if uncertain else "exact", "supportStatus": "uncertain" if uncertain else "supported",
            "verificationNote": note, "evidenceIds": ids}


def node(graph, identifier, label, role, summary, ids, note, code, kind="component", uncertain=False):
    item = {"id": identifier, "kind": kind, "label": label, "roleLabel": role,
            "summary": summary, "codeName": code, "importance": "core", "contextOnly": False,
            "actions": [], **claim(ids, note, uncertain)}
    graph["nodes"].append(item)
    return item


def edge(graph, identifier, start, end, label, kind, ids, note):
    graph["edges"].append({"id": identifier, "from": start, "to": end, "label": label,
                            "type": kind, "derivation": "direct-code", **claim(ids, note)})


def scenario(graph, identifier, title, steps):
    graph["scenarios"].append({"id": identifier, "title": title, "kind": "typical", "steps": [
        {"id": f"{identifier}-{i}", "nodeId": target, "caption": caption, **claim(ids, note)}
        for i, (target, caption, ids, note) in enumerate(steps, 1)]})


def partial(graph, message, next_read):
    graph["analysis"].update(status="partial", unresolved=[message], nextAttempts=[next_read])
    graph["summary"]["limitations"].append(message)


def save(identifier, graph):
    s2s.validate(graph)
    author.write_json(OUTPUT / f"{identifier}.json", graph)


def existing_cases():
    configurations = [
        ("utility-strip", "strip-ansi", "utility-minimum", "stripAnsi는 문자열을 어떻게 검사하고 터미널 서식 표시를 제거하나요?",
         "문자열에서 터미널 서식 표시 제거하기", "stripAnsi", ["cli-utility", "library-sdk"],
         ["공개 함수의 입력 검사, 빠른 반환, 매처를 이용한 치환"], ["ansi-regex 의존성의 정규식 내부", "별도 CLI와 스트림 패키지"],
         ["package.json", "readme.md", "index.js", "test.js"], "capability"),
        ("plugin-hooks", "pluggy", "framework-plugin", "pluggy에서 플러그인 등록과 이후 일반 훅 호출은 어떻게 연결되나요?",
         "플러그인 등록과 훅 호출의 차이", "PluginManager.register + HookCaller.__call__", ["framework-plugin"],
         ["정상 등록과 이후 호스트의 일반 훅 호출", "기본 실행기의 구현 호출과 결과 수집"],
         ["historic 훅과 래퍼의 준비·정리", "추적 실행기 교체", "플러그인의 사용자 정의 동작"],
         ["pyproject.toml", "README.rst", "src/pluggy/_manager.py", "src/pluggy/_hooks.py", "src/pluggy/_callers.py", "testing/test_pluginmanager.py"], "lifecycle"),
        ("agent-tool-loop", "smolagents", "agent-run", "ToolCallingAgent가 요청을 받아 도구를 사용하고 실행을 종료하는 흐름을 설명해 줘.",
         "도구를 사용하는 에이전트의 실행과 종료", "ToolCallingAgent.run", ["ai-agent"],
         ["비스트리밍 반환과 비스트리밍 모델 호출 경로", "도구 선택 경계, 단계 기록과 반복·종료"],
         ["계획 단계", "CodeAgent", "실제 모델·도구의 내부", "콜백과 최종 답변 검사 함수의 내부"],
         ["pyproject.toml", "README.md", "src/smolagents/agents.py", "tests/test_agents.py"], "workflow"),
    ]
    for identifier, repo, fixture, question, title, target, profiles, includes, excludes, searched, kind in configurations:
        graph = base(identifier, repo, question, title, target, profiles, includes, excludes, searched, kind)
        old = json.loads((ROOT / "fixtures" / f"{fixture}.json").read_text())
        for key in ("nodes", "edges", "scenarios", "stateTransitions", "rules", "warnings"):
            graph[key] = copy.deepcopy(old[key])
        graph["summary"].update({k: copy.deepcopy(v) for k, v in old["summary"].items() if k != "title"})
        graph["subject"]["targets"] = [{"label": target, "file": old["evidence"][0]["file"], "symbol": target}]
        for item in old["evidence"]:
            evidence(graph, repo, item["id"], item["file"], item["symbolOrKey"], item["startLine"], item["endLine"])
        if repo == "strip-ansi":
            graph["summary"]["limitations"] = ["의존성 매처의 내부를 분석하지 않았으므로 모든 종류의 터미널 제어 표시 제거를 보장하지 않습니다."]
            graph["nodes"][0]["verificationNote"] = "문자열 유형 검사, ESC/CSI가 없을 때 원문 반환, 매처 치환 반환의 실제 분기를 읽었습니다."
            for rule in graph["rules"]:
                rule["verificationNote"] = "함수 본문의 typeof 검사와 TypeError 발생 분기를 확인했습니다."
        elif repo == "pluggy":
            notes = {
                "register": "구현 표시가 있는 속성을 HookImpl로 만들고 해당 HookCaller의 구현 목록에 추가합니다. historic 경로는 제외했습니다.",
                "caller": "일반 훅의 __call__은 필수 인자를 점검한 뒤 구현 목록의 사본을 _hookexec로 전달합니다.",
                "dispatch": "기본 _inner_hookexec가 _multicall에 연결되고 _hookexec가 이 실행기에 인자를 전달함을 확인했습니다.",
                "multicall": "일반 구현 분기에서 실제 함수를 호출하고 None이 아닌 결과를 수집합니다. firstresult는 추가 호출을 중단할 수 있습니다.",
                "plugin": "등록 객체가 실행 시 제공되므로 구체적 플러그인 구현과 반환 내용은 이 저장소 범위에서 확정하지 않았습니다.",
                "register-hook": "register의 마지막 _add_hookimpl은 등록 관계입니다. 일반 훅 구현을 여기서 실행하는 것으로 해석하지 않았습니다.",
                "call-dispatch": "HookCaller.__call__의 반환식에서 _hookexec 호출을 확인했습니다.",
                "dispatch-multi": "PluginManager 초기화에서 기본 실행기를 지정하고 _hookexec에서 실제로 호출합니다.",
                "multi-plugin": "_multicall의 일반 구현 분기는 hook_impl.function을 호출합니다. 대상과 결과는 등록 목록에 따라 달라집니다.",
            }
            for item in graph["nodes"] + graph["edges"]:
                item["verificationNote"] = notes[item["id"]]
            graph["nodes"][3]["summary"] = "일반 훅 구현을 호출하고 None이 아닌 결과를 모읍니다. 첫 결과만 요구하는 훅은 중간에 멈출 수 있습니다."
            partial(graph, "구체적 플러그인과 그 반환값은 실제 등록 구성에 따라 결정됩니다.", "대상 애플리케이션의 플러그인 등록과 구현을 읽습니다.")
        else:
            notes = {
                "request": "run이 TaskStep을 기록한 뒤 비스트리밍 경로에서 _run_stream을 소비하는 것을 확인했습니다.",
                "loop": "최종 답변 여부와 단계 한계로 while을 제어하고, finally에서 단계 기록과 번호 증가를 수행합니다.",
                "step": "ToolCallingAgent._step_stream의 비스트리밍 generate 호출과 process_tool_calls 소비를 읽었습니다.",
                "model": "generate 호출 위치와 전달 항목은 보이지만 실제 모델 응답·추론 내용은 정적 소스에서 확정할 수 없습니다.",
                "tools": "등록 목록 검사와 인자 검증 후 호출합니다. 하나의 요청은 직접 처리하고 복수 요청은 실행 풀을 사용합니다.",
                "tool": "tools와 managed_agents를 합친 목록에서 이름으로 선택하므로 실제 대상 구현은 런타임 구성에 달려 있습니다.",
                "memory": "_run_stream의 finally에서 action_step을 추가하고, 다음 _step_stream은 기록을 메시지로 변환합니다.",
                "answer": "FinalAnswerStep으로 끝나며 단계 한계에서는 _handle_max_steps_reached를 거칩니다. 오류는 모두 정상 답변으로 바뀌는 것이 아닙니다.",
                "start-loop": "run의 비스트리밍 경로에서 _run_stream을 호출합니다.",
                "loop-step": "while 내부에서 self._step_stream(action_step)을 호출합니다. 선택된 에이전트 클래스는 ToolCallingAgent입니다.",
                "step-model": "stream_outputs 분기의 else에서 self.model.generate를 호출합니다. 실제 응답 내용은 미해소입니다.",
                "step-tools": "모델 응답의 도구 요청을 파싱한 뒤 process_tool_calls로 전달하는 호출을 확인했습니다.",
                "tools-tool": "execute_tool_call이 등록 대상을 찾고 인자를 검증해 도구나 관리 에이전트를 호출합니다.",
                "loop-memory": "단계 성공 또는 처리 가능한 AgentError 뒤에도 finally에서 action_step을 기록합니다.",
                "repeat": "while의 최종 답변·단계 한계 조건이 다음 반복을 결정합니다. 실제 반복 횟수는 기록한 것이 아닙니다.",
                "loop-answer": "반복 종료 후 FinalAnswerStep을 내보냅니다. 한계 도달 경로는 추가 최종 답변 생성을 거칩니다.",
            }
            for item in graph["nodes"] + graph["edges"]:
                item["verificationNote"] = notes[item["id"]]
            graph["summary"]["limitations"] += ["모델 생성 오류는 즉시 전파됩니다. 처리되는 AgentError는 단계에 기록된 뒤 다음 반복으로 이어질 수 있습니다."]
            partial(graph, "실제 모델 응답과 선택되는 도구·위임 대상은 실행 시 결정됩니다.", "실제 모델 설정과 도구·관리 에이전트 등록 구현을 읽습니다.")
        by_id = {item["id"]: item for item in graph["nodes"] + graph["edges"]}
        for flow in graph["scenarios"]:
            for step in flow["steps"]:
                item = by_id[step.get("nodeId") or step["edgeId"]]
                step["verificationNote"] = "캡션을 해당 범위에서 다시 확인했습니다. " + item["verificationNote"]
        save(identifier, graph)


def lru_case():
    repo, identifier = "golang-lru", "library-eviction"
    g = base(identifier, repo, "Cache.Add는 용량이 찼을 때 무엇을 제거하고 사용자 콜백을 언제 호출하나요?",
             "캐시가 오래된 항목을 비우고 알리는 과정", "Cache.Add", ["library-sdk", "framework-plugin"],
             ["일반 Cache에 새 키를 추가해 용량을 초과하는 경로", "퇴출 콜백이 등록된 경우 잠금과 알림의 순서"],
             ["expirable 및 ARC 캐시", "동시 호출 간 전체 순서", "사용자 콜백 내부"],
             ["go.mod", "lru.go", "simplelru/lru.go", "lru_test.go"], "workflow")
    g["subject"]["targets"] = [{"label": "동기화된 캐시의 추가", "file": "lru.go", "symbol": "Cache.Add"}]
    g["summary"].update(purpose="정해진 크기 안에서 최근 사용한 항목을 남기고, 제거된 항목을 호출자에게 알립니다.",
                         inputs=["초기화된 캐시, 새 키와 값, 선택적인 퇴출 콜백"], outputs=["퇴출 발생 여부", "조건을 만족할 때 제거된 키·값의 알림"],
                         limitations=["이미 있는 키는 값을 갱신하고 앞으로 옮기며 퇴출 없이 반환합니다."])
    setup = evidence(g, repo, "ev-setup", "lru.go", "NewWithEvict", 33, 43)
    add = evidence(g, repo, "ev-add", "lru.go", "Cache.Add", 78, 92)
    insert = evidence(g, repo, "ev-insert", "simplelru/lru.go", "LRU.Add", 50, 68)
    remove = evidence(g, repo, "ev-remove", "simplelru/lru.go", "removeOldest/removeElement", 169, 182)
    buffer = evidence(g, repo, "ev-buffer", "lru.go", "Cache.onEvicted", 53, 56)
    node(g, "add", "추가 요청 조율", "공개 API", "잠근 상태에서 캐시를 갱신하고, 잠금을 푼 뒤 필요한 퇴출 알림을 보냅니다.", [add], "Lock, 내부 Add, Unlock, 사용자 콜백의 실제 순서를 확인했습니다.", "Cache.Add")
    node(g, "insert", "항목 추가와 용량 확인", "내부 캐시", "새 항목을 최근 사용 위치에 넣고 용량을 넘으면 오래된 항목 제거를 요청합니다.", [insert], "새 키 분기의 PushFront, 크기 비교, removeOldest 호출을 확인했습니다.", "simplelru.LRU.Add")
    node(g, "remove", "오래된 항목 제거", "퇴출 처리", "목록의 오래된 항목을 찾아 목록과 키 조회에서 제거합니다.", [remove], "Back으로 선택한 항목을 removeElement가 목록과 맵 양쪽에서 제거합니다.", "removeOldest / removeElement")
    node(g, "buffer", "알림할 항목 보관", "공유 상태", "내부 콜백이 제거된 키와 값을 잠시 보관합니다. 공개 추가 함수가 이 내용을 꺼냅니다.", [setup, buffer, add], "NewWithEvict가 내부 콜백을 연결하고 onEvicted가 버퍼에 기록하며 Add가 이를 소비합니다.", "Cache.onEvicted", "state")
    node(g, "callback", "사용자 퇴출 콜백", "외부 경계", "퇴출과 콜백 등록 조건이 맞으면 잠금 해제 후 호출됩니다. 콜백 내부 동작은 호출자가 정의합니다.", [add], "호출 조건과 위치는 확인했으나 실제 콜백 구현은 이 패키지에 고정되지 않았습니다.", "onEvictedCB", "boundary", True)
    edge(g, "add-inner", "add", "insert", "잠근 상태에서 추가", "invokes", [add], "Lock 뒤 c.lru.Add를 호출합니다.")
    edge(g, "insert-remove", "insert", "remove", "용량 초과 시 퇴출", "invokes", [insert, remove], "크기 비교가 참일 때만 removeOldest를 호출합니다.")
    edge(g, "remove-buffer", "remove", "buffer", "등록된 내부 콜백에 기록", "invokes", [setup, remove, buffer], "생성자가 연결한 c.onEvicted를 제거 함수의 onEvict가 호출합니다.")
    edge(g, "add-callback", "add", "callback", "잠금 해제 후 조건부 알림", "dispatches", [add], "Unlock 다음의 콜백 존재 및 evicted 검사 안에서 호출합니다.")
    g["stateTransitions"] = [{"id": "eviction-buffered", "subjectNodeId": "buffer", "from": "알림할 항목 없음", "to": "제거된 항목 보관",
                              "trigger": "퇴출 콜백이 등록되어 있고 새 항목 추가로 오래된 항목이 제거되었을 때",
                              "plainText": "제거한 키와 값을 사용자 알림에 사용할 수 있도록 기록합니다.",
                              **claim([setup, remove, buffer], "등록된 내부 콜백의 키·값 append를 확인했습니다.")}]
    scenario(g, "eviction", "콜백이 등록된 캐시가 용량을 넘는 경우", [
        ("add", "추가 요청이 잠금을 잡고 내부 캐시에 전달됩니다.", [add], "잠금과 내부 호출 순서 확인"),
        ("insert", "새 항목을 넣은 뒤 용량 초과 여부를 확인합니다.", [insert], "기존 키 분기가 아닌 새 키 경로 확인"),
        ("remove", "오래된 항목을 제거합니다.", [remove], "목록과 맵 삭제 확인"),
        ("buffer", "제거한 항목을 내부 알림 버퍼에 기록합니다.", [setup, buffer], "등록된 내부 콜백 연결과 기록 확인"),
        ("add", "버퍼의 값을 꺼내고 잠금을 풉니다. 퇴출과 콜백 등록 조건을 만족하면 사용자에게 알립니다.", [add], "버퍼 소비, Unlock, 조건부 사용자 콜백 순서 확인")])
    partial(g, "사용자가 제공하는 퇴출 콜백의 내부 동작은 미확인입니다.", "호출 애플리케이션의 NewWithEvict 콜백 구현을 읽습니다.")
    save(identifier, g)


def web_case():
    repo, identifier = "httprouter", "web-dispatch"
    g = base(identifier, repo, "httprouter에 등록한 경로가 일치할 때 요청은 어떤 핸들러로 전달되나요?",
             "등록된 경로로 요청을 연결하는 과정", "Router.Handle + Router.ServeHTTP", ["web", "library-sdk"],
             ["정상 경로 등록", "메서드와 경로가 일치한 요청의 핸들러 호출과 매개변수 전달"],
             ["리다이렉트, 경로 미일치 및 메서드 미지원 처리", "사용자 핸들러 내부", "SaveMatchedRoutePath 래퍼", "panic 복구 내부"],
             ["go.mod", "router.go", "tree.go", "router_test.go"], "workflow")
    g["subject"]["targets"] = [{"label": "라우트 등록", "file": "router.go", "symbol": "Router.Handle"}, {"label": "요청 처리", "file": "router.go", "symbol": "Router.ServeHTTP"}]
    g["summary"].update(purpose="등록할 때 저장한 메서드·경로 정보를 사용해 요청을 올바른 처리 함수에 전달합니다.",
                         inputs=["등록할 메서드·경로·핸들러", "일치하는 메서드와 경로의 요청"], outputs=["선택된 핸들러 호출과 경로 매개변수 전달"],
                         limitations=["일치한 경로만 설명합니다. 요청이 없을 때 등록 자체가 핸들러를 실행하지는 않습니다."])
    register = evidence(g, repo, "ev-register", "router.go", "Router.Handle", 292, 336)
    serve = evidence(g, repo, "ev-serve", "router.go", "Router.ServeHTTP", 463, 479)
    lookup = evidence(g, repo, "ev-lookup", "tree.go", "node.getValue", 326, 431)
    insertion = evidence(g, repo, "ev-insertion", "tree.go", "node.addRoute", 109, 119)
    node(g, "register", "경로 등록", "설정", "메서드별 경로 트리에 처리 함수를 등록합니다.", [register], "유효성 검사 후 메서드별 root를 찾거나 만들고 addRoute를 호출합니다.", "Router.Handle")
    node(g, "tree", "메서드별 경로 트리", "탐색", "등록된 경로를 보관하고 일치하는 처리 함수와 매개변수를 찾습니다.", [register, insertion, lookup], "등록 위임과 getValue의 경로 탐색·handle 반환을 읽었습니다. 트리 최적화 내부는 설명하지 않습니다.", "node.addRoute / node.getValue")
    node(g, "serve", "요청 처리", "공개 진입점", "요청 메서드의 트리에서 경로를 찾고 처리 함수가 있으면 호출합니다.", [serve], "req.Method로 root를 선택하고 getValue가 핸들러를 반환한 분기를 확인했습니다.", "Router.ServeHTTP")
    node(g, "handler", "등록된 처리 함수", "외부 경계", "응답 작성 도구, 요청, 경로 매개변수를 받습니다. 함수가 만드는 응답 내용은 애플리케이션에 달려 있습니다.", [serve], "handle 호출 인자는 확인했지만 실제 애플리케이션의 핸들러 내부는 미확인입니다.", "Handle", "boundary", True)
    edge(g, "store-route", "register", "tree", "메서드와 경로로 등록", "registers", [register], "root.addRoute(path, handle)로 보관을 위임합니다.")
    edge(g, "find-route", "serve", "tree", "요청 경로 탐색", "invokes", [serve, lookup], "getValue 호출과 handle·ps 반환을 확인했습니다.")
    edge(g, "invoke-handler", "serve", "handler", "일치한 처리 함수 호출", "dispatches", [serve], "handle이 nil이 아닌 분기에서 매개변수가 있으면 전달하고 없으면 nil로 호출합니다.")
    scenario(g, "match", "등록 후 일치하는 요청이 들어온 경우", [
        ("register", "처리 함수를 메서드와 경로에 등록합니다.", [register], "등록은 addRoute에 위임되며 이 단계에서 핸들러를 호출하지 않음"),
        ("serve", "이후 요청이 들어오면 요청 메서드에 해당하는 트리를 선택합니다.", [serve], "실제 요청 진입은 ServeHTTP이며 register에서 자동 호출되는 것이 아님"),
        ("tree", "경로를 따라 일치하는 처리 함수와 매개변수를 찾습니다.", [lookup], "경로 탐색과 매개변수 수집 및 handle 반환 확인"),
        ("serve", "찾은 함수를 호출하고, 매개변수가 있었다면 반환 후 풀에 돌려놓습니다.", [serve], "handle 호출, putParams, return의 순서 확인")])
    partial(g, "실제 요청 처리 함수가 만드는 응답은 이 라우터 패키지만으로 알 수 없습니다.", "대상 애플리케이션의 Router.Handle 등록과 핸들러 본문을 읽습니다.")
    save(identifier, g)


def event_case():
    repo, identifier = "blinker", "event-receivers"
    g = base(identifier, repo, "Blinker에서 수신자를 연결한 뒤 send하면 누가 호출되고 어떤 결과가 돌아오나요?",
             "발신자에 맞는 이벤트 수신자에게 알리기", "Signal.connect + Signal.send", ["data-event", "library-sdk", "framework-plugin"],
             ["Signal의 수신자 등록과 발신자 필터", "동기 수신자 호출과 결과 수집", "약한 참조의 수신자 정리와 음소거 경계"],
             ["비동기 수신자 어댑터와 send_async", "사용자 수신자 내부", "receiver_connected 보조 신호"],
             ["pyproject.toml", "README.md", "src/blinker/__init__.py", "src/blinker/base.py", "tests/test_signals.py"])
    g["subject"]["targets"] = [{"label": "수신자 등록과 발신", "file": "src/blinker/base.py", "symbol": "Signal.connect / Signal.send"}]
    g["summary"].update(purpose="신호를 구독한 함수 중 발신자 조건에 맞고 살아 있는 수신자에게 내용을 전달합니다.",
                         inputs=["수신자와 발신자 필터의 등록", "발신자와 추가 전달 값"], outputs=["수신자와 반환값의 쌍 목록"],
                         limitations=["기본 수신자 호출 순서는 정해져 있지 않습니다. 그림은 고정된 호출 순서가 아닙니다.", "수신자에서 오류가 나면 호출자에게 전파되므로 모든 수신자가 완료된다고 보장하지 않습니다.", "음소거된 신호는 수신자를 호출하지 않고 빈 결과를 반환합니다."])
    connect = evidence(g, repo, "ev-connect", "src/blinker/base.py", "Signal.connect", 91, 138)
    send = evidence(g, repo, "ev-send", "src/blinker/base.py", "Signal.send", 204, 253)
    select = evidence(g, repo, "ev-select", "src/blinker/base.py", "Signal.receivers_for", 326, 363)
    node(g, "connect", "수신자 연결", "공개 API", "수신 함수와 발신자 조건을 등록합니다. 기본 약한 참조와 명시적인 강한 참조를 구분합니다.", [connect], "weak 분기의 저장 방식과 _by_sender/_by_receiver 기록을 확인했습니다. 보조 연결 신호는 제외했습니다.", "Signal.connect")
    node(g, "registry", "수신자 등록 정보", "공유 상태", "수신자 참조와 발신자별 연결 정보를 보관합니다.", [connect, select], "등록에서 쓴 인덱스를 receivers_for가 조회하는 관계를 확인했습니다.", "receivers / _by_sender", "state")
    node(g, "send", "신호 보내기", "공개 API", "음소거 여부를 확인하고 발신자에 맞는 동기 수신자를 호출한 뒤 결과를 모읍니다.", [send], "is_muted의 빈 반환, receivers_for 반복, 동기 receiver 호출, 결과 append와 반환을 읽었습니다.", "Signal.send")
    node(g, "select", "호출할 수신자 찾기", "선택 규칙", "모든 발신자용 등록과 현재 발신자용 등록을 합치고, 이미 사라진 약한 참조는 건너뜁니다.", [select], "ANY_ID 집합 합치기와 죽은 약한 참조의 disconnect/continue를 확인했습니다.", "Signal.receivers_for")
    node(g, "receiver", "애플리케이션 수신자", "외부 경계", "발신자와 추가 값을 받아 처리합니다. 실제 수신자와 반환 내용은 등록된 구현에 달려 있습니다.", [send, select], "receiver 호출 위치는 확인했지만 실제 등록 객체와 함수 동작은 고정되지 않았습니다.", "receiver", "boundary", True)
    edge(g, "connect-register", "connect", "registry", "발신자 조건과 참조 저장", "writes", [connect], "수신자와 발신자별 인덱스에 기록하는 대입을 확인했습니다.")
    edge(g, "send-select", "send", "select", "발신자에 맞는 후보 요청", "invokes", [send], "for receiver in self.receivers_for(sender) 호출을 확인했습니다.")
    edge(g, "select-registry", "select", "registry", "등록과 참조 조회", "reads", [select], "발신자 집합과 receivers 참조를 조회하며 죽은 참조는 건너뜁니다.")
    edge(g, "send-receiver", "send", "receiver", "선택된 동기 수신자 호출", "dispatches", [send], "동기 else 분기의 receiver(sender, **kwargs) 호출을 확인했습니다. 수신자 간 순서는 보장하지 않습니다.")
    g["rules"] = [{"id": "muted-signal", "plainText": "음소거된 신호는 수신자를 호출하지 않고 빈 결과를 돌려줍니다.",
                   "condition": "신호가 음소거되어 있음", "outcome": "빈 결과 반환", "numeric": False, "nodeIds": ["send"],
                   **claim([send], "수신자 반복 전에 is_muted를 검사하고 빈 목록으로 반환합니다.")}]
    partial(g, "등록된 수신자 집합과 수신자 내부의 실제 결과는 애플리케이션에 달려 있습니다.", "대상 애플리케이션의 connect 호출과 수신자 구현을 읽습니다.")
    save(identifier, g)


if __name__ == "__main__":
    existing_cases()
    lru_case()
    web_case()
    event_case()
    author.write_json(ROOT / "eval/m1/cases.json", CASES)
    print(f"Recorded {len(CASES)} agent-authored source readings; human review remains pending.")

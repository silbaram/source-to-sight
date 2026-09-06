"""Reproduce manually traced M0 contracts; this is not an automatic analyzer."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
from s2s import validate

REPOS = {s["id"]: s for s in json.loads((ROOT / "fixtures/source-repositories.json").read_text())}
synthetic_lines = ["Source to Sight synthetic graph model. Not executable software."]
graphs = {}


def base(identifier, title, profile, kind="workflow", repository=None):
    source = REPOS.get(repository)
    result = {
        "schemaVersion":"0.1.0", "layer":"behavior", "language":"ko",
        "provenance":{"kind":"source-traced" if source else "synthetic",
            "description":"고정 커밋의 실제 코드를 읽고 범위를 정해 추적한 예시입니다." if source else "공통 화면과 데이터 계약을 시험하는 합성 모델입니다.",
            "humanReviewed":False},
        "snapshot":{"repository":source["repository"] if source else "synthetic-model",
            "branch":None,"commit":source["commit"] if source else None,
            "workingTreeClean":True if source else None,"generatedAt":"2026-09-06T03:40:00Z",
            "skillVersion":"0.1.0","model":None},
        "subject":{"id":identifier,"kind":kind,"title":title,"question":title+" 설명해 줘",
            "module":repository or profile,"targets":[{"label":title}],
            "scope":{"includes":[title],"excludes":["외부 시스템과 동적으로 선택되는 구현의 내부"]}},
        "analysis":{"status":"complete","profiles":[profile],"searched":[],
            "unresolved":[],"nextAttempts":[]},
        "summary":{"title":title,"purpose":"","inputs":[],"outputs":[],"limitations":[]},
        **{key:[] for key in ["nodes","edges","scenarios","stateTransitions","rules",
                              "regions","subjects","evidence","warnings","sources"]},
        "links":{},"regeneration":{"subjectId":identifier,"question":title+" 설명해 줘",
            "language":"ko","command":"$code-flow "+title+" 설명해 줘"},
    }
    graphs[identifier] = result
    return result


def ev(graph, identifier, text, file=None, start=None, end=None, anchor=None):
    if file:
        source_id = next(key for key,value in REPOS.items()
                         if value["repository"] == graph["snapshot"]["repository"])
        content = (ROOT / ".cache/sources" / source_id / file).read_bytes()
        lines = content.decode().splitlines()
        evidence = {"id":identifier,"kind":"code","file":file,"symbolOrKey":text,
            "startLine":start,"endLine":end,"anchorText":lines[(anchor or start)-1],
            "contentHash":hashlib.sha256(content).hexdigest(),"locationStatus":"passed"}
    else:
        synthetic_lines.append(f"[{graph['subject']['id']}/{identifier}] {text}")
        evidence = {"id":identifier,"kind":"documentation","file":"fixtures/sources/synthetic.txt",
            "symbolOrKey":identifier,"startLine":len(synthetic_lines),"endLine":len(synthetic_lines),
            "anchorText":synthetic_lines[-1],"contentHash":None,"locationStatus":"passed"}
    graph["evidence"].append(evidence)
    if evidence["file"] not in graph["analysis"]["searched"]:
        graph["analysis"]["searched"].append(evidence["file"])
    return identifier


def claim(evidence_ids, uncertain=False):
    return {"confidence":"inferred" if uncertain else "exact",
        "evidenceIds":evidence_ids,"supportStatus":"uncertain" if uncertain else "supported",
        "verificationNote":"대상 구현은 실행 시 정해져 추가 확인이 필요합니다." if uncertain
            else "표시한 범위에서 이 역할 또는 관계를 확인했습니다."}


def node(graph, identifier, label, summary, evidence_ids=None, kind="component",
         code=None, role="처리", detail=False, uncertain=False):
    ids = evidence_ids or [ev(graph,"ev-"+identifier,summary)]
    n = {"id":identifier,"kind":kind,"label":label,"roleLabel":role,"summary":summary,
         "importance":"detail" if detail else "core","contextOnly":False,"actions":[],
         **claim(ids,uncertain)}
    if code: n["codeName"] = code
    graph["nodes"].append(n)
    return n


def edge(graph, identifier, source, target, label, evidence_ids=None, kind="invokes",
         uncertain=False, derivation=None):
    ids = evidence_ids or [ev(graph,"ev-"+identifier,f"{source} → {target}: {label}")]
    e = {"id":identifier,"from":source,"to":target,"label":label,"type":kind,
         "derivation":derivation or ("direct-code" if graph["provenance"]["kind"] == "source-traced" else "documentation"),
         **claim(ids,uncertain)}
    graph["edges"].append(e)
    return e


def scenario(graph, identifier, title, refs, kind="typical"):
    steps = []
    by_id = {x["id"]:x for x in graph["nodes"]+graph["edges"]}
    for index,(target,caption) in enumerate(refs):
        item = by_id[target]
        steps.append({"id":identifier+"-step-"+str(index+1),
            "edgeId" if "from" in item else "nodeId":target,"caption":caption,
            **claim(item["evidenceIds"],item["supportStatus"]=="uncertain")})
    graph["scenarios"].append({"id":identifier,"title":title,"kind":kind,"steps":steps})


def make_real():
    g = base("utility-minimum","문자열의 터미널 색상 표시 지우기","cli-utility","capability","strip-ansi")
    g["summary"].update(purpose="글자 내용은 유지하면서 터미널의 색상·서식 제어 표시를 제거합니다.",
                         inputs=["문자열"],outputs=["서식 제어 표시를 제거한 문자열"])
    e = ev(g,"ev-strip","stripAnsi","index.js",5,19)
    node(g,"strip","서식 표시 제거","문자열인지 확인한 뒤, 제어 표시가 없으면 그대로 반환하고 있으면 제거합니다.",
         [e],code="stripAnsi",role="공개 함수")
    g["rules"] = [{"id":"rule-input","plainText":"문자열이 아닌 값은 오류로 거부합니다.",
        "condition":"입력이 문자열이 아님","outcome":"유형 오류를 알림","numeric":False,
        "nodeIds":["strip"],**claim([e])}]
    g["links"] = {"logic":{"url":"utility-logic.html","generated":False,
        "command":"$code-flow stripAnsi --explain"},"atlas":{"url":"utility-atlas.html",
        "generated":False,"command":"$codebase-atlas strip-ansi"}}

    g = base("framework-plugin","플러그인이 등록되어 호출되기까지","framework-plugin","lifecycle","pluggy")
    g["summary"].update(purpose="플러그인의 기능을 이름별로 등록하고, 사용자가 그 기능을 요청하면 연결된 구현을 호출합니다.",
        inputs=["플러그인과 훅 호출"],outputs=["등록된 구현의 반환 결과"],
        limitations=["일반 훅의 기본 실행 경로입니다. 과거 호출 재생과 추적 래퍼는 제외합니다."])
    manager="src/pluggy/_manager.py"; hooks="src/pluggy/_hooks.py"; callers="src/pluggy/_callers.py"
    register=ev(g,"ev-register","PluginManager.register",manager,110,159,158)
    caller=ev(g,"ev-caller","HookCaller.__call__",hooks,527,542,542)
    dispatch=ev(g,"ev-dispatch","PluginManager._hookexec",manager,97,108,108)
    multi=ev(g,"ev-multi","_multicall",callers,82,143,130)
    node(g,"register","플러그인 등록","사용 가능한 구현을 찾아 해당 훅에 추가합니다.",[register],code="PluginManager.register",role="등록")
    node(g,"caller","기능 호출 접수","요청에 필요한 인자를 확인하고 등록된 구현 목록을 실행기로 보냅니다.",[caller],code="HookCaller",role="공개 호출")
    node(g,"dispatch","실행기로 전달","설정된 훅 실행기에 이름·구현 목록·인자를 전달합니다.",[dispatch],code="PluginManager._hookexec",role="중계")
    node(g,"multicall","구현들 실행","구현들을 실행하고 반환 결과를 모읍니다. 래퍼는 별도의 준비·정리 순서를 따릅니다.",[multi],code="_multicall",role="실행 제어")
    node(g,"plugin","등록된 플러그인","어떤 구현이 선택되는지는 실제 등록된 플러그인에 따라 달라집니다.",[multi],kind="boundary",role="동적 구현",uncertain=True)
    edge(g,"register-hook","register","caller","훅에 구현 등록",[register],kind="registers")
    edge(g,"call-dispatch","caller","dispatch","호출 전달",[caller,register],derivation="registration-rule")
    edge(g,"dispatch-multi","dispatch","multicall","기본 실행기 호출",[dispatch])
    edge(g,"multi-plugin","multicall","plugin","등록된 구현 실행",[multi],kind="dispatches",uncertain=True)
    scenario(g,"plugin-lifecycle","등록 후 일반 훅 호출",[("register-hook","사용 가능한 구현을 훅에 등록합니다."),
        ("caller","이후 사용자가 그 훅을 호출하면 입력을 확인합니다."),
        ("call-dispatch","호출 정보와 구현 목록을 중계합니다."),
        ("dispatch-multi","기본 실행기로 전달합니다."),
        ("multi-plugin","등록된 구현을 실행합니다. 구체적인 구현은 실행 환경에 달려 있습니다.")],"lifecycle")
    g["analysis"].update(status="partial",unresolved=["실제로 설치할 플러그인 구현은 이 범위에서 정해지지 않았습니다."],
        nextAttempts=["대상 프로젝트의 플러그인 등록 목록을 추가로 확인합니다."])

    g = base("agent-run","에이전트가 도구를 쓰며 답을 완성하는 과정","ai-agent","workflow","smolagents")
    g["summary"].update(purpose="요청을 기록하고 모델에 다음 행동을 요청합니다. 도구 결과를 기록하며, 최종 답변이나 단계 한계에 도달할 때까지 진행합니다.",
        inputs=["사용자의 작업 요청"],outputs=["최종 답변 또는 단계 한계에서 만든 결과"],
        limitations=["ToolCallingAgent의 비스트리밍 모델 호출 경로입니다. 선택적 계획 단계와 개별 도구 내부는 제외합니다."])
    f="src/smolagents/agents.py"
    run=ev(g,"ev-run","MultiStepAgent.run",f,468,503,499)
    loop=ev(g,"ev-loop","MultiStepAgent._run_stream",f,540,612,545)
    step=ev(g,"ev-step","ToolCallingAgent._step_stream",f,1276,1359,1309)
    process=ev(g,"ev-process","ToolCallingAgent.process_tool_calls",f,1361,1442,1392)
    tool=ev(g,"ev-tool","ToolCallingAgent.execute_tool_call",f,1453,1488,1472)
    node(g,"request","요청 기록","사용자의 작업 요청을 실행 기록에 넣고 실행을 시작합니다.",[run],code="MultiStepAgent.run",role="시작")
    node(g,"loop","계속할지 확인","최종 답변 여부와 단계 한계를 확인하며 각 단계를 진행합니다.",[loop],code="_run_stream",role="반복 제어")
    node(g,"step","다음 행동 요청","기록을 메시지로 구성해 모델에 보내고, 반환된 도구 요청을 처리합니다.",[step],code="ToolCallingAgent._step_stream",role="행동 단계")
    node(g,"model","언어 모델","주어진 메시지와 도구 목록으로 응답을 생성합니다. 모델 내부는 이 범위 밖입니다.",[step],kind="boundary",role="외부 경계")
    node(g,"tools","도구 요청 처리","모델이 요청한 도구를 찾고 인자를 검사해 실행합니다. 복수 요청은 병렬로 처리될 수 있습니다.",[process,tool],code="process_tool_calls / execute_tool_call",role="도구 중계")
    node(g,"tool","등록된 도구·에이전트","요청된 이름에 따라 실제 도구 또는 관리되는 에이전트가 선택됩니다.",[tool],kind="boundary",role="동적 대상",uncertain=True)
    node(g,"memory","실행 기록","각 단계의 결과와 오류를 기록해 다음 단계에 활용합니다.",[loop,process],kind="state",role="상태",detail=True)
    node(g,"answer","최종 결과","반복이 끝나면 최종 답변 단계를 반환합니다. 단계 한계에 도달하면 별도의 종료 처리를 거칩니다.",[loop],kind="artifact",role="결과")
    edge(g,"start-loop","request","loop","실행 시작",[run])
    edge(g,"loop-step","loop","step","한 단계 진행",[loop,step],derivation="symbol-resolution")
    edge(g,"step-model","step","model","다음 행동 생성",[step])
    edge(g,"step-tools","step","tools","응답의 도구 요청 처리",[step,process])
    edge(g,"tools-tool","tools","tool","이름에 맞는 대상 실행",[tool],kind="dispatches",uncertain=True)
    edge(g,"loop-memory","loop","memory","결과·오류 기록",[loop],kind="writes")
    edge(g,"repeat","loop","loop","종료 전이면 반복",[loop],kind="transitions")
    edge(g,"loop-answer","loop","answer","종료 결과 반환",[loop],kind="passes-data")
    scenario(g,"agent-typical","도구를 사용하는 한 단계",[("start-loop","요청을 기록하고 실행을 시작합니다."),
        ("loop-step","종료 조건을 확인한 뒤 다음 단계를 진행합니다."),
        ("step-model","이전 기록과 사용 가능한 도구를 모델에 전달합니다."),
        ("step-tools","응답에 포함된 도구 요청을 처리합니다."),
        ("tools-tool","선택된 도구를 실행합니다. 대상과 결과는 실행 시 정해집니다."),
        ("loop-memory","단계의 결과나 오류를 실행 기록에 남깁니다.")])
    scenario(g,"agent-stop","반복과 종료 조건",[("loop","최종 답변과 단계 한계를 확인합니다."),
        ("repeat","아직 종료되지 않았으면 다음 단계를 진행합니다."),
        ("loop-answer","반복을 마치면 최종 결과를 반환합니다.")],"alternate")
    g["analysis"].update(status="partial",unresolved=["모델 응답에 따라 선택할 도구와 실행 결과는 정적으로 확정할 수 없습니다."],
        nextAttempts=["실제 등록 도구와 실행 설정을 확인합니다."])
    g["warnings"]=[{"id":"dynamic-tools","kind":"dynamic-behavior","severity":"medium",
        "message":"점선은 실행 시 선택되는 대상입니다. 실제 실행 기록을 재생하는 화면은 아닙니다.",
        "relatedIds":["tool","tools-tool"],"candidates":[]}]


def make_synthetic():
    cases = [
        ("web-request","검색 요청이 결과가 되기까지","web",[
            ("request","검색 요청","검색어를 받아 처리합니다.","component"),
            ("search","조건에 맞게 찾기","주어진 조건으로 필요한 항목을 찾습니다.","component"),
            ("response","검색 결과","찾은 항목을 화면에 전달합니다.","artifact")]),
        ("cli-transform","입력 파일을 변환해 저장하기","cli-utility",[
            ("input","입력 파일","변환할 자료를 담고 있습니다.","artifact"),
            ("convert","형식 변환","읽은 내용을 목표 형식으로 변환합니다.","component"),
            ("output","결과 파일","변환된 내용을 저장합니다.","artifact")]),
        ("library-use","연결을 열고 사용한 뒤 닫기","library-sdk",[
            ("open","연결 열기","사용에 필요한 자원을 준비합니다.","component"),
            ("use","기능 사용","열린 연결을 통해 기능을 사용합니다.","component"),
            ("close","자원 정리","사용을 마치면 연결을 정리합니다.","component")]),
        ("data-pipeline","두 입력을 합쳐 보고서 만들기","data-event",[
            ("source","자료 수집","처리할 자료를 받습니다.","artifact"),
            ("normalize","값 정리","같은 의미의 값을 공통 형태로 바꿉니다.","component"),
            ("filter","조건 검사","보고서에 필요한 자료를 고릅니다.","component"),
            ("merge","결과 합치기","두 처리 결과를 합칩니다.","component"),
            ("report","보고서","합친 자료를 보고서로 저장합니다.","artifact")]),
    ]
    for identifier,title,profile,spec in cases:
        g=base(identifier,title,profile)
        g["summary"].update(purpose=title+"의 구조와 순서를 보여주는 합성 예시입니다.",
                             inputs=[spec[0][1]],outputs=[spec[-1][1]])
        for id,label,summary,kind in spec: node(g,id,label,summary,kind=kind,role="예시 단계")
        pairs = [("source","normalize"),("source","filter"),("normalize","merge"),("filter","merge"),("merge","report")] if profile=="data-event" else [(spec[i][0],spec[i+1][0]) for i in range(len(spec)-1)]
        for i,(a,b) in enumerate(pairs): edge(g,"edge-"+str(i),a,b,"처리 결과 전달",kind="passes-data")
        if profile!="data-event":
            scenario(g,"normal","대표 사용 순서",[(e["id"],e["label"]) for e in g["edges"]])

    g=base("adversarial","분기와 반복이 많은 작업","data-event")
    g["summary"].update(purpose="복잡한 연결과 미확인 근거가 있어도 사실을 잘라내지 않는지 검사합니다.",
        inputs=["여러 작업"],outputs=["완료 결과 또는 실패 상태"])
    names=["작업 접수","입력 검사","빠른 처리","정밀 처리","결과 합류","재시도 판단","결과 저장","알림 전송","오류 기록","부가 통계","별도 등록 기능"]
    for i,label in enumerate(names):
        node(g,"n"+str(i),label,label+"를 담당하는 합성 구성 요소입니다.",role="합성 단계",detail=i==9)
    pairs=[(0,1),(1,2),(1,3),(2,4),(3,4),(4,5),(5,1),(5,6),(6,7),(1,8),(6,9)]
    for i,(a,b) in enumerate(pairs): edge(g,"edge-"+str(i),"n"+str(a),"n"+str(b),
        "다시 확인" if (a,b)==(5,1) else "오류 시" if b==8 else "다음 처리",
        uncertain=i==10,kind="transitions" if (a,b)==(5,1) else "invokes")
    g["evidence"][0]["endLine"]=999999
    g["evidence"][0]["locationStatus"]="failed"
    scenario(g,"normal","기본 처리",[("edge-0","작업을 검사합니다."),("edge-1","빠른 처리로 진행합니다."),
        ("edge-3","결과를 합칩니다."),("edge-5","재시도 여부를 판단합니다."),("edge-7","완료 결과를 저장합니다.")])
    scenario(g,"failure","입력 오류",[("n1","입력 조건을 확인합니다."),("edge-9","입력이 맞지 않으면 오류를 기록합니다.")],"error")
    g["scenarios"][1]["steps"][0]["branch"]="error"
    g["analysis"].update(status="partial",unresolved=["실행 대상 후보가 여러 개입니다."],
        nextAttempts=["등록 설정에서 실제 대상을 확인합니다."])
    g["warnings"]=[{"id":"ambiguous","kind":"ambiguous-target","severity":"high",
        "message":"두 실행 대상 중 어느 것이 활성화되는지 확인하지 못했습니다.",
        "relatedIds":["n3"],"candidates":[{"label":"빠른 처리 후보","file":"example/fast.js","line":10},
                                       {"label":"정밀 처리 후보","file":"example/deep.js","line":20}]}]
    g=base("insufficient","등록 경로를 찾지 못한 기능","framework-plugin","capability")
    g["summary"].update(purpose="근거가 부족할 때 빈 차트 대신 이유와 다음 시도를 안내합니다.")
    g["analysis"].update(status="insufficient",searched=["설정 파일","공개 등록 함수"],
        unresolved=["실제 등록 위치를 찾지 못했습니다."],nextAttempts=["사용하는 플러그인 이름이나 등록 파일을 지정합니다."])

    # Keep condition text separate from the state summary so omission is visible.
    g=graphs["cli-transform"]
    action=ev(g,"ev-convert-action","변환 단계는 읽은 내용을 목표 형식으로 정리한다.")
    next(n for n in g["nodes"] if n["id"]=="convert")["actions"]=[{
        "id":"convert-content","plainText":"읽은 내용을 목표 형식으로 정리합니다.",**claim([action])}]
    transition=ev(g,"ev-output-saved","출력 파일은 저장에 성공한 경우에만 저장 대기 상태에서 저장 완료 상태로 바뀐다.")
    g["stateTransitions"]=[{"id":"output-saved","subjectNodeId":"output",
        "from":"저장 대기","to":"저장 완료","trigger":"결과 파일 저장에 성공했을 때만",
        "plainText":"결과 파일의 저장 상태가 바뀝니다.",**claim([transition])}]


def write():
    make_real();make_synthetic()
    minimal=graphs["utility-minimum"]
    logic=copy.deepcopy(minimal);logic["layer"]="logic";logic["links"]={
        "behavior":{"url":"utility-minimum.html","generated":False,"command":"$code-flow stripAnsi"}}
    logic["regeneration"]["command"]="$code-flow stripAnsi --explain"
    graphs["utility-logic"]=logic
    atlas=copy.deepcopy(minimal);atlas["layer"]="atlas";atlas["subject"]["id"]="strip-ansi-map"
    atlas["subject"]["kind"]="project";atlas["regeneration"]["subjectId"]="strip-ansi-map"
    atlas["subject"]["question"]="strip-ansi 프로젝트 구성을 설명해 줘"
    atlas["regeneration"]["question"]=atlas["subject"]["question"]
    atlas["regeneration"]["command"]="$codebase-atlas strip-ansi"
    atlas["summary"]["title"]="작은 유틸리티의 프로젝트 지도";atlas["rules"]=[];atlas["links"]={}
    atlas["regions"]=[{"id":"public-api","label":"공개 기능","summary":"문자열 정리를 위한 공개 함수입니다.",
                       "nodeIds":["strip"],**claim(["ev-strip"])}]
    atlas["subjects"]=[{"id":"utility-minimum","label":"서식 표시 제거","nodeId":"strip",
        "link":{"url":"utility-minimum.html","generated":False,"command":"$code-flow stripAnsi"}}]
    graphs["utility-atlas"]=atlas
    source=ROOT/"fixtures/sources/synthetic.txt";source.parent.mkdir(parents=True,exist_ok=True)
    source.write_text("\n".join(synthetic_lines)+"\n")
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    for key,g in graphs.items():
        for evidence in g["evidence"]:
            if evidence["kind"]=="documentation":evidence["contentHash"]=digest
        validate(g)
        (ROOT/"fixtures"/(key+".json")).write_text(json.dumps(g,ensure_ascii=False,indent=2)+"\n")
        print(key)


if __name__=="__main__":
    write()

#!/usr/bin/env python3
"""Render the synthetic bilingual map → behavior → picture-lesson QA fixture."""
import argparse
from copy import deepcopy
import importlib.util
from pathlib import Path

from authored_cases import SOURCE, story_case


def render_learning_fixture(atlas, project, behavior, logic, layout, source, folder, language):
    """Synthetic extra processing node checks data labels and rule isolation."""
    t = lambda ko, en: ko if language == "ko" else en
    behavior, logic, layout = deepcopy(behavior), deepcopy(logic), deepcopy(layout)
    for graph in (behavior, logic):
        owner = deepcopy(next(node for node in graph["nodes"] if node["id"] == "node-main"))
        owner.update(id="node-extra", label=t("별도 처리", "Separate processing"), importance="detail", actions=[])
        graph["nodes"].append(owner)
        transfer = deepcopy(graph["edges"][0])
        transfer.update(id="edge-result", **{"from": "node-main", "to": "node-extra"},
                        label=t("판단 결과", "Decision result"), type="passes-data")
        graph["edges"].append(transfer)
        rule = deepcopy(graph["rules"][0])
        rule.update(id="rule-extra", nodeIds=["node-extra"], plainText=t("별도 처리의 합성 규칙", "Synthetic rule for the separate step"))
        graph["rules"].append(rule)
    layout["sections"].append({"id": "separate", "kind": "authored", "title": t("별도 처리의 그림", "Separate step picture"),
                               "ruleIds": ["rule-extra"], "html": '<svg viewBox="0 0 320 140" role="img" aria-label="Synthetic separate scene"><circle cx="160" cy="70" r="48" fill="none" stroke="currentColor"/></svg>'})
    project = deepcopy(project)
    region = project["regions"][0]
    region.update(parentId="region-domain", interface={"inputs": [t("취소 요청", "Cancellation request")],
        "activity": t("취소 가능 여부 판단", "Decide whether cancellation is allowed"), "outputs": [t("판단 결과", "Decision result")]})
    region["interface"].update(actor=t("주문 처리 프로그램", "Order processing program"),
        entryLabel=t("취소 판단 과정 보기", "See how cancellation is decided"), example={
            "kind": "illustrative",
            "input": {"type": "request", "title": t("이 주문을 취소할 수 있나요?", "Can this order be cancelled?"), "items": ["<request> & example"]},
            "output": {"type": "record", "title": t("판단 결과", "Decision result"), "items": [t("합성 예시의 응답", "Synthetic example response")]}})
    parent = deepcopy(region)
    parent.pop("parentId")
    parent.update(id="region-domain", label=t("주문 영역", "Orders area"), nodeIds=["node-main", "node-caller"])
    caller = deepcopy(region)
    caller.update(id="region-entry", label=t("요청 접수", "Request intake"), nodeIds=["node-caller"])
    caller["interface"].update(activity=t("요청을 받아 전달", "Receive and forward the request"))
    caller["interface"].pop("example")
    project["regions"].extend([caller, parent])
    support = deepcopy(project["nodes"][0])
    support.update(id="node-support", label=t("공통 도구", "Shared tool"), importance="detail", actions=[])
    project["nodes"].append(support)
    group = deepcopy(parent)
    group.update(id="region-support", label=t("공통 지원", "Shared support"), nodeIds=[support["id"]], role="support")
    group.pop("interface")
    project["regions"].append(group)
    edge = deepcopy(project["edges"][0])
    edge.update(id="edge-dependency", **{"from": "node-main", "to": support["id"]}, type="depends-on", label=t("공통 도구 사용", "Use shared tool"))
    project["edges"].append(edge)
    target = folder / "journey"
    atlas.build_site(project, source, target / "project.html", pages=[{
        "behavior": behavior, "output": target / "behavior.html", "logic": logic,
        "layout": layout, "logicOutput": target / "logic.html",
    }])
    uncertain = deepcopy(project)
    next(group for group in uncertain["regions"] if group["id"] == "region-domain")["supportStatus"] = "uncertain"
    atlas.build_site(uncertain, source, target / "uncertain.html")


def render_feature_fixture(atlas, project, behavior, logic, layout, source, folder, language):
    """The same owner can expose two distinct, fully scoped feature previews."""
    project = deepcopy(project)
    project["composition"] = {"regionIds": [project["regions"][0]["id"]], "edgeIds": []}
    behavior, logic = deepcopy(behavior), deepcopy(logic)
    t = lambda ko, en: ko if language == "ko" else en
    for graph in (behavior, logic):
        extra = deepcopy(graph["nodes"][1])
        extra.update(id="node-receive", label="DETAILED RECEIVE", importance="detail")
        graph["nodes"].append(extra)
        groups = []
        for id, label, summary, members in (
            ("group-request", t("요청 접수", "Request intake"), t("취소 요청을 받아 판단에 전달합니다.", "Accepts cancellation requests and passes them to the decision."), ["node-receive", "node-caller"]),
            ("group-decision", t("취소 판단", "Cancellation decision"), t("주문 상태에 따라 취소 결과를 정합니다.", "Determines cancellation from the order status."), ["node-main"]),
        ):
            group = deepcopy(graph["regions"][0])
            group.update(id=id, label=label, summary=summary, nodeIds=members, role="primary")
            groups.append(group)
        graph["regions"] = groups
    second = deepcopy(behavior)
    second["subject"]["id"] = second["regeneration"]["subjectId"] = "cap-second"
    second["subject"]["scope"]["includes"].append("Separate synthetic capability")
    second["nodes"][0]["label"] = "SECOND ONLY"
    second["regions"][1]["label"] = "SECOND ONLY"
    second["scenarios"][0]["steps"][0]["execution"] = "parallel"
    alternate = deepcopy(second["scenarios"][0])
    alternate.update(id="scenario-alternate", title="Alternate synthetic path", kind="alternate")
    for step in alternate["steps"]:
        step["id"] += "-alternate"
        step.pop("execution", None)
    second["scenarios"].append(alternate)
    cap = deepcopy(project["subjects"][0])
    cap.update(id="cap-second", label="SECOND CAPABILITY", scope=deepcopy(second["subject"]["scope"]))
    cap["link"]["url"] = "second.html"
    project["subjects"].append(cap)
    missing = deepcopy(cap); missing.update(id="cap-missing", label="MISSING CAPABILITY")
    missing["scope"]["includes"].append("Missing synthetic detail")
    missing["link"]["url"] = "missing.html"
    project["subjects"].append(missing)
    target = folder / "features"
    result = atlas.build_site(project, source, target / "project.html", pages=[
        {"behavior": behavior, "output": target / "behavior.html", "logic": logic,
         "layout": layout, "logicOutput": target / "logic.html"},
        {"behavior": second, "output": target / "second.html"}])
    uncondensed = deepcopy(result[target / "project.html"])
    for child in uncondensed["featureDetails"]:
        for group in child["regions"]:
            group.pop("role", None)
    s2s, _ = atlas.companion()
    (target / "no-summary.html").write_text(s2s.render(uncondensed), encoding="utf-8")


def render_structure_fixtures(s2s, project, source, folder):
    """Verify literal ancestry independently of path length and input order."""
    fixture = deepcopy(project)
    directory_template, file_template = deepcopy(fixture["structureEntries"])
    for index, directory in enumerate(("R", "_", "가", "R/skipped/nested", "Rextra")):
        relative_file = directory + "/example.py"
        target = source / relative_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(SOURCE, encoding="utf-8")
        evidence = deepcopy(fixture["evidence"][0])
        evidence.update({"id": f"evidence-tree-{index}", "file": relative_file})
        fixture["evidence"].append(evidence)
        for kind, path, template in (("directory", directory, directory_template),
                                     ("file", relative_file, file_template)):
            entry = deepcopy(template)
            entry.update({"id": f"structure-tree-{index}-{kind}", "path": path,
                          "label": path, "evidenceIds": [evidence["id"]]})
            fixture["structureEntries"].append(entry)
    # Children precede parents in authored input. No entry is recorded for
    # R/skipped; its descendant must use the closest *recorded* ancestor R.
    fixture["structureEntries"].reverse()
    for variant in ("rooted", "rootless"):
        data = deepcopy(fixture)
        if variant == "rootless":
            data["structureEntries"] = [entry for entry in data["structureEntries"] if entry["path"] != "."]
        prepared = s2s.prepare(data, source)
        assert all(entry["displayStatus"] == "confirmed" for entry in prepared["structureEntries"])
        (folder / f"entry-tree-{variant}.html").write_text(s2s.render(prepared), encoding="utf-8")


def render_runtime_fixtures(atlas, source, folder, language):
    """Exercise shared controls without imposing their classes on authored HTML."""
    s2s, _ = atlas.companion()
    primer = atlas.load_primer()
    _, _, logic, layout = story_case(language)
    logic["links"]["behavior"] = {"url": "pending.html", "generated": False, "command": "$code-flow synthetic cancellation"}
    section = layout["sections"][0]
    section.update({"css": "", "script": "", "html": '''<section class="rule-figure comparison" data-kind="comparison"><p>Two reviewed outcomes.</p></section>
<section class="rule-figure comparison" data-kind="comparison">
<div class="case-controls" hidden><button type="button" aria-pressed="false">Authored control</button></div>
<article class="rule-case">Not shipped: cancelled.</article><article class="rule-case">Already shipped: manual review.</article>
</section>
<svg viewBox="0 0 20 20"><path d="M0 0 L20 20"/><foreignObject><div>Reviewed</div></foreignObject></svg>
<textarea>Complete explanation</textarea><!-- complete scene annotation -->'''})
    prepared = s2s.prepare(logic, source)
    page, _ = primer.render_rules(prepared, layout, s2s, original=logic)
    (folder / "runtime-authored.html").write_text(page, encoding="utf-8")
    legacy = {"version": 1, "sections": [{"id": "cancellation", "title": section["title"], "kind": "comparison", "ruleIds": section["ruleIds"]}]}
    page, _ = primer.render_rules(prepared, legacy, s2s, original=logic)
    (folder / "runtime-comparison.html").write_text(page, encoding="utf-8")
    # Fault injection: incomplete legacy markup must not stop unrelated controls.
    incomplete = page.replace('class="case-controls"', 'class="incomplete-controls"')
    (folder / "runtime-incomplete.html").write_text(incomplete, encoding="utf-8")
    for name, markup, script in (
        ("navigation", '''<svg viewBox="0 0 160 50"><a data-layer="outcome" href="#scene-cancellation-outcome"><text x="0" y="25">Outcome</text></a></svg>
<a data-layer="atlas" href="#scene-cancellation-outcome">Read the outcome</a>
<p id="scene-cancellation-outcome">Not shipped: cancelled.</p>''', ""),
        ("copy", '''<output>Cancelled</output>
<button type="button" class="copy-command">Copy outcome</button>
<button type="button" class="copy-command" data-command="scene-only-command">Copy outcome again</button>''',
         "root.querySelectorAll('button').forEach(button => button.addEventListener('click', () => navigator.clipboard.writeText(root.querySelector('output').textContent)));"),
    ):
        section.update({"html": markup, "script": script})
        page, _ = primer.render_rules(prepared, layout, s2s, original=logic)
        (folder / f"runtime-{name}.html").write_text(page, encoding="utf-8")


def render_workspace_fixture(s2s, project, source, folder, language):
    """Independent owners prove that selecting a feature cannot mix its context."""
    t = lambda ko, en: ko if language == "ko" else en
    fixture = deepcopy(project)
    other = deepcopy(fixture["nodes"][0])
    other.update({"id": "node-review", "label": t("출고 후 검토", "Post-shipment review"),
                  "summary": t("출고된 주문의 별도 검토 결과입니다.", "The manual-review outcome for shipped orders."), "actions": []})
    fixture["nodes"].append(other)
    group = deepcopy(fixture["regions"][0])
    group.update({"id": "region-review", "label": other["label"], "nodeIds": [other["id"]]})
    fixture["regions"].append(group)
    subject = deepcopy(fixture["subjects"][0])
    subject.update({"id": "subject-review", "nodeId": other["id"], "label": t("출고 후 결과 살펴보기", "Explore the shipped outcome"),
                    "summary": other["summary"]})
    subject["link"].update({"url": "review.html", "generated": False,
                            "command": f"$code-flow synthetic post-shipment review | subject={subject['id']} | language={language}"})
    fixture["subjects"].append(subject)
    fixture["rules"][1]["nodeIds"] = [other["id"]]
    scenario = deepcopy(fixture["scenarios"][0])
    scenario.update({"id": "scenario-review", "title": other["label"], "kind": "alternate"})
    step = deepcopy(scenario["steps"][-1])
    step.update({"id": "step-review", "nodeId": other["id"], "branch": "alternate",
                 "caption": t("별도 검토 결과를 반환합니다.", "Return manual review."),
                 "condition": t("이미 출고되었을 때", "When already shipped")})
    scenario["steps"] = [step]
    fixture["scenarios"].append(scenario)
    fixture["structureEntries"][1]["nodeIds"].append(other["id"])
    test_source = 'from example import check\n\ndef test_unshipped():\n    assert check(False) == "cancelled"\n'
    (source / "test_example.py").write_text(test_source, encoding="utf-8")
    test = deepcopy(fixture["evidence"][0])
    test.update({"id": "ev-linked-test", "kind": "test", "file": "test_example.py", "startLine": 3,
                 "endLine": 4, "symbolOrKey": "test_unshipped", "anchorText": "def test_unshipped():"})
    fixture["evidence"].append(test)
    fixture["subjects"][0]["evidenceIds"].append(test["id"])
    (folder / "entry-workspace.html").write_text(s2s.render(s2s.prepare(fixture, source)), encoding="utf-8")
    # Uneven groups (three capabilities versus one) exercise the visual boundary
    # and filtered group counts without inventing extra graph connections.
    grouped = deepcopy(fixture)
    for name, label in (("condition", t("취소 조건 살펴보기", "Explore cancellation conditions")),
                        ("result", t("취소 결과 살펴보기", "Explore cancellation results"))):
        capability = deepcopy(grouped["subjects"][0])
        capability.update({"id": "subject-" + name, "label": label})
        capability["link"].update({"url": name + ".html", "generated": False,
                                    "command": f"$code-flow synthetic {name} | subject={capability['id']} | language={language}"})
        grouped["subjects"].append(capability)
    (folder / "entry-groups.html").write_text(s2s.render(s2s.prepare(grouped, source)), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory for synthetic QA artifacts")
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists():
        parser.error("Use a new output directory; existing files are not overwritten.")
    source = root / "source"
    source.mkdir(parents=True)
    (source / "example.py").write_text(SOURCE, encoding="utf-8")
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("demo_atlas", repo / "skills/codebase-atlas/scripts/atlas.py")
    atlas = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(atlas)
    for language in ("ko", "en"):
        project, behavior, logic, layout = story_case(language)
        t = lambda ko, en: ko if language == "ko" else en
        project["summary"]["purpose"] = t(
            "취소 요청을 받아 출고 여부를 확인하고, 취소 완료 또는 별도 검토 결과를 돌려줍니다.",
            "Receives a cancellation request, checks shipment, and returns cancelled or manual review.")
        project["subject"]["scope"]["excludes"] = deepcopy(behavior["subject"]["scope"]["excludes"])
        project["analysis"].update({"status": "partial", "unresolved": [t(
            "실제 배송 시스템과의 연결은 확인하지 않았습니다.", "Integration with a real shipping system has not been checked.")],
            "nextAttempts": [t("실제 서비스에 적용하기 전에 배송 연동을 확인하세요.", "Review shipping integration before using this in a real service.")]})
        project["summary"]["limitations"] = [t(
            "작은 합성 예제이며 실제 서비스 전체를 분석한 결과가 아닙니다.", "A small synthetic example, not an analysis of an entire real service.")]
        steps = project["scenarios"][0]["steps"]
        steps[0]["caption"] = t("취소 판단을 요청합니다.", "Request a cancellation decision.")
        for step_id, caption, condition in (
            ("step-shipment", t("출고 여부를 확인합니다.", "Check shipment state."), t("취소 요청을 받았을 때", "When cancellation is requested")),
            ("step-cancelled", t("취소 완료를 반환합니다.", "Return cancelled."), t("아직 출고되지 않았을 때", "When the order has not shipped")),
        ):
            step = deepcopy(steps[0])
            step.pop("edgeId")
            step.update({"id": step_id, "nodeId": "node-main", "caption": caption, "condition": condition})
            steps.append(step)
        project["rules"][0]["exceptions"] = [t(
            "출고된 주문은 별도 검토 경로로 갑니다.", "Shipped orders take the manual-review path.")]
        folder = root / language
        rendered = atlas.build_site(project, source, folder / "project.html", pages=[{
            "behavior": behavior, "output": folder / "behavior.html", "logic": logic,
            "layout": layout, "logicOutput": folder / "logic.html",
        }])
        s2s, _ = atlas.companion()
        render_learning_fixture(atlas, project, behavior, logic, layout, source, folder, language)
        render_feature_fixture(atlas, project, behavior, logic, layout, source, folder, language)
        render_workspace_fixture(s2s, project, source, folder, language)
        for variant in ("legacy", "missing", "empty", "uncertain", "ungrouped", "narrative-empty", "narrative-uncertain"):
            fixture = deepcopy(rendered[(folder / "project.html").resolve()])
            if variant == "legacy":
                fixture.pop("structureEntries")
                fixture["subjects"] = [{key: subject[key] for key in ("id", "label", "nodeId", "link")}
                                       for subject in fixture["subjects"]]
            if variant == "missing":
                for subject in fixture["subjects"]:
                    subject["link"]["generated"] = False
            if variant == "empty":
                fixture["subjects"] = []
            if variant == "uncertain":
                fixture["structureEntries"][0].update({"confidence": "inferred", "supportStatus": "uncertain", "displayStatus": "uncertain"})
            if variant == "ungrouped":
                fixture["regions"] = []
            if variant == "narrative-empty":
                fixture["scenarios"] = []
                fixture["rules"] = []
                fixture["analysis"].update({"status": "complete", "unresolved": [], "nextAttempts": []})
                fixture["summary"]["limitations"] = []
                fixture["subject"]["scope"]["excludes"] = []
            if variant == "narrative-uncertain":
                # Presentation-only fault injection, not a source-backed
                # assertion that this sequential example actually runs in parallel.
                fixture["scenarios"][0]["steps"][1].update({
                    "confidence": "inferred", "supportStatus": "uncertain", "displayStatus": "uncertain",
                    "execution": "parallel", "branch": "alternate",
                    "caption": t("합성 병렬 구간 · 화면 검증용", "Synthetic parallel segment · presentation test")})
                fixture["rules"][0].update({"confidence": "inferred", "supportStatus": "uncertain", "displayStatus": "uncertain"})
            (folder / f"entry-{variant}.html").write_text(s2s.render(fixture), encoding="utf-8")
        # Documentation may establish a stated convention, not code-wide compliance.
        documented = deepcopy(project)
        rule_document = source / "CONTRIBUTING.md"
        rule_document.write_text("Keep cancellation outcomes distinct.\n", encoding="utf-8")
        evidence = deepcopy(documented["evidence"][0])
        evidence.update({"id": "ev-documentation", "kind": "documentation", "file": "CONTRIBUTING.md",
                         "startLine": 1, "endLine": 1, "symbolOrKey": "Cancellation convention",
                         "anchorText": "Keep cancellation outcomes distinct."})
        documented["evidence"].append(evidence)
        rule = deepcopy(documented["rules"][0])
        rule.update({"id": "rule-documentation", "evidenceIds": ["ev-documentation"], "exceptions": [],
                     "plainText": t("문서는 취소 결과를 구분하도록 정합니다.", "The document requires distinct cancellation outcomes."),
                     "condition": t("결과를 수정할 때", "When changing outcomes"),
                     "outcome": t("취소와 검토 결과를 구분합니다.", "Keep cancellation and review outcomes distinct."),
                     "rationale": t("프로젝트 규약에 명시되어 있습니다.", "Stated in the project convention.")})
        documented["rules"] = [rule]
        numeric = deepcopy(rule)
        numeric.update({"id": "rule-numeric-unverified", "numeric": True, "supportStatus": "uncertain",
                        "confidence": "inferred", "plainText": "Retry 7 times."})
        documented["rules"].append(numeric)
        prepared = s2s.prepare(documented, source)
        assert [rule["id"] for rule in prepared["rules"]] == ["rule-documentation"]
        (folder / "entry-narrative-documentation.html").write_text(s2s.render(prepared), encoding="utf-8")
        render_structure_fixtures(s2s, project, source, folder)
        render_runtime_fixtures(atlas, source, folder, language)
        if language == "en":
            # These tags satisfy the IR contract, but some are rejected by
            # browser Intl implementations. Keep the original language data.
            for locale in ("en-GB-oed", "en-foo", "ko-foo", "en-US", "ko-KR"):
                fixture = deepcopy(project)
                fixture["language"] = fixture["regeneration"]["language"] = locale
                page = s2s.render(s2s.prepare(fixture, source))
                (folder / f"entry-locale-{locale}.html").write_text(page, encoding="utf-8")
        print(folder / "project.html")


if __name__ == "__main__":
    main()

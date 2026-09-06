#!/usr/bin/env python3
"""Build a source-backed rules explainer and its matching behavior page."""
from __future__ import annotations

import argparse
import base64
import copy
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote

from jsonschema import Draft202012Validator, ValidationError

SKILL = Path(__file__).resolve().parents[1]


def companion(root=None):
    root = Path(root).resolve() if root else SKILL.parent / "code-flow"
    if not (root / "scripts/author.py").is_file():
        raise ValueError("Source-backed rules need code-flow. Supply its installed --code-flow-root.")
    sys.path.insert(0, str(root / "scripts"))
    import s2s
    import author
    if s2s.SKILL != root:
        raise ValueError("Another code-flow installation is already loaded; use a fresh process.")
    return s2s, author


def validate_shared(behavior, logic, s2s):
    s2s.validate(behavior)
    s2s.validate(logic)
    if behavior["layer"] != "behavior" or logic["layer"] != "logic":
        raise ValueError("The pair needs an internal behavior graph and an internal logic graph.")
    for key in ("subject", "language", "nodes", "edges", "scenarios", "stateTransitions", "regions", "subjects"):
        if behavior[key] != logic[key]:
            raise ValueError(f"Rules must retain the behavior's {key}; update and review the behavior first.")
    for key in ("repository", "commit"):
        if behavior["snapshot"][key] != logic["snapshot"][key]:
            raise ValueError(f"The pair has a different source {key}.")
    evidence = {e["id"]: e for e in logic["evidence"]}
    if any(evidence.get(e["id"]) != e for e in behavior["evidence"]):
        raise ValueError("Keep the behavior's evidence intact; append evidence for new rules.")
    rules = {r["id"]: r for r in logic["rules"]}
    for original in behavior["rules"]:
        rule = rules.get(original["id"], {})
        if any(rule.get(k) != original[k] for k in ("plainText", "condition", "outcome", "numeric", "nodeIds")):
            raise ValueError("An existing rule changed meaning; review the behavior first.")
        if not set(original["evidenceIds"]) <= set(rule["evidenceIds"]):
            raise ValueError("An existing rule lost its behavior evidence.")


def validate_layout(layout, graph, s2s):
    schema = json.loads((SKILL / "references/rule-layout.schema.json").read_text())
    Draft202012Validator(schema).validate(layout)
    ids = [s["id"] for s in layout["sections"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Figure IDs must be unique.")
    rules = {r["id"]: r for r in graph["rules"]}
    transitions = {s["id"]: s for s in graph["stateTransitions"]}
    for section in layout["sections"]:
        if not set(section["ruleIds"]) <= set(rules) or not set(section.get("transitionIds", [])) <= set(transitions):
            raise ValueError("A figure references an unknown rule or state transition.")
        if any(not rules[r].get("rationale", "").strip() for r in section["ruleIds"]):
            raise ValueError("Each illustrated rule needs a reviewed rationale.")
        owners = {n for r in section["ruleIds"] for n in rules[r]["nodeIds"]}
        if any(transitions[s]["subjectNodeId"] not in owners for s in section.get("transitionIds", [])):
            raise ValueError("State figures must concern the selected rules' nodes.")
    s2s.ensure_no_source_bodies(layout, [e.get("anchorText", "") for e in graph["evidence"]])


def escaped(value):
    return html.escape(str(value), quote=True)


def encoded(data):
    value = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for character, replacement in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                                   ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        value = value.replace(character, replacement)
    return value


def render_rules(data, layout, s2s, original=None):
    s2s.validate(data, "render")
    s2s.ensure_no_source_bodies(data)
    validate_layout(layout, original or data, s2s)
    t = lambda ko, en: ko if data["language"].lower().startswith("ko") else en
    rules = {r["id"]: r for r in data["rules"]}
    states = {s["id"]: s for s in data["stateTransitions"]}
    evidence = {e["id"]: e for e in data["evidence"]}
    labels = {"confirmed": t("위치·내용 확인", "Location & claim checked"),
              "uncertain": t("추정 · 추가 확인 필요", "Uncertain · needs review"),
              "unverified": t("근거 위치 미확인", "Location unverified")}

    def badge(item):
        status = item["displayStatus"]
        return f'<span class="pill {status}">{labels[status]}</span>'

    def locations(item):
        blocks = []
        for identifier in item["evidenceIds"]:
            e = evidence[identifier]
            label = t("위치 일치", "Location matches") if e["locationStatus"] == "passed" else t("위치 미확인", "Location unverified")
            blocks.append(f'<li><span>{label}</span><strong>{escaped(e["file"])}</strong>'
                          f'<span>{t("줄", "Lines")} {e["startLine"]}–{e["endLine"]}</span></li>')
        return '<ul class="rule-locations">' + ''.join(blocks) + '</ul>'

    def explanation(rule):
        result = '<div class="rule-reason"><h3>' + t("왜 이렇게 되나요?", "Why does this happen?") + '</h3><p>' + escaped(rule["rationale"]) + '</p></div>'
        if rule.get("exceptions"):
            result += '<div class="rule-exceptions"><h3>' + t("예외와 적용 범위", "Exceptions and scope") + '</h3><ul>'
            result += ''.join('<li>' + escaped(x) + '</li>' for x in rule["exceptions"]) + '</ul></div>'
        result += '<details class="rule-evidence"><summary>' + t("근거와 전체 설명", "Evidence and full explanation") + '</summary>'
        result += '<p>' + escaped(rule["plainText"]) + '</p><p>' + escaped(rule["verificationNote"]) + '</p>' + locations(rule) + '</details>'
        return result

    def case(rule, identifier):
        return (f'<article class="rule-case" id="{identifier}" data-rule-id="{escaped(rule["id"])}">' + badge(rule) +
                '<div class="condition-result"><div class="rule-condition"><h3>' + t("이 조건이면", "When") + '</h3><p>' + escaped(rule["condition"]) + '</p></div>' +
                '<span class="figure-arrow" aria-hidden="true">→</span><div class="rule-outcome"><h3>' + t("이렇게 처리합니다", "Then") + '</h3><p>' + escaped(rule["outcome"]) + '</p></div></div>' +
                explanation(rule) + '</article>')

    figures, contents, omitted = [], [], []
    for section in layout["sections"]:
        identifier = 'figure-' + section["id"]
        title = escaped(section["title"])
        contents.append(f'<a href="#{identifier}">{title}</a>')
        heading = f'<h2 id="{identifier}-title">{title}</h2>'
        if not set(section["ruleIds"]) <= set(rules) or not set(section.get("transitionIds", [])) <= set(states):
            omitted.append(section["id"])
            figures.append(f'<section class="rule-figure withheld" id="{identifier}">{heading}<p>' +
                           t("검증 자료가 부족해 이 그림을 생략했습니다. 아래 확인할 점을 살펴보세요.",
                             "This figure was withheld because its supporting claims could not be verified. See the notices below.") + '</p></section>')
            continue
        chosen = [rules[r] for r in section["ruleIds"]]
        body = ''
        if section["kind"] == "comparison":
            body += '<div class="case-controls" role="group" aria-label="' + t("비교할 조건 선택", "Choose a condition to compare") + '" hidden>'
            for i, rule in enumerate(chosen):
                body += f'<button type="button" data-case="{i}" aria-controls="{identifier}-case-{i}" aria-pressed="false">{escaped(rule["condition"])}</button>'
            body += '</div>'
        for state_id in section.get("transitionIds", []):
            state = states[state_id]
            body += '<article class="state-picture" data-transition-id="' + escaped(state_id) + '">' + badge(state)
            body += '<p class="state-trigger">' + t("변경 조건: ", "Trigger: ") + escaped(state["trigger"]) + '</p><div class="condition-result">'
            body += '<div class="rule-condition"><h3>' + t("이전 상태", "Before") + '</h3><p>' + escaped(state["from"]) + '</p></div>'
            body += '<span class="figure-arrow" aria-hidden="true">→</span><div class="rule-outcome"><h3>' + t("이후 상태", "After") + '</h3><p>' + escaped(state["to"]) + '</p></div></div>'
            body += '<details class="rule-evidence"><summary>' + t("상태 변화 근거", "State evidence") + '</summary><p>' + escaped(state["plainText"]) + '</p><p>' + escaped(state["verificationNote"]) + '</p>' + locations(state) + '</details></article>'
        body += ''.join(case(rule, identifier + '-case-' + str(i)) for i, rule in enumerate(chosen))
        figures.append(f'<section class="rule-figure {section["kind"]}" data-kind="{section["kind"]}" id="{identifier}" aria-labelledby="{identifier}-title">{heading}{body}</section>')

    links = []
    for kind, link in data["links"].items():
        label = {"behavior": t("동작과 협력으로 돌아가기", "Back to how it works"),
                 "atlas": t("프로젝트 지도", "Project map"), "logic": t("규칙과 이유", "Rules and reasons")}[kind]
        if link["generated"]:
            links.append(f'<a href="{escaped(link["url"])}">{label} ↗</a>')
        else:
            links.append(f'<button type="button" class="copy-command" data-command="{escaped(link["command"])}">{label} · {t("생성 명령 복사", "copy generation command")}</button>')
    notices = ''.join('<li>' + escaped(w["message"]) + '</li>' for w in data["warnings"])
    scope = ''
    for title, values in ((t("포함한 범위", "Included"), data["subject"]["scope"]["includes"]),
                          (t("제외한 범위", "Excluded"), data["subject"]["scope"]["excludes"]),
                          (t("확인하지 못한 내용", "Unresolved"), data["analysis"]["unresolved"]),
                          (t("한계", "Limitations"), data["summary"]["limitations"]),
                          (t("탐색한 위치", "Searched"), data["analysis"]["searched"]),
                          (t("다음 시도", "Next attempts"), data["analysis"]["nextAttempts"])):
        if values:
            scope += '<div><h3>' + title + '</h3><ul>' + ''.join('<li>' + escaped(v) + '</li>' for v in values) + '</ul></div>'
    snapshot = data["snapshot"]
    status = {"complete": t("지정 범위 확인", "Scoped analysis"), "partial": t("일부 미확인", "Partial analysis"), "insufficient": t("근거 부족", "Insufficient evidence")}[data["analysis"]["status"]]
    provenance = data["provenance"]["description"] + ('' if data["provenance"]["humanReviewed"] else t(" · 사람 검토 전", " · Pending human review"))
    main = '<section class="primer-intro"><p class="eyebrow">03 / ' + t("규칙과 이유", "RULES & REASONS") + ' <span class="pill">' + status + '</span></p>'
    main += '<h1>' + escaped(data["summary"]["title"]) + '</h1><p class="primer-purpose">' + escaped(data["summary"]["purpose"]) + '</p><p class="provenance">' + escaped(provenance) + '</p><nav class="links" aria-label="' + t("관련 설명", "Related explanations") + '">' + ''.join(links) + '</nav></section>'
    main += '<nav class="primer-contents" aria-label="' + t("설명 목차", "Explanation contents") + '">' + ''.join(contents) + '</nav>' + ''.join(figures)
    if notices:
        main += '<details class="primer-notices" open><summary>' + t("확인할 점", "Things to check") + '</summary><ul>' + notices + '</ul></details>'
    main += '<details class="primer-scope"><summary>' + t("설명 범위와 한계", "Scope and limitations") + '</summary><div class="scope-body-grid">' + scope + '</div></details>'
    font = base64.b64encode((s2s.SKILL / "templates/vendor/NotoSansKR.woff2").read_bytes()).decode('ascii')
    font_css = '@font-face{font-family:S2S;src:url(data:font/woff2;base64,' + font + ') format("woff2");font-weight:400 700;font-display:swap}'
    replacements = {
        '__S2S_LANGUAGE__': escaped(data["language"]), '__S2S_TITLE__': escaped(data["summary"]["title"]),
        '__S2S_MAIN__': main, '__S2S_DATA__': encoded(data), '__S2S_LAYOUT__': encoded(layout),
        '__S2S_SNAPSHOT__': escaped(snapshot["repository"] + ' · ' + (snapshot["commit"] or '')[:8] + ' · ' + snapshot["generatedAt"]),
        '__S2S_STYLE__': font_css + (s2s.SKILL / "templates/viewer.css").read_text() + (SKILL / "templates/rules.css").read_text(),
        '__S2S_SCRIPT__': (SKILL / "templates/rules.js").read_text(),
        '__S2S_LICENSE__': escaped((s2s.SKILL / "templates/vendor/NotoSansKR.LICENSE").read_text()),
        '__S2S_SKIP__': t("설명으로 바로 이동", "Skip to explanation"),
    }
    content = re.sub('|'.join(map(re.escape, replacements)), lambda m: replacements[m.group()],
                     (SKILL / "templates/rules-template.html").read_text())
    return content, omitted


def write_outputs(outputs):
    staged = []
    try:
        for path, text in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix='.s2s-', delete=False) as stream:
                staged.append((Path(stream.name), path))
                stream.write(text)
        for temporary, destination in staged:
            temporary.replace(destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def build_pair(behavior, logic, layout, source_root, behavior_output, output, data_output=None, code_flow_root=None):
    s2s, author = companion(code_flow_root)
    validate_shared(behavior, logic, s2s)
    validate_layout(layout, logic, s2s)
    illustrated = {r for section in layout["sections"] for r in section["ruleIds"]}
    added = {r["id"] for r in logic["rules"]} - {r["id"] for r in behavior["rules"]}
    if not added <= illustrated:
        raise ValueError("Every new rule must appear in the explanation.")
    behavior_output, output = Path(behavior_output).resolve(), Path(output).resolve()
    destinations = [behavior_output, output] + ([Path(data_output).resolve()] if data_output else [])
    if len(destinations) != len(set(destinations)):
        raise ValueError("Pair HTML and render JSON need different output paths.")
    base, detail = copy.deepcopy(behavior), copy.deepcopy(logic)
    for source, target, destination, kind in ((base, output, behavior_output, "logic"), (detail, behavior_output, output, "behavior")):
        source["links"].pop(source["layer"], None)
        source["links"][kind] = {"url": quote(Path(os.path.relpath(target, destination.parent)).as_posix(), safe='/'), "generated": False,
                                 "command": "$code-flow " + source["subject"]["question"] + (" --explain" if kind == "logic" else '')}
    # Resolve the pair against the newly prepared pages, never stale prior HTML.
    initial = {behavior_output: author.prepare_build(base, source_root, behavior_output),
               output: author.prepare_build(detail, source_root, output)}
    prepared_base = author.prepare_build(base, source_root, behavior_output, linked_pages=initial)
    prepared_detail = author.prepare_build(detail, source_root, output, linked_pages=initial)
    page, omitted = render_rules(prepared_detail, layout, s2s, original=logic)
    outputs = {behavior_output: s2s.render(prepared_base), output: page}
    if data_output:
        outputs[Path(data_output).resolve()] = json.dumps(prepared_detail, ensure_ascii=False, indent=2) + '\n'
    write_outputs(outputs)
    return {"behavior": prepared_base, "logic": prepared_detail, "omittedSections": omitted}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    build = commands.add_parser('build-pair')
    for name in ('behavior-input', 'input', 'layout', 'source-root', 'behavior-output', 'output'):
        build.add_argument('--' + name, type=Path, required=True)
    build.add_argument('--data-output', type=Path)
    build.add_argument('--code-flow-root', type=Path)
    args = parser.parse_args(argv)
    try:
        inputs = {p.resolve() for p in (args.behavior_input, args.input, args.layout)}
        outputs = {p.resolve() for p in (args.behavior_output, args.output, args.data_output) if p}
        if inputs & outputs:
            raise ValueError("Keep internal evidence and layout inputs separate from output files.")
        read = lambda path: json.loads(path.read_text(encoding='utf-8'))
        result = build_pair(read(args.behavior_input), read(args.input), read(args.layout), args.source_root,
                            args.behavior_output, args.output, args.data_output, args.code_flow_root)
        print(f"{args.output}: {len(result['logic']['rules'])} rules; {len(result['omittedSections'])} withheld figures; {result['logic']['analysis']['status']}")
    except (OSError, ValueError, ValidationError) as error:
        parser.exit(1, f"rules: {error}\n")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build a source-backed rules explainer and its matching behavior page."""
from __future__ import annotations

import argparse
import base64
import copy
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote

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
    authored = isinstance(layout, dict) and layout.get("version") == 2
    name = "authored-layout.schema.json" if authored else "rule-layout.schema.json"
    schema = json.loads((SKILL / "references" / name).read_text(encoding="utf-8"))
    s2s.validate_schema(layout, schema, "layout", formats=False)
    ids = [s["id"] for s in layout["sections"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Figure IDs must be unique.")
    rules = {r["id"]: r for r in graph["rules"]}
    transitions = {s["id"]: s for s in graph["stateTransitions"]}
    claims = {c["id"]: c for c in s2s.claims(graph)}
    authored_ids = set()
    for section in layout["sections"]:
        if not set(section["ruleIds"]) <= set(rules) or not set(section.get("transitionIds", [])) <= set(transitions):
            raise ValueError("A figure references an unknown rule or state transition.")
        if any(not rules[r].get("rationale", "").strip() for r in section["ruleIds"]):
            raise ValueError("Each illustrated rule needs a reviewed rationale.")
        owners = {n for r in section["ruleIds"] for n in rules[r]["nodeIds"]}
        if any(transitions[s]["subjectNodeId"] not in owners for s in section.get("transitionIds", [])):
            raise ValueError("State figures must concern the selected rules' nodes.")
        if authored:
            if not set(section.get("claimIds", [])) <= set(claims):
                raise ValueError("An authored scene references an unknown claim.")
            scene_ids = validate_scene(section, graph, s2s)
            if authored_ids & scene_ids:
                raise ValueError("Authored DOM IDs must also be unique across scenes.")
            authored_ids.update(scene_ids)
    if not authored:
        s2s.ensure_no_source_bodies(layout, [e.get("anchorText", "") for e in graph["evidence"]])


class SceneHTML(HTMLParser):
    """Check fragment boundaries, namespaced IDs and offline asset references.

    This is an authoring guard, not a sandbox for untrusted HTML/JavaScript.
    """
    forbidden = {"html", "head", "body", "base", "meta", "link", "script", "style",
                 "iframe", "frame", "frameset", "object", "embed", "form", "template", "plaintext"}
    void = {"area", "br", "col", "hr", "img", "input", "source", "track", "wbr"}
    foreign_breakout = {"b", "big", "blockquote", "body", "br", "center", "code", "dd", "div", "dl", "dt",
                        "em", "embed", "h1", "h2", "h3", "h4", "h5", "h6", "head", "hr", "i", "img", "li",
                        "listing", "menu", "meta", "nobr", "ol", "p", "pre", "ruby", "s", "small", "span",
                        "strong", "strike", "sub", "sup", "table", "tt", "u", "ul", "var"}

    def __init__(self, identifier):
        super().__init__(convert_charrefs=True)
        self.prefix = "scene-" + identifier + "-"
        self.ids, self.references, self.stack, self.text = set(), [], [], []

    def element_namespace(self, tag, attrs):
        namespace = "html"
        if self.stack:
            parent, namespace, parent_attrs = self.stack[-1]
            # Foreign-content integration points parse their children as HTML.
            if namespace == "svg" and parent in ("foreignobject", "desc", "title"):
                namespace = "html"
            elif namespace == "math":
                if parent in ("mi", "mo", "mn", "ms", "mtext") and tag not in ("mglyph", "malignmark"):
                    namespace = "html"
                elif parent == "annotation-xml":
                    if (parent_attrs.get("encoding") or "").lower() in ("text/html", "application/xhtml+xml"):
                        namespace = "html"
                    elif tag == "svg":
                        return "svg"
        if namespace == "html":
            return tag if tag in ("svg", "math") else "html"
        if tag in self.foreign_breakout or (tag == "font" and {"color", "face", "size"} & attrs.keys()):
            # Browsers implicitly pop the foreign ancestors here, which violates
            # the explicit nesting contract even if HTMLParser sees balanced tags.
            raise ValueError("Put HTML inside an SVG/MathML integration point, not directly in foreign content.")
        return namespace

    def set_cdata_mode(self, elem, **options):
        # HTMLParser is namespace-blind (including title/textarea on Python 3.14+).
        # SVG titles must still parse child tags through the integration rules.
        if self.stack and self.stack[-1][1] == "html":
            super().set_cdata_mode(elem, **options)

    def handle_starttag(self, tag, attrs):
        if tag in self.forbidden:
            raise ValueError(f"Authored scenes cannot contain <{tag}>; use the fragment/css/script fields.")
        namespace = self.element_namespace(tag, dict(attrs))
        seen = set()
        for key, value in attrs:
            if key in seen:
                raise ValueError("An authored element has duplicate attributes.")
            seen.add(key)
            value = value or ""
            if key.startswith("on") or key in ("srcdoc", "style", "srcset"):
                raise ValueError("Use scoped CSS and the scene script, not inline handlers/styles or srcset.")
            if key == "id":
                if not value.startswith(self.prefix) or value in self.ids or re.search(r"\s", value):
                    raise ValueError(f"Scene IDs must be unique and start with {self.prefix}")
                self.ids.add(value)
            if key in ("href", "xlink:href", "src", "poster", "action", "formaction"):
                if value.startswith("#"):
                    self.references.append(value[1:])
                elif not re.fullmatch(r"data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+", value):
                    raise ValueError("Scene resources must be inline SVG, fragment links or embedded bitmap data.")
            if key in ("aria-labelledby", "aria-describedby", "aria-controls", "for"):
                self.references.extend(value.split())
            for url in re.findall(r"url\((.*?)\)", value, re.I):
                reference = url.strip().strip("'\"")
                if not reference.startswith("#"):
                    raise ValueError("SVG paint resources must reference this scene's inline definitions.")
                self.references.append(reference[1:])
            self.text.append(value)
        if namespace != "html" or tag not in self.void:
            self.stack.append((tag, namespace, dict(attrs)))
        return namespace

    def handle_startendtag(self, tag, attrs):
        namespace = self.handle_starttag(tag, attrs)
        if namespace == "html" and tag not in self.void:
            raise ValueError(f"HTML <{tag}> is not void; use an explicit </{tag}> closing tag instead of />.")
        if namespace != "html":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop()[0] != tag:
            raise ValueError("Scene HTML must have balanced, explicitly closed elements.")

    def handle_data(self, data):
        self.text.append(data)

    def handle_comment(self, data):
        self.text.append(data)

    def handle_decl(self, decl):
        raise ValueError("Supply an HTML fragment, not a full document.")


def validate_scene(section, graph, s2s):
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,95}", section["id"]):
        raise ValueError("Invalid authored scene ID.")
    parser = SceneHTML(section["id"])
    parser.feed(section["html"])
    # close() can flush an unfinished comment/tag as text. In a browser that
    # token would instead consume the shell appended after the scene fragment.
    if "<" in parser.rawdata:
        raise ValueError("Scene HTML has incomplete markup; finish comments/tags and escape literal < as &lt;.")
    parser.close()
    if parser.stack or set(parser.references) - parser.ids:
        raise ValueError("Scene HTML has unclosed elements or unresolved local references.")
    css, script = section.get("css", ""), section.get("script", "")
    if re.search(r"</(?:style|script)\b", css + "\n" + script, re.I) or re.search(r"<!--|<script\b", script, re.I):
        raise ValueError("Scene assets cannot close their containing style/script element.")
    css_urls = [url.strip().strip("'\"") for url in re.findall(r"url\((.*?)\)", css, re.I | re.S)]
    if re.search(r"@import\b", css, re.I) or any(not url.startswith("#") for url in css_urls):
        raise ValueError("Scene CSS must be offline; use the bundled font and inline SVG/bitmap HTML.")
    if any(url[1:] not in parser.ids for url in css_urls):
        raise ValueError("Scene CSS references an unknown inline definition.")
    anchors = [e.get("anchorText", "") for e in graph["evidence"]]
    # Newly authored UI code is allowed; copied target code is not. Text/attributes
    # are decoded before checking so HTML entities cannot conceal an anchor.
    s2s.ensure_no_source_bodies([section["title"], *parser.text], anchors)
    for value in (section["html"], css, script):
        if any(len(a.strip()) >= 12 and a in html.unescape(value) for a in anchors):
            raise ValueError("An evidence anchor was copied into an authored scene asset.")
    return parser.ids


def scene_dependencies(section, graph, s2s):
    """Include transitive owners/targets so a verified arrow cannot outlive a node."""
    claims = {c["id"]: c for c in s2s.claims(graph)}
    action_owners = {a["id"]: n["id"] for n in graph["nodes"] for a in n["actions"]}
    pending = list(section["ruleIds"]) + section.get("claimIds", [])
    dependencies = set()
    while pending:
        identifier = pending.pop()
        if identifier in dependencies:
            continue
        dependencies.add(identifier)
        claim = claims[identifier]
        if identifier in action_owners:
            pending.append(action_owners[identifier])
        pending.extend(claim.get("nodeIds", []))
        pending.extend(claim[key] for key in ("from", "to", "subjectNodeId", "edgeId", "nodeId")
                       if key in claim and (key not in ("from", "to") or "type" in claim))
    return dependencies


def scene_supported(section, data, original, s2s):
    claims = {c["id"]: c for c in s2s.claims(data)}
    return all(identifier in claims and claims[identifier]["displayStatus"] in ("confirmed", "context")
               for identifier in scene_dependencies(section, original, s2s))


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

    authored = layout["version"] == 2
    figures, contents, omitted, public_sections = [], [], [], []
    for section in layout["sections"]:
        identifier = 'figure-' + section["id"]
        withheld = (not set(section["ruleIds"]) <= set(rules) or
                    not set(section.get("transitionIds", [])) <= set(states) or
                    (authored and not scene_supported(section, data, original or data, s2s)))
        title = escaped(t("검토가 필요한 그림", "Scene pending review") if authored and withheld else section["title"])
        contents.append(f'<a href="#{identifier}">{title}</a>')
        heading = f'<h2 id="{identifier}-title">{title}</h2>'
        # Never embed authored assets (including withheld claims in JS/CSS) as
        # metadata. Regeneration starts from the private layout and current source.
        public_sections.append({"id": section["id"], "kind": section["kind"], "withheld": withheld})
        if withheld:
            omitted.append(section["id"])
            figures.append(f'<section class="rule-figure withheld" id="{identifier}">{heading}<p>' +
                           t("검증 자료가 부족해 이 그림을 생략했습니다. 아래 확인할 점을 살펴보세요.",
                             "This figure was withheld because its supporting claims could not be verified. See the notices below.") + '</p></section>')
            continue
        chosen = [rules[r] for r in section["ruleIds"]]
        body = ''
        if authored:
            body = '<div class="authored-picture">' + section["html"] + '</div>'
            body += '<details class="authored-evidence"><summary>' + t("조건·이유·예외와 코드 근거", "Conditions, reasons, exceptions and code evidence") + '</summary>'
            body += ''.join(case(rule, identifier + '-case-' + str(i)) for i, rule in enumerate(chosen))
            for claim_id in sorted(scene_dependencies(section, original or data, s2s) - {r["id"] for r in chosen}):
                claim = next(c for c in s2s.claims(data) if c["id"] == claim_id)
                if not claim.get("contextOnly"):
                    body += '<div class="scene-claim">' + badge(claim) + '<p>' + escaped(claim.get("plainText", claim.get("caption", claim.get("summary", claim.get("label", claim_id))))) + '</p>' + locations(claim) + '</div>'
            body += '</details>'
            if section.get("css"):
                body += '<style>' + section["css"] + '</style>'
            if section.get("script"):
                body += '<script>\n((root) => {\n' + section["script"] + '\n})(document.currentScript.closest(".authored-figure"));\n</script>'
            figures.append(f'<section class="rule-figure authored-figure" data-kind="authored" id="{identifier}" aria-labelledby="{identifier}-title">{heading}{body}</section>')
            continue
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
        label = {"behavior": t("← 기능의 처리 과정으로 돌아가기", "← Back to the capability process"),
                 "atlas": t("← 프로젝트 지도로 돌아가기", "← Back to the project map"), "logic": t("규칙과 이유", "Rules and reasons")}[kind]
        if link["generated"]:
            links.append(f'<a data-layer="{kind}" href="{escaped(link["url"])}">{label}</a>')
        else:
            links.append(f'<button type="button" class="copy-command" data-command="{escaped(link["command"])}">{label} · {t("생성 명령 복사", "copy generation command")}</button>')
    notices = ''.join('<li>' + escaped(w["message"]) + '</li>' for w in data["warnings"])
    scope = ''
    scope_seen = set()
    for title, values in ((t("포함한 범위", "Included"), data["subject"]["scope"]["includes"]),
                          (t("제외한 범위", "Excluded"), data["subject"]["scope"]["excludes"]),
                          (t("확인하지 못한 내용", "Unresolved"), data["analysis"]["unresolved"]),
                          (t("한계", "Limitations"), data["summary"]["limitations"]),
                          (t("탐색한 위치", "Searched"), data["analysis"]["searched"]),
                          (t("다음 시도", "Next attempts"), data["analysis"]["nextAttempts"])):
        values = [value for value in values if value not in scope_seen]
        if values:
            scope_seen.update(values)
            scope += '<div><h3>' + title + '</h3><ul>' + ''.join('<li>' + escaped(v) + '</li>' for v in values) + '</ul></div>'
    snapshot = data["snapshot"]
    status = {"complete": t("지정 범위 확인", "Scoped analysis"), "partial": t("일부 미확인", "Partial analysis"), "insufficient": t("근거 부족", "Insufficient evidence")}[data["analysis"]["status"]]
    provenance = data["provenance"]["description"] + ('' if data["provenance"]["humanReviewed"] else t(" · 사람 검토 전", " · Pending human review"))
    main = '<section class="primer-intro"><p class="eyebrow">03 / ' + t("규칙과 이유", "RULES & REASONS") + ' <span class="pill">' + status + '</span></p>'
    stages = ([t("프로젝트", "Project"), t("기능", "Capability")] if data["links"].get("atlas", {}).get("generated") else []) + [t("처리 과정", "Process"), t("조건·결과 그림", "Condition & result pictures")]
    journey = '<ol class="reading-path" aria-label="' + t("설명 탐색 단계", "Explanation reading stages") + '">' + ''.join('<li' + (' aria-current="step"' if i == len(stages) - 1 else '') + '>' + label + '</li>' for i, label in enumerate(stages)) + '</ol>'
    main += '<h1>' + escaped(data["summary"]["title"]) + '</h1><p class="primer-purpose">' + escaped(data["summary"]["purpose"]) + '</p>' + journey + '<details class="review-details"><summary>' + t("분석 기준과 확인 범위", "Analysis source and review scope") + '</summary><p class="provenance">' + escaped(provenance) + '</p></details><nav class="links" aria-label="' + t("관련 설명", "Related explanations") + '">' + ''.join(links) + '</nav></section>'
    if not authored or len(layout["sections"]) > 1:
        main += '<nav class="primer-contents" aria-label="' + t("설명 목차", "Explanation contents") + '">' + ''.join(contents) + '</nav>'
    main += ''.join(figures)
    if notices:
        main += '<details class="primer-notices" open><summary>' + t("확인할 점", "Things to check") + '</summary><ul>' + notices + '</ul></details>'
    main += '<details class="primer-scope"><summary>' + t("설명 범위와 한계", "Scope and limitations") + '</summary><div class="scope-body-grid">' + scope + '</div></details>'
    font = base64.b64encode((s2s.SKILL / "templates/vendor/NotoSansKR.woff2").read_bytes()).decode('ascii')
    font_css = '@font-face{font-family:S2S;src:url(data:font/woff2;base64,' + font + ') format("woff2");font-weight:400 700;font-display:swap}'
    replacements = {
        '__S2S_LANGUAGE__': escaped(data["language"]), '__S2S_TITLE__': escaped(data["summary"]["title"]),
        '__S2S_MAIN__': main, '__S2S_DATA__': encoded(data),
        '__S2S_LAYOUT__': encoded({"version": 2, "sections": public_sections} if authored else layout),
        '__S2S_BODY_CLASS__': 'primer primer-story' if authored else 'primer',
        '__S2S_CSP__': ('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; font-src data:; connect-src \'none\'; base-uri \'none\'; form-action \'none\'">' if authored else ''),
        '__S2S_SNAPSHOT__': escaped(snapshot["repository"] + ' · ' + (snapshot["commit"] or '')[:8] + ' · ' + snapshot["generatedAt"]),
        '__S2S_STYLE__': (font_css + (s2s.SKILL / "templates/viewer.css").read_text(encoding="utf-8")
                          + (SKILL / "templates/rules.css").read_text(encoding="utf-8")),
        '__S2S_SCRIPT__': (SKILL / "templates/rules.js").read_text(encoding="utf-8"),
        '__S2S_LICENSE__': escaped((s2s.SKILL / "templates/vendor/NotoSansKR.LICENSE").read_text(encoding="utf-8")),
        '__S2S_SKIP__': t("설명으로 바로 이동", "Skip to explanation"),
    }
    content = re.sub('|'.join(map(re.escape, replacements)), lambda m: replacements[m.group()],
                     (SKILL / "templates/rules-template.html").read_text(encoding="utf-8"))
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
    except (OSError, ValueError) as error:
        parser.exit(1, f"rules: {error}\n")


if __name__ == '__main__':
    main()

"""Synthetic cancellation policy for authored-story regression and visual QA.

Not a production business policy or a source-discovery evaluation.
"""
from copy import deepcopy

from validation_cases import atlas_graph, graph

SOURCE = 'def check(shipped):\n    if shipped:\n        return "manual_review"\n    return "cancelled"\n'


def story_case(language="en"):
    t = lambda ko, en: ko if language == "ko" else en
    behavior = graph()
    behavior["language"] = behavior["regeneration"]["language"] = language
    behavior["provenance"]["description"] = t("합성 주문 취소 데모 · 실제 프로젝트 정책 아님", "Synthetic cancellation demo · not a production policy")
    behavior["subject"].update({"title": t("주문 취소", "Order cancellation"),
                                "question": t("출고 상태에 따라 취소 경로가 어떻게 달라지나요?", "How does shipment change the cancellation path?")})
    behavior["subject"]["scope"] = {"includes": [t("출고 상태별 취소 결과", "Cancellation outcomes by shipment state")], "excludes": [t("결제·환불·외부 배송 시스템", "Payments, refunds and external shipping systems")]}
    behavior["summary"].update({"title": behavior["subject"]["title"], "purpose": behavior["subject"]["question"],
                                "inputs": [t("출고 여부", "Shipment state")], "outputs": ["cancelled", "manual_review"]})
    behavior["regeneration"]["question"] = behavior["subject"]["question"]
    behavior["nodes"][0].update({"label": "check", "roleLabel": t("취소 판단", "Cancellation gate"), "summary": t("출고 여부로 처리 경로를 고릅니다.", "Chooses an outcome from shipment state.")})
    behavior["nodes"][0]["actions"][0]["plainText"] = t("출고 여부를 확인합니다.", "Check whether the order has shipped.")
    behavior["nodes"][1].update({"label": t("요청자", "Caller"), "roleLabel": t("취소 요청", "Request cancellation"), "summary": t("주문의 출고 상태를 전달합니다.", "Supplies the order's shipment state.")})
    behavior["edges"][0]["label"] = t("취소 판단 요청", "Request cancellation decision")
    behavior["scenarios"][0]["title"] = t("출고 전 취소", "Cancel before shipment")
    behavior["scenarios"][0]["steps"][0].update({"caption": t("출고 상태로 취소 경로를 결정합니다.", "Choose the cancellation path from shipment state."), "condition": t("취소 요청이 들어옵니다.", "Cancellation is requested.")})
    behavior["stateTransitions"][0].update({"from": "Pending", "to": "Cancelled", "trigger": t("아직 출고되지 않았습니다.", "The order has not shipped."), "plainText": t("출고 전 주문은 취소됩니다.", "An unshipped order is cancelled.")})
    first = behavior["rules"][0]
    first.update({"condition": t("출고 전", "Not shipped"), "outcome": t("취소 완료", "Cancelled"),
                  "plainText": t("출고 전이면 취소 결과를 반환합니다.", "An unshipped order returns cancelled."),
                  "rationale": t("출고 여부 검사에 걸리지 않아 취소 반환 경로에 도달합니다.", "The shipment guard does not match, so the cancellation return is reached.")})
    second = deepcopy(first)
    second.update({"id": "rule-shipped", "condition": t("이미 출고됨", "Already shipped"), "outcome": t("별도 검토", "Manual review"),
                   "plainText": t("출고된 주문은 검토 필요 결과를 반환합니다.", "A shipped order returns manual_review."),
                   "rationale": t("출고 여부 검사가 먼저 검토 경로를 반환하여 자동 취소에 도달하지 않습니다.", "The shipment guard returns the review outcome before automatic cancellation.")})
    behavior["rules"].append(second)
    behavior["regions"][0].update({"label": t("주문 처리", "Order handling"), "summary": t("취소 경로를 판단합니다.", "Decides the cancellation path.")})
    behavior["subjects"] = []
    behavior["evidence"][0].update({"anchorText": "def check(shipped):", "endLine": 4})
    behavior["warnings"] = []
    behavior["sources"] = []
    logic = deepcopy(behavior)
    logic["layer"] = "logic"
    logic["links"] = {}
    atlas = deepcopy(behavior)
    atlas["layer"] = "atlas"
    atlas["subject"] = deepcopy(atlas_graph()["subject"])
    atlas["subject"].update({"id": "project-orders", "title": t("주문 서비스 지도", "Order service map")})
    atlas["summary"]["title"] = atlas["subject"]["title"]
    atlas["regeneration"]["subjectId"] = "project-orders"
    atlas["links"] = {}
    entry = deepcopy(atlas_graph()["subjects"][0])
    entry.update(deepcopy(behavior["subject"]))
    entry.pop("title")
    entry.update({"label": behavior["subject"]["title"], "summary": behavior["summary"]["purpose"],
                  "link": {"url": "behavior.html", "generated": False, "command": "$code-flow " + behavior["subject"]["question"]}})
    atlas["subjects"] = [entry]
    atlas["structureEntries"] = [
        {"id": "structure-root", "path": ".", "kind": "directory",
         "label": t("예제 소스", "Example source"),
         "summary": t("취소 판단을 담은 작은 합성 예제입니다.", "A small synthetic cancellation example."),
         "nodeIds": ["node-main"],
         **{key: deepcopy(entry[key]) for key in ("confidence", "supportStatus", "verificationNote", "evidenceIds")}},
        {"id": "structure-check", "path": "example.py", "kind": "file",
         "label": t("취소 판단", "Cancellation decision"),
         "summary": t("출고 상태에 따라 취소 결과를 고릅니다.", "Chooses a cancellation outcome from shipment state."),
         "nodeIds": ["node-main"],
         **{key: deepcopy(entry[key]) for key in ("confidence", "supportStatus", "verificationNote", "evidenceIds")}},
    ]
    markup = '''<div class="lesson-hero">
<div class="lesson-copy"><p class="lesson-kicker">CANCELLATION / SHIPMENT GATE</p>
<h3>__HEADLINE__</h3><p>__PURPOSE__</p><p class="lesson-limit">__LIMIT__</p></div>
<div class="lesson-visual"><svg viewBox="0 0 560 470" role="img" aria-labelledby="scene-cancellation-diagram-title scene-cancellation-diagram-desc">
<title id="scene-cancellation-diagram-title">__TITLE__</title><desc id="scene-cancellation-diagram-desc">__DESC__</desc>
<defs><marker id="scene-cancellation-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>
<rect class="actor" x="180" y="24" width="200" height="76" rx="20"/><text x="280" y="70">__REQUEST__</text>
<path class="request-route" d="M280 100 L280 172" marker-end="url(#scene-cancellation-arrow)"/>
<rect class="gate" x="160" y="176" width="240" height="82" rx="24"/><text x="280" y="224">__GATE__</text>
<path class="result-route allow" data-route="before" d="M220 258 C220 296 128 294 128 360" marker-end="url(#scene-cancellation-arrow)"/>
<path class="result-route review" data-route="after" d="M340 258 C340 296 432 294 432 360" marker-end="url(#scene-cancellation-arrow)"/>
<text class="branch-label" x="111" y="301">__NO__</text><text class="branch-label" x="451" y="301">__YES__</text>
<rect class="allow-box" x="22" y="365" width="212" height="76" rx="20"/><text x="128" y="412">__CANCELLED__</text>
<rect class="review-box" x="326" y="365" width="212" height="76" rx="20"/><text x="432" y="412">__REVIEW__</text></svg>
<div class="lesson-controls" role="group" aria-label="__CHOOSE__"><button type="button" data-choice="before" aria-pressed="false" aria-controls="scene-cancellation-result">__BEFORE__</button><button type="button" data-choice="after" aria-pressed="false" aria-controls="scene-cancellation-result">__AFTER__</button><button type="button" data-reset="true">__RESET__</button></div>
<p id="scene-cancellation-result" class="lesson-result" role="status" aria-live="polite">__STATIC__</p></div></div>'''
    texts = {
        "HEADLINE": t("취소는 같아도,<br>출고 상태가<br><em>결과를 바꾼다.</em>", "Same request.<br>Shipment changes<br><em>the outcome.</em>"),
        "PURPOSE": t("취소 요청이 오면 먼저 출고 여부를 봅니다. 출고 전이면 취소하고, 출고 후이면 별도 검토 경로로 보냅니다.", "A cancellation request first checks shipment. Before shipping, it cancels; after shipping, it takes the review path."),
        "LIMIT": t("이 그림은 합성 예제입니다. 결제·환불 동작이나 실제 서비스 정책을 뜻하지 않습니다.", "Synthetic example. This does not describe payments, refunds or a real service policy."),
        "TITLE": t("출고 상태에 따른 취소 분기", "Cancellation branches by shipment state"),
        "DESC": t("취소 요청에서 출고 여부를 확인합니다. 출고 전은 취소 완료, 출고 후는 별도 검토로 이어집니다.", "A cancellation request checks shipment. Not shipped leads to cancelled; already shipped leads to manual review."),
        "REQUEST": t("취소 요청", "Cancel request"), "GATE": t("출고되었나요?", "Shipped yet?"),
        "NO": t("아니요", "No"), "YES": t("예", "Yes"),
        "BEFORE": first["condition"], "AFTER": second["condition"], "CANCELLED": first["outcome"], "REVIEW": second["outcome"],
        "CHOOSE": t("출고 상태 선택", "Choose shipment state"), "RESET": t("전체 경로", "Show both"),
        "STATIC": t("출고 전 → 취소 완료 · 출고 후 → 별도 검토", "Not shipped → Cancelled · Already shipped → Manual review")}
    for key, value in texts.items():
        markup = markup.replace("__" + key + "__", value)
    css = '''#figure-cancellation .lesson-hero{display:grid;grid-template-columns:1.05fr 1.15fr;gap:32px;align-items:center;padding:10px 0}
#figure-cancellation .lesson-kicker{font-size:11px;letter-spacing:1.4px;color:var(--teal)}
#figure-cancellation .lesson-copy h3{font-size:clamp(34px,3.5vw,50px);line-height:1.22;letter-spacing:-1.8px;margin:20px 0;word-break:keep-all}
#figure-cancellation .lesson-copy em{font-style:normal;color:var(--teal)}
#figure-cancellation .lesson-copy p{line-height:1.8}#figure-cancellation .lesson-limit{font-size:12px;color:var(--muted)}
#figure-cancellation .lesson-visual{border:1px solid var(--line);background:var(--surface);border-radius:28px;padding:18px}
#figure-cancellation svg text{font:600 24px S2S,sans-serif;text-anchor:middle;fill:var(--ink)}
#figure-cancellation svg .branch-label{font-size:21px;fill:var(--muted)}
#figure-cancellation .actor{fill:var(--paper);stroke:var(--line);stroke-width:2}#figure-cancellation .gate{fill:var(--soft);stroke:var(--teal);stroke-width:2}
#figure-cancellation .allow-box{fill:var(--soft);stroke:var(--teal);stroke-width:2}#figure-cancellation .review-box{fill:var(--paper);stroke:#b06c31;stroke-width:2}
#figure-cancellation .request-route{fill:none;stroke:var(--muted);stroke-width:3}#figure-cancellation .result-route{fill:none;stroke-width:4;transition:opacity .2s}
#figure-cancellation .allow{stroke:var(--teal)}#figure-cancellation .review{stroke:#b06c31;stroke-dasharray:7 5}
#figure-cancellation [data-route].inactive{opacity:.18}#figure-cancellation [data-route].active{stroke-width:6}
#figure-cancellation .lesson-controls{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 12px}
#figure-cancellation button{font:inherit;font-size:13px;padding:10px 14px;border:1px solid var(--line);border-radius:12px;background:var(--paper);color:var(--ink);cursor:pointer}
#figure-cancellation button[aria-pressed=true]{background:var(--soft);border-color:var(--teal)}#figure-cancellation .lesson-result{font-size:14px;min-height:48px;color:var(--teal)}
@media(max-width:760px){#figure-cancellation .lesson-hero{grid-template-columns:1fr;padding-top:0;gap:20px}#figure-cancellation .lesson-copy h3{font-size:38px}#figure-cancellation .lesson-visual{padding:10px}#figure-cancellation .lesson-copy{max-width:540px}}'''
    # The UI selects already reviewed outcomes; it does not reproduce target code.
    script = '''const result = root.querySelector('.lesson-result');
const original = result.textContent;
const buttons = [...root.querySelectorAll('[data-choice]')];
const outcomes = [...root.querySelectorAll('svg text')].slice(-2).map(node => node.textContent);
const show = (choice) => {
  buttons.forEach((button, index) => {
    const active = button.dataset.choice === choice;
    button.setAttribute('aria-pressed', String(active));
    if(active) result.textContent = button.textContent + ' → ' + outcomes[index];
  });
  root.querySelectorAll('[data-route]').forEach(path => {
    path.classList.toggle('active', path.dataset.route === choice);
    path.classList.toggle('inactive', Boolean(choice) && path.dataset.route !== choice);
  });
  if(!choice) result.textContent = original;
};
buttons.forEach(button => button.addEventListener('click', () => show(button.dataset.choice)));
root.querySelector('[data-reset]').addEventListener('click', () => show(null));'''
    layout = {"version": 2, "sections": [{"id": "cancellation", "title": texts["TITLE"], "kind": "authored",
                                         "ruleIds": ["rule-main", "rule-shipped"],
                                         "claimIds": ["edge-call", "step-main", "transition-main"],
                                         "html": markup, "css": css, "script": script}]}
    return atlas, behavior, logic, layout

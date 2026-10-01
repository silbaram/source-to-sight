"""Synthetic purchase flow with reviewed business operations for visual QA.

This is a presentation fixture, not a source-discovery evaluation or an example
of production payment, persistence or messaging guarantees.
"""
from copy import deepcopy

from validation_cases import graph


SOURCE = '''def receive_purchase(request):
    return request["order_id"]

def read_order(database, order_id):
    return database.find_order(order_id)

def decide_purchase(order):
    return order["available"]

def request_payment(payment_service, order):
    return payment_service.charge(order)

def save_order(database, order):
    database.save_order(order)

def publish_confirmation(queue, order):
    queue.publish(order)

def write_receipt(receipt_file, receipt):
    receipt_file.write(receipt)

def respond_purchase(order):
    return order["confirmation"]

def stop_purchase(order):
    return "unavailable"
'''


def operation_case(language="en"):
    """One graph distinguishes action from its target without inventing edges."""
    t = lambda ko, en: ko if language == "ko" else en
    data = graph()
    claim = {key: deepcopy(data["nodes"][0][key]) for key in
             ("confidence", "supportStatus", "evidenceIds", "verificationNote")}
    data["language"] = data["regeneration"]["language"] = language
    data["provenance"]["description"] = t(
        "합성 구매 처리 화면 검증 · 실제 결제 정책 아님",
        "Synthetic purchase presentation fixture; not a production payment policy.")
    data["subject"].update(
        id="purchase-demo", title=t("구매 요청 처리", "Process a purchase"),
        question=t("어떤 정보를 확인하고 어디에 요청하거나 저장하나요?",
                   "What is checked, and where are requests and records sent?"),
        targets=[{"label": t("구매 요청", "Purchase request"), "file": "operations.py"}],
        scope={"includes": [t("합성 구매 처리의 작업과 대상", "Operations and targets in a synthetic purchase")],
               "excludes": [t("실제 결제·배포·재시도 보장", "Production payments, deployment and retry guarantees")]})
    data["summary"].update(
        title=data["subject"]["title"], purpose=data["subject"]["question"],
        inputs=[t("구매할 주문", "Order to purchase")],
        outputs=[t("구매 확인 또는 품절 결과", "Purchase confirmation or unavailable result")],
        limitations=[t("화면 검증을 위한 합성 흐름입니다.", "Synthetic flow for presentation checks.")])
    data["analysis"]["searched"] = ["operations.py"]
    data["analysis"]["profiles"] = ["web"]
    data["regeneration"].update(subjectId="purchase-demo", question=data["subject"]["question"],
                                command=t("합성 구매 처리를 설명하세요.", "Explain the synthetic purchase."))
    data["nodes"], data["evidence"], data["edges"] = [], [], []
    specs = (
        ("receive", "receive", None, None, "구매 요청 받기", "Receive purchase", "구매할 주문을 받습니다.", "Receives the order to purchase."),
        ("read", "read", "database", ("주문 DB", "Orders database"), "주문 불러오기", "Load the order", "저장된 주문 정보를 확인합니다.", "Reads the stored order."),
        ("decide", "decide", None, None, "구매 가능 여부", "Purchase eligibility", "재고 상태에 따라 진행 또는 종료를 선택합니다.", "Chooses whether to proceed based on availability."),
        ("payment", "request", "api", ("결제 서비스", "Payment service"), "결제 승인 요청", "Request payment approval", "외부 결제 서비스에 승인을 요청합니다.", "Requests approval from the external payment service."),
        ("save", "write", "database", ("주문 DB", "Orders database"), "구매 결과 저장", "Save the purchase", "승인된 구매 결과를 보관합니다.", "Stores the approved purchase."),
        ("publish", "publish", "queue", ("구매 알림 대기열", "Purchase notification queue"), "구매 알림 발행", "Publish purchase notice", "구매 알림을 대기열에 보냅니다.", "Sends the purchase notice to the queue."),
        ("receipt", "write", "file", ("영수증 파일", "Receipt file"), "영수증 파일 저장", "Write the receipt", "영수증을 파일에 기록합니다.", "Writes the receipt to a file."),
        ("respond", "respond", None, None, "구매 확인 반환", "Return confirmation", "구매 확인 결과를 요청자에게 돌려줍니다.", "Returns purchase confirmation to the requester."),
        ("stop", "stop", None, None, "품절로 종료", "Stop when unavailable", "구매할 수 없으면 처리를 마칩니다.", "Ends processing when the order is unavailable."),
    )
    functions = [line.removeprefix("def ").split("(")[0] for line in SOURCE.splitlines() if line.startswith("def ")]
    for index, (slug, kind, target_kind, target, ko_label, en_label, ko_summary, en_summary) in enumerate(specs):
        evidence_id = f"ev-{slug}"
        operation = {"kind": kind}
        if target_kind:
            operation.update(targetKind=target_kind, target=t(*target))
        label = t(ko_label, en_label)
        data["nodes"].append({
            "id": f"node-{slug}", "kind": "component", "label": label,
            "roleLabel": label, "summary": t(ko_summary, en_summary),
            "importance": "core", "contextOnly": False, "actions": [],
            **deepcopy(claim), "evidenceIds": [evidence_id], "operation": operation,
            "codeName": functions[index],
        })
        data["evidence"].append({
            "id": evidence_id, "kind": "code", "file": "operations.py",
            "symbolOrKey": functions[index], "startLine": index * 3 + 1,
            "endLine": index * 3 + 2, "contentHash": None, "locationStatus": "passed",
            "anchorText": SOURCE.splitlines()[index * 3],
        })
    node_ids = [node["id"] for node in data["nodes"]]
    for index, (source, destination) in enumerate(zip(node_ids[:7], node_ids[1:8])):
        data["edges"].append({
            "id": f"edge-{index}", "from": source, "to": destination,
            "label": t("주문 정보 전달", "Pass order details"),
            "type": "passes-data", "derivation": "direct-code", **deepcopy(claim),
            "evidenceIds": [data["nodes"][index]["evidenceIds"][0]],
        })
    data["edges"].append({"id": "edge-unavailable", "from": "node-decide", "to": "node-stop",
        "label": t("품절", "Unavailable"), "type": "invokes", "derivation": "direct-code",
        **deepcopy(claim), "evidenceIds": ["ev-decide"]})
    data["scenarios"] = [{
        "id": "scenario-purchase", "title": t("구매 가능", "Available purchase"), "kind": "typical",
        "steps": [{"id": f"step-{index}", "edgeId": edge["id"],
                   "caption": data["nodes"][index + 1]["summary"], "branch": "normal",
                   "condition": t("구매할 수 있을 때", "When available") if index == 2 else
                                t("앞 처리가 끝났을 때", "When the previous operation finishes"),
                   "execution": "sequential", **deepcopy(claim),
                   "evidenceIds": deepcopy(edge["evidenceIds"])}
                  for index, edge in enumerate(data["edges"][:-1])],
    }, {
        "id": "scenario-unavailable", "title": t("품절", "Unavailable order"), "kind": "alternate",
        "steps": [{"id": "step-unavailable", "edgeId": "edge-unavailable",
                   "caption": t("품절 결과로 종료합니다.", "Stop with an unavailable result."),
                   "branch": "alternate", "condition": t("품절일 때", "When unavailable"),
                   "execution": "sequential", **deepcopy(claim), "evidenceIds": ["ev-decide"]}],
    }]
    data["regions"] = [{"id": "region-purchase", "label": t("구매 처리", "Purchase processing"),
                        "summary": data["subject"]["question"], "nodeIds": node_ids,
                        "role": "primary", **deepcopy(claim), "evidenceIds": ["ev-receive"]}]
    for key in ("stateTransitions", "rules", "subjects", "warnings", "sources"):
        data[key] = []
    data["links"] = {}
    return data

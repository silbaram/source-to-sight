"""Small synthetic inputs and mutations shared by regression and migration checks."""
from copy import deepcopy


def graph():
    claim = {"confidence": "exact", "supportStatus": "supported",
             "evidenceIds": ["ev-main"], "verificationNote": "Checked against the source."}
    return {
        "schemaVersion": "0.1.0", "layer": "behavior", "language": "en",
        "provenance": {"kind": "synthetic", "humanReviewed": False,
                       "description": "Synthetic validator regression input."},
        "snapshot": {"repository": "validation-example", "branch": None, "commit": None,
                     "workingTreeClean": None, "generatedAt": "2026-09-07T12:00:00Z",
                     "skillVersion": "0.6.0", "model": None},
        "subject": {"id": "subject-main", "kind": "capability", "title": "Validate input",
                    "question": "How is an input checked?", "module": "example", "targets": [{"label": "check"}],
                    "scope": {"includes": ["Input validation"], "excludes": []}},
        "analysis": {"status": "complete", "profiles": ["cli-utility"], "searched": ["example.py"],
                     "unresolved": [], "nextAttempts": []},
        "summary": {"title": "Validate input", "purpose": "Explain a condition.",
                    "inputs": ["An input"], "outputs": ["An accepted input"], "limitations": []},
        "nodes": [
            {"id": "node-main", "kind": "component", "label": "Validator", "roleLabel": "Check input",
             "summary": "Checks the input.", "importance": "core", "contextOnly": False,
             "actions": [{"id": "action-check", "plainText": "Check the condition.", **deepcopy(claim)}], **deepcopy(claim)},
            {"id": "node-caller", "kind": "actor", "label": "Caller", "roleLabel": "Provide input",
             "summary": "Provides an input.", "importance": "detail", "contextOnly": True, "actions": []}],
        "edges": [{"id": "edge-call", "from": "node-caller", "to": "node-main", "label": "Calls validator",
                   "type": "invokes", "derivation": "direct-code", **deepcopy(claim)}],
        "scenarios": [{"id": "scenario-main", "title": "Valid input", "kind": "typical", "steps": [
            {"id": "step-main", "edgeId": "edge-call", "caption": "Check the input.",
             "branch": "normal", "condition": "An input is supplied.", "execution": "sequential", **deepcopy(claim)}]}],
        "stateTransitions": [{"id": "transition-main", "subjectNodeId": "node-main", "from": "Pending",
                              "to": "Accepted", "trigger": "The condition holds.",
                              "plainText": "Accept the input.", **deepcopy(claim)}],
        "rules": [{"id": "rule-main", "plainText": "Accept valid input.", "condition": "The input is valid.",
                   "outcome": "Accept the input.", "numeric": False, "nodeIds": ["node-main"],
                   "rationale": "Only valid input may proceed.", "exceptions": [], **deepcopy(claim)}],
        "regions": [{"id": "region-main", "label": "Validation", "summary": "Checks input.",
                     "nodeIds": ["node-main"], **deepcopy(claim)}],
        "subjects": [{"id": "subject-detail", "label": "Details", "nodeId": "node-main",
                      "link": {"url": "detail.html", "generated": False, "command": "Explain the details."}}],
        "evidence": [{"id": "ev-main", "kind": "code", "file": "example.py", "symbolOrKey": "check",
                      "startLine": 1, "endLine": 2, "contentHash": None, "locationStatus": "passed",
                      "anchorText": "def check(value):"}],
        "warnings": [{"id": "warning-main", "kind": "coverage-limited", "severity": "low",
                      "message": "Only one condition is shown.", "relatedIds": ["node-main"], "candidates": []}],
        "sources": [{"id": "source-main", "title": "Example", "version": "current",
                     "url": "https://example.org/", "retrievedAt": "2026-09-07"}],
        "links": {"logic": {"url": "rules.html", "generated": False, "command": "Explain the rule."}},
        "regeneration": {"subjectId": "subject-main", "question": "How is an input checked?",
                         "language": "en", "command": "Explain how the input is checked."}}


def layout(kind="conditions"):
    section = {"id": "figure-main", "title": "Input condition", "kind": kind, "ruleIds": ["rule-main"]}
    if kind == "comparison":
        section["ruleIds"].append("rule-other")
    if kind == "states":
        section["transitionIds"] = ["transition-main"]
    return {"version": 1, "sections": [section]}


def render_graph():
    data = graph()
    for key in ("nodes", "edges", "rules", "regions", "stateTransitions"):
        for item in data[key]:
            item["displayStatus"] = "context" if item.get("contextOnly") else "confirmed"
            for action in item.get("actions", []):
                action["displayStatus"] = "confirmed"
    data["scenarios"][0]["steps"][0]["displayStatus"] = "confirmed"
    for evidence in data["evidence"]:
        evidence.pop("anchorText")
        evidence["contentHash"] = "a" * 64
        evidence["observedContentHash"] = "a" * 64
    return data


def atlas_graph():
    data = graph()
    data["layer"] = "atlas"
    data["subject"]["kind"] = "project"
    data["subjects"][0].update({
        "summary": "Check an input.", "kind": "capability", "question": "How is input checked?",
        "module": "example", "targets": [{"label": "check", "file": "example.py", "symbol": "check"}],
        "scope": {"includes": ["Input validation"], "excludes": []},
        "confidence": "exact", "supportStatus": "supported", "evidenceIds": ["ev-main"],
        "verificationNote": "The entrypoint was read."})
    return data


def mutations(value):
    """One change at every nested location, including deletion and duplicate items."""
    def visit(item, path=()):
        yield path, item
        if isinstance(item, dict):
            for key, child in item.items():
                yield from visit(child, (*path, key))
        elif isinstance(item, list):
            for index, child in enumerate(item):
                yield from visit(child, (*path, index))

    yield "valid", deepcopy(value)
    replacements = [None, False, True, 0, 1, 1.0, 1.5, -1, "", "invalid", "value\n", [], {}]
    for location, item in visit(value):
        candidates = list(replacements)
        if isinstance(item, str):
            candidates.append(item + "\n")
        if isinstance(item, list) and item:
            candidates.append(item + [deepcopy(item[0])])
        if isinstance(item, dict):
            candidates.append({**item, "unexpected": True})
            candidates.extend({k: v for k, v in item.items() if k != name} for name in item)
        for index, replacement in enumerate(candidates):
            changed = deepcopy(value)
            if location:
                parent = changed
                for part in location[:-1]:
                    parent = parent[part]
                parent[location[-1]] = deepcopy(replacement)
            else:
                changed = deepcopy(replacement)
            yield f"/{'/'.join(map(str, location))}:{index}", changed

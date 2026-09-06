"""Generate the two stage-specific contracts from one maintained definition."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "skills/code-flow/references"
TEXT = {"type": "string", "minLength": 1}
ID = {"type": "string", "pattern": "^[a-zA-Z][a-zA-Z0-9_-]{0,95}$"}


def enum(*values):
    return {"enum": list(values)}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def build(stage):
    rendering = stage == "render"
    claim = {
        "confidence": enum("exact", "resolved", "inferred"),
        "evidenceIds": {**array(ID, 1), "uniqueItems": True},
        "supportStatus": enum("supported", "uncertain", *([] if rendering else ["unsupported"])),
        "verificationNote": TEXT,
        "sourceIds": {**array(ID), "uniqueItems": True},
    }
    claim_required = ["confidence", "evidenceIds", "supportStatus", "verificationNote"]
    if rendering:
        claim["displayStatus"] = enum("confirmed", "uncertain", "unverified")
        claim_required.append("displayStatus")

    def claimed(fields, optional=()):
        return obj({**fields, **claim},
                   [k for k in fields if k not in optional] + claim_required)

    action = claimed({"id": ID, "plainText": TEXT, "codeName": TEXT}, ("codeName",))
    node_fields = {
        "id": ID, "kind": enum("actor", "component", "state", "artifact", "boundary"),
        "label": TEXT, "roleLabel": TEXT, "summary": TEXT, "codeName": TEXT,
        "importance": enum("core", "detail"), "contextOnly": {"type": "boolean"},
        "actions": array(ref("action")), **claim,
    }
    if rendering:
        node_fields["displayStatus"] = enum("confirmed", "uncertain", "unverified", "context")
    node = obj(node_fields, ["id", "kind", "label", "roleLabel", "summary",
                            "importance", "contextOnly", "actions"])
    node["allOf"] = [{
        "if": {"properties": {"contextOnly": {"const": True}}},
        "then": {
            "not": {"anyOf": [{"required": [k]} for k in claim_required
                             if k != "displayStatus"]},
            "properties": {"actions": {"maxItems": 0},
                           **({"displayStatus": {"const": "context"}} if rendering else {})},
            **({"required": ["displayStatus"]} if rendering else {}),
        },
        "else": {"required": claim_required},
    }]
    edge = claimed({
        "id": ID, "from": ID, "to": ID, "label": TEXT,
        "type": enum("invokes", "passes-data", "depends-on", "registers", "dispatches",
                     "reads", "writes", "emits", "consumes", "transitions", "delegates"),
        "derivation": enum("direct-code", "explicit-config", "symbol-resolution",
                           "registration-rule", "framework-rule", "documentation",
                           "test-example", "pattern"),
    })
    step = claimed({
        "id": ID, "caption": TEXT, "edgeId": ID, "nodeId": ID, "returns": TEXT,
        "branch": enum("normal", "alternate", "error", "retry", "stop"),
        "condition": TEXT,
        "execution": enum("sequential", "parallel", "unordered"),
    }, ("edgeId", "nodeId", "returns", "branch", "condition", "execution"))
    step["oneOf"] = [{"required": ["edgeId"], "not": {"required": ["nodeId"]}},
                     {"required": ["nodeId"], "not": {"required": ["edgeId"]}}]
    evidence_fields = {
        "id": ID, "kind": enum("code", "config", "documentation", "test"),
        "file": TEXT, "symbolOrKey": TEXT,
        "startLine": {"type": "integer", "minimum": 1},
        "endLine": {"type": "integer", "minimum": 1},
        "contentHash": {"anyOf": [{"type": "string", "pattern": "^[a-f0-9]{64}$"},
                                 {"type": "null"}]},
        "observedContentHash": {"anyOf": [{"type": "string", "pattern": "^[a-f0-9]{64}$"},
                                         {"type": "null"}]},
        "locationStatus": enum("passed", "failed"),
        "locationNote": {"type": "string"},
    }
    if not rendering:
        evidence_fields["anchorText"] = {**TEXT, "pattern": "^[^\n\r]+$"}
    # Optional for compatibility with existing 0.1.0 pages; prepare always sets it.
    evidence = obj(evidence_fields, [k for k in evidence_fields
                                     if k not in ("locationNote", "observedContentHash")])
    warning = obj({
        "id": ID, "kind": enum("subject-ambiguous", "ambiguous-target",
            "unresolved-dispatch", "evidence-unverified", "claim-unsupported",
            "dynamic-behavior", "external-boundary", "node-budget-exceeded",
            "coverage-limited", "snapshot-mismatch"),
        "severity": enum("high", "medium", "low"), "message": TEXT,
        "relatedIds": array(ID),
        "candidates": array(obj({"label": TEXT, "file": TEXT,
                                "line": {"type": "integer", "minimum": 1}})),
    })
    link = obj({"url": TEXT, "generated": {"type": "boolean"}, "command": TEXT,
                "sourceFingerprint": TEXT}, ["url", "generated"])
    link["allOf"] = [{"if": {"properties": {"generated": {"const": False}}},
                     "then": {"required": ["command"]}}]
    definitions = {
        "action": action, "node": node, "edge": edge, "step": step,
        "evidence": evidence, "warning": warning, "link": link,
        "scenario": obj({"id": ID, "title": TEXT,
                         "kind": enum("typical", "alternate", "error", "retry", "lifecycle"),
                         "steps": array(ref("step"), 1)}),
        "transition": claimed({"id": ID, "subjectNodeId": ID, "from": TEXT,
                               "to": TEXT, "trigger": TEXT, "plainText": TEXT}),
        "rule": claimed({"id": ID, "plainText": TEXT, "condition": TEXT,
                         "outcome": TEXT, "numeric": {"type": "boolean"},
                         "nodeIds": array(ID), "rationale": TEXT,
                         "exceptions": array(TEXT)}, ("rationale", "exceptions")),
        "region": claimed({"id": ID, "label": TEXT, "summary": TEXT, "nodeIds": array(ID, 1)}),
        "target": obj({"label": TEXT, "file": TEXT, "symbol": TEXT}, ["label"]),
    }
    props = {
        "schemaVersion": {"const": "0.1.0"},
        "layer": enum("atlas", "behavior", "logic"),
        "language": {**TEXT, "pattern": "^[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*$"},
        "provenance": obj({"kind": enum("source-traced", "synthetic"),
                           "description": TEXT, "humanReviewed": {"type": "boolean"}}),
        "snapshot": obj({
            "repository": TEXT, "branch": {"type": ["string", "null"]},
            "commit": {"anyOf": [{"type": "string", "pattern": "^[a-f0-9]{40,64}$"},
                                 {"type": "null"}]},
            "workingTreeClean": {"type": ["boolean", "null"]},
            "generatedAt": {"type": "string", "format": "date-time"},
            "skillVersion": TEXT, "model": {"type": ["string", "null"]},
        }),
        "subject": obj({
            "id": ID, "kind": enum("project", "capability", "workflow", "lifecycle"),
            "title": TEXT, "question": TEXT, "module": TEXT,
            "targets": array(ref("target")),
            "scope": obj({"includes": array(TEXT, 1), "excludes": array(TEXT)}),
        }),
        "analysis": obj({
            "status": enum("complete", "partial", "insufficient"),
            "profiles": array(TEXT, 1), "searched": array(TEXT),
            "unresolved": array(TEXT), "nextAttempts": array(TEXT),
        }),
        "summary": obj({"title": TEXT, "purpose": TEXT, "inputs": array(TEXT),
                        "outputs": array(TEXT), "limitations": array(TEXT)}),
        "nodes": array(ref("node")), "edges": array(ref("edge")),
        "scenarios": array(ref("scenario")),
        "stateTransitions": array(ref("transition")), "rules": array(ref("rule")),
        "regions": array(ref("region")),
        "subjects": array(obj({"id": ID, "label": TEXT, "nodeId": ID, "link": ref("link")})),
        "evidence": array(ref("evidence")), "warnings": array(ref("warning")),
        "sources": array(obj({"id": ID, "url": TEXT, "title": TEXT,
                              "version": TEXT, "retrievedAt": TEXT})),
        "links": obj({k: ref("link") for k in ("atlas", "behavior", "logic")}, []),
        "regeneration": obj({"subjectId": ID, "question": TEXT, "language": TEXT,
                              "command": TEXT}),
    }
    schema = obj(props)
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema",
                   "$id": f"urn:source-to-sight:{stage}:0.1.0",
                   "title": f"Understanding Graph — {stage}", "$defs": definitions})
    return schema


if __name__ == "__main__":
    for stage in ("internal", "render"):
        path = OUT / f"ir-{stage}-v0.1.0.schema.json"
        path.write_text(json.dumps(build(stage), ensure_ascii=False, indent=2) + "\n")
        print(path.relative_to(ROOT))

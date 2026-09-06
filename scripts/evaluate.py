#!/usr/bin/env python3
"""Evaluate source-backed candidates; automatic checks never substitute for human review."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import author
import s2s

VERSION = 1
AXES = ("scope", "structure", "semantics", "rules", "comprehension", "genericity")
VARIANTS = ({"typical", "boundary", "minimal"}, {"typical", "boundary", "dynamic"})
VARIANTS = (*VARIANTS, *(v | {"complex"} for v in VARIANTS))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def within(root, relative):
    if not isinstance(relative, str) or not s2s.relative_path(relative):
        raise ValueError(f"Invalid relative evaluation path: {relative!r}")
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Evaluation path escapes its root: {relative}")
    return path


def load_suite(path):
    path = Path(path).resolve()
    suite = read(path)
    if suite["version"] != VERSION:
        raise ValueError("Unsupported evaluation manifest version")
    source_list = read(within(path.parent, suite["sources"]))
    sources = {s["id"]: s for s in source_list}
    if len(sources) != len(source_list):
        raise ValueError("Duplicate source IDs")
    if len({s["repository"] for s in source_list}) != len(source_list):
        raise ValueError("Sources must identify distinct repositories")
    for source in source_list:
        if not re.fullmatch(r"[a-z0-9-]+", source["id"]) or not re.fullmatch(r"[0-9a-f]{40}", source["commit"]):
            raise ValueError("Sources need safe IDs and full pinned commits")
    ids, files = set(), set()
    profiles = {}
    for case in suite["cases"]:
        identifier = case["id"]
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,95}", identifier) or identifier in ids:
            raise ValueError("Invalid or duplicate case ID")
        ids.add(identifier)
        source = sources[case["source"]]
        if case["sourceLanguage"] != source["language"]:
            raise ValueError("Case/source language mismatch")
        profiles.setdefault(case["profile"], []).append(case["variant"])
        for key in ("candidate", "expectation"):
            file = within(path.parent, case[key])
            if file in files:
                raise ValueError("Cases must not share candidate/expectation files")
            files.add(file)
        reference = read(within(path.parent, case["expectation"]))
        validate_reference(reference, identifier)
        if case["profile"] not in reference["profiles"]:
            raise ValueError("Case profile missing from reference")
    if (set(profiles) != set(author.PROFILES) or len({len(v) for v in profiles.values()}) != 1
            or any(len(v) != len(set(v)) or set(v) not in VARIANTS for v in profiles.values())):
        raise ValueError("Suite needs six profiles × typical/boundary/minimal-or-dynamic, optionally one complex case each")
    if len({c["source"] for c in suite["cases"]}) < 6 or len({c["sourceLanguage"] for c in suite["cases"]}) < 3:
        raise ValueError("Suite needs six source repositories and three languages")
    return suite, sources


def validate_reference(ref, identifier):
    if ref["version"] != VERSION or ref["caseId"] != identifier:
        raise ValueError("Reference version/case mismatch")
    keys = [n["key"] for n in ref["nodes"]]
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("Reference roles must be nonempty and unique")
    if not ref["statuses"] or not set(ref["statuses"]) <= {"complete", "partial", "insufficient"}:
        raise ValueError("Invalid expected analysis statuses")
    if type(ref["noScenarios"]) is not bool:
        raise ValueError("noScenarios must be boolean")
    for node in ref["nodes"]:
        if not s2s.relative_path(node["file"]) or type(node["line"]) is not int or node["line"] < 1:
            raise ValueError("Invalid reference location")
        if not isinstance(node["codeNames"], list) or any(not isinstance(n, str) or not n for n in node["codeNames"]):
            raise ValueError("Invalid role code names")
        if node["kind"] not in {"component", "actor", "state", "artifact", "boundary"}:
            raise ValueError("Invalid role kind")
        if node["status"] not in {"confirmed", "uncertain", "unverified"}:
            raise ValueError("Invalid role display status")
    allowed_types = s2s.schema("render")["$defs"]["edge"]["properties"]["type"]["enum"]
    for edge in ref["edges"] + ref["forbiddenEdges"]:
        if edge["fromRole"] not in keys or edge["toRole"] not in keys or edge["type"] not in allowed_types:
            raise ValueError("Invalid reference relationship")
        if edge["status"] not in {"confirmed", "uncertain", "unverified"}:
            raise ValueError("Invalid relationship display status")
    for field in ("requiredFacts", "forbiddenClaims"):
        if not ref[field] or any(not isinstance(t, str) or not t.strip() for t in ref[field]):
            raise ValueError(f"Reference needs nonempty {field}")
    behavior_keys = set()
    for item in ref.get("behaviors", []):
        if item["key"] in behavior_keys or item["role"] not in keys:
            raise ValueError("Duplicate behavior key or unknown role")
        behavior_keys.add(item["key"])
        if item["kind"] not in {"step", "rule", "transition"} or not s2s.relative_path(item["file"]) or type(item["line"]) is not int or item["line"] < 1:
            raise ValueError("Invalid behavior location/kind")
        if item["status"] not in {"confirmed", "uncertain", "unverified"}:
            raise ValueError("Invalid behavior status")
        for field, allowed in (("branch", {"normal", "alternate", "error", "retry", "stop"}),
                               ("execution", {"sequential", "parallel", "unordered"}),
                               ("scenarioKind", {"typical", "alternate", "error", "retry", "lifecycle"})):
            if field in item and (item["kind"] != "step" or item[field] not in allowed):
                raise ValueError(f"Invalid behavior {field}")
        if "numeric" in item and (item["kind"] != "rule" or type(item["numeric"]) is not bool):
            raise ValueError("Invalid behavior numeric flag")
        if "condition" in item and (item["kind"] != "step" or type(item["condition"]) is not bool):
            raise ValueError("Invalid behavior condition flag")
    path_keys = set()
    for path in ref.get("paths", []):
        if path["key"] in path_keys or not path["roles"] or any(role not in keys for role in path["roles"]):
            raise ValueError("Invalid path roles or duplicate key")
        path_keys.add(path["key"])
        if path["kind"] not in {"typical", "alternate", "error", "retry", "lifecycle"}:
            raise ValueError("Invalid path kind")


def check_behaviors(graph, ref, mapped):
    """Match source locations and execution metadata; prose remains a human check."""
    evidence = {e["id"]: e for e in graph["evidence"]}
    edges = {e["id"]: e for e in graph["edges"]}
    def target(step):
        return step.get("nodeId") or edges.get(step.get("edgeId"), {}).get("to")
    items = [("rule", r, r["nodeIds"], None) for r in graph["rules"]]
    items += [("transition", r, [r["subjectNodeId"]], None) for r in graph["stateTransitions"]]
    items += [("step", step, [target(step)], scenario["kind"])
              for scenario in graph["scenarios"] for step in scenario.get("steps", [])]
    errors, critical, missing = [], [], []
    for expected in ref.get("behaviors", []):
        found = []
        for kind, item, owners, scenario_kind in items:
            if kind != expected["kind"] or mapped.get(expected["role"]) is None or mapped[expected["role"]] not in owners:
                continue
            if any(item.get(k) != expected[k] for k in ("branch", "execution", "numeric") if k in expected):
                continue
            if "scenarioKind" in expected and expected["scenarioKind"] != scenario_kind:
                continue
            if "condition" in expected and bool(item.get("condition", "").strip()) != expected["condition"]:
                continue
            if any(evidence[e]["file"] == expected["file"] and evidence[e]["startLine"] <= expected["line"] <= evidence[e]["endLine"]
                   for e in item["evidenceIds"]):
                found.append(item)
        if not any(item["displayStatus"] == expected["status"] for item in found):
            missing.append(expected["key"])
            errors.append("behavior-missing:"+expected["key"])
        if expected["status"] != "confirmed" and any(item["displayStatus"] == "confirmed" for item in found):
            critical.append("behavior-certainty:"+expected["key"])
    missing_paths = []
    for expected in ref.get("paths", []):
        wanted = [mapped.get(role) for role in expected["roles"]]
        matches = False
        for scenario in graph["scenarios"]:
            if scenario.get("kind") != expected["kind"] or None in wanted:
                continue
            # Ordered subsequence: extra explanatory steps are allowed, reversals are not.
            remaining = iter(target(step) for step in scenario["steps"])
            if all(any(actual == role for actual in remaining) for role in wanted):
                matches = True
                break
        if not matches:
            missing_paths.append(expected["key"])
            errors.append("path-missing:"+expected["key"])
    return dict(errors=errors, criticalErrors=critical, missingBehaviors=missing, missingPaths=missing_paths,
                requiredBehaviors=len(ref.get("behaviors", [])), matchedBehaviors=len(ref.get("behaviors", []))-len(missing),
                requiredPaths=len(ref.get("paths", [])), matchedPaths=len(ref.get("paths", []))-len(missing_paths))


def match_roles(graph, ref):
    evidence = {e["id"]: e for e in graph["evidence"]}
    matches = {}
    for role in ref["nodes"]:
        candidates = []
        for node in graph["nodes"]:
            if node["contextOnly"] or node["kind"] != role["kind"]:
                continue
            if role["codeNames"] and node.get("codeName") not in role["codeNames"]:
                continue
            if any(evidence[e]["file"] == role["file"] and
                   evidence[e]["startLine"] <= role["line"] <= evidence[e]["endLine"]
                   for e in node["evidenceIds"]):
                candidates.append(node)
        matches[role["key"]] = candidates
    return matches


def check_graph(graph, ref):
    """Check explicit source-role criteria. Prose truth remains a human decision."""
    errors, critical = [], []
    matches = match_roles(graph, ref)
    mapped, missing_nodes, missing_edges = {}, [], []
    for role in ref["nodes"]:
        found = matches[role["key"]]
        if len(found) != 1:
            missing_nodes.append(role["key"])
            errors.append(f"role-{('missing' if not found else 'ambiguous')}:{role['key']}")
            continue
        node = found[0]
        if node["id"] in mapped.values():
            errors.append(f"role-reused:{role['key']}")
            missing_nodes.append(role["key"])
            continue
        mapped[role["key"]] = node["id"]
        if node["displayStatus"] != role["status"]:
            message = f"role-certainty:{role['key']}:{node['displayStatus']}"
            errors.append(message)
            if node["displayStatus"] == "confirmed":
                critical.append(message)
    matched_edges = set()
    for expected in ref["edges"]:
        key = f"{expected['fromRole']}:{expected['type']}:{expected['toRole']}"
        found = [e for e in graph["edges"] if e["from"] == mapped.get(expected["fromRole"])
                 and e["to"] == mapped.get(expected["toRole"]) and e["type"] == expected["type"]]
        if not found:
            missing_edges.append(key)
            errors.append(f"relationship-missing:{key}")
        for edge in found:
            matched_edges.add(edge["id"])
            if edge["displayStatus"] != expected["status"]:
                message = f"relationship-certainty:{key}:{edge['displayStatus']}"
                errors.append(message)
                if edge["displayStatus"] == "confirmed":
                    critical.append(message)
    for forbidden in ref["forbiddenEdges"]:
        if any(e["from"] == mapped.get(forbidden["fromRole"]) and e["to"] == mapped.get(forbidden["toRole"])
               and e["type"] == forbidden["type"] and e["displayStatus"] == forbidden["status"] for e in graph["edges"]):
            message = f"forbidden-relationship:{forbidden['fromRole']}:{forbidden['type']}:{forbidden['toRole']}"
            errors.append(message)
            critical.append(message)
    if graph["analysis"]["status"] not in ref["statuses"]:
        errors.append("analysis-status")
        if graph["analysis"]["status"] == "complete":
            critical.append("unresolved-marked-complete")
    if graph["analysis"]["status"] != "complete" and (not graph["analysis"]["unresolved"] or not graph["summary"]["limitations"]):
        errors.append("missing-unresolved-limitations")
    if ref["noScenarios"] and graph["scenarios"]:
        errors.append("invented-ordered-scenario")
    if any(e["locationStatus"] != "passed" for e in graph["evidence"]):
        errors.append("evidence-location-failed")
    behavior = check_behaviors(graph, ref, mapped)
    errors += behavior.pop("errors")
    critical += behavior.pop("criticalErrors")
    return dict(**behavior, errors=errors, criticalErrors=critical, missingNodes=missing_nodes, missingEdges=missing_edges,
                requiredNodes=len(ref["nodes"]), matchedNodes=len(ref["nodes"])-len(missing_nodes),
                requiredEdges=len(ref["edges"]), matchedEdges=len(ref["edges"])-len(missing_edges),
                additionalNodes=[n["id"] for n in graph["nodes"] if n["id"] not in mapped.values()],
                additionalEdges=[e["id"] for e in graph["edges"] if e["id"] not in matched_edges])


def review_template(candidate, ref, engine_hash):
    return dict(version=VERSION, caseId=ref["caseId"], candidateHash=digest(candidate),
                expectationHash=digest(ref), engineHash=engine_hash,
                reference=dict(decision="pending", reviewer=None, reviewedAt=None),
                candidate=dict(decision="pending", reviewer=None, reviewedAt=None,
                               axes={axis: "pending" for axis in AXES},
                               facts={f"fact-{i}": "pending" for i in range(1, len(ref["requiredFacts"])+1)},
                               forbidden={f"forbidden-{i}": "pending" for i in range(1, len(ref["forbiddenClaims"])+1)},
                               criticalErrors=[], notes=""))


def review_status(review, candidate, ref, engine_hash):
    if review is None:
        return "pending", [], []
    if not isinstance(review, dict):
        return "invalid", ["invalid-review-object"], []
    template = review_template(candidate, ref, engine_hash)
    if any(review.get(k) != template[k] for k in ("version", "caseId", "candidateHash", "expectationHash", "engineHash")):
        return "stale", ["review-digest-mismatch"], []
    errors, critical = [], []
    for key in ("reference", "candidate"):
        block = review.get(key, {})
        if not isinstance(block, dict):
            return "invalid", ["invalid-review-block"], []
        if block.get("decision") not in {"pending", "pass", "fail"}:
            return "invalid", ["invalid-review-decision"], []
        if block["decision"] != "pending":
            if not isinstance(block.get("reviewer"), str) or not block["reviewer"].strip():
                return "invalid", ["reviewer-required"], []
            try:
                stamp = datetime.fromisoformat(block["reviewedAt"].replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    raise ValueError("timezone required")
            except (ValueError, TypeError, KeyError, AttributeError):
                return "invalid", ["review-time-required"], []
        if block["decision"] == "fail":
            errors.append(f"human-{key}-failed")
    c = review.get("candidate", {})
    for group in ("axes", "facts", "forbidden"):
        values = c.get(group, {})
        if not isinstance(values, dict) or set(values) != set(template["candidate"][group]) or any(v not in ("pending", "pass", "fail") for v in values.values()):
            return "invalid", [f"invalid-review-{group}"], []
        errors.extend(f"human-{group}:{key}" for key, value in values.items() if value == "fail")
    findings = c.get("criticalErrors")
    if not isinstance(findings, list) or any(not isinstance(t, str) or not t.strip() for t in findings):
        return "invalid", ["invalid-critical-findings"], []
    critical.extend(findings)
    if errors or critical:
        return "failed", errors, critical
    if all(review[k]["decision"] == "pass" for k in ("reference", "candidate")) and all(
            v == "pass" for group in ("axes", "facts", "forbidden") for v in c[group].values()):
        return "passed", [], []
    return "pending", [], []


def engine_hash():
    files = sorted(p for skill in ("code-flow", "visual-primer") for p in (ROOT / "skills" / skill).rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    files += [Path(__file__).resolve(), ROOT / "scripts/evaluate_rules.py", ROOT / "eval/rubric.md"]
    return digest({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


def evidence_line_count(ranges):
    """Count the union of ranges without expanding possibly very large inputs."""
    total, last_file, last_end = 0, None, 0
    for file, first, last in sorted(ranges):
        if file != last_file:
            last_file, last_end = file, 0
        total += max(0, last - max(first-1, last_end))
        last_end = max(last_end, last)
    return total


def evaluate_case(case, source, ref, candidate_path, source_root, output, fingerprint, review=None, origin="external-candidate"):
    start = time.perf_counter()
    result = dict(id=case["id"], profile=case["profile"], variant=case["variant"],
                  expectationHash=digest(ref), candidateHash=None, autoStatus="failed", status="failed",
                  errors=[], criticalErrors=[], reviewStatus="pending",
                  metrics=dict(generationSeconds=None, inputTokens=None, outputTokens=None, costUSD=None, model=None),
                  requiredNodes=len(ref["nodes"]), matchedNodes=0, requiredEdges=len(ref["edges"]), matchedEdges=0,
                  requiredBehaviors=len(ref.get("behaviors", [])), matchedBehaviors=0,
                  requiredPaths=len(ref.get("paths", [])), matchedPaths=0,
                  missingBehaviors=[b["key"] for b in ref.get("behaviors", [])],
                  missingPaths=[p["key"] for p in ref.get("paths", [])],
                  missingNodes=[n["key"] for n in ref["nodes"]],
                  missingEdges=[f"{e['fromRole']}:{e['type']}:{e['toRole']}" for e in ref["edges"]])
    try:
        data = read(candidate_path)
        result["candidateHash"] = digest(data)
        s2s.validate(data)
        expected = ref["identity"]
        subject_fields = ("id", "kind", "question", "module", "targets", "scope")
        if any(data[k] != expected[k] for k in ("layer", "language")) or any(
                data["subject"][k] != expected["subject"][k] for k in subject_fields) or data["analysis"]["profiles"] != ref["profiles"]:
            raise ValueError("candidate-target-scope-profile-mismatch")
        if data["snapshot"]["repository"] != source["repository"] or data["snapshot"]["commit"] != source["commit"]:
            raise ValueError("candidate-source-mismatch")
        snap = author.snapshot(source_root)
        if snap["commit"] != source["commit"] or snap["workingTreeClean"] is not True:
            raise ValueError("source-checkout-must-be-clean-at-pin")
        prepared = author.build(data, source_root, output / f"{case['id']}.html",
                                output / f"{case['id']}.render.json")
        if any("anchorText" in e for e in prepared["evidence"]):
            raise ValueError("internal-source-anchor-leaked")
        result.update(check_graph(prepared, ref))
        result["analysisStatus"] = prepared["analysis"]["status"]
        review_state, human_errors, human_critical = review_status(review, data, ref, fingerprint)
        result["autoStatus"] = "failed" if result["errors"] or result["criticalErrors"] else "passed"
        result["reviewStatus"] = review_state
        result["errors"] += human_errors
        result["criticalErrors"] += human_critical
        result["status"] = ("failed" if result["errors"] or result["criticalErrors"] else
                            "passed" if review_state == "passed" else "pending-review")
        ranges = {(e["file"], e["startLine"], e["endLine"]) for e in data["evidence"]}
        result["metrics"] = dict(evidenceFiles=len({e["file"] for e in data["evidence"]}),
                                  evidenceRanges=len(ranges), evidenceLines=evidence_line_count(ranges),
                                  recordedSearchEntries=len(set(data["analysis"]["searched"])),
                                  generationSeconds=None, inputTokens=None, outputTokens=None, costUSD=None,
                                  model=data["snapshot"]["model"], skillVersion=data["snapshot"]["skillVersion"])
        result["recordedCandidate"] = dict(generatedAt=data["snapshot"]["generatedAt"],
                                            provenance=data["provenance"]["description"],
                                            origin=origin)
        author.write_json(output / f"{case['id']}.review-template.json", review_template(data, ref, fingerprint), exclusive=True)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["errors"].append(f"evaluation-error:{exc}")
        result["autoStatus"] = "failed"
        result["status"] = "failed"
    result["metrics"]["evaluationSeconds"] = round(time.perf_counter()-start, 4)
    return result


def summarize(results):
    groups = {}
    for profile in author.PROFILES:
        rows = [r for r in results if r["profile"] == profile]
        if not rows:
            continue
        nodes = sum(r.get("requiredNodes", 0) for r in rows)
        edges = sum(r.get("requiredEdges", 0) for r in rows)
        groups[profile] = dict(cases=len(rows), autoPassed=sum(r["autoStatus"] == "passed" for r in rows),
                               accepted=sum(r["status"] == "passed" for r in rows),
                               criticalErrors=sum(len(r["criticalErrors"]) for r in rows),
                               nodeRecall=sum(r.get("matchedNodes", 0) for r in rows)/nodes if nodes else None,
                               edgeRecall=sum(r.get("matchedEdges", 0) for r in rows)/edges if edges else None,
                               errors=dict(Counter(e.split(":")[0] for r in rows for e in r["errors"])))
    return groups


def markdown(report):
    lines = ["# Source-backed evaluation run", "", f"- Run: `{report['createdAt']}`",
             f"- Mode: `{report['mode']}`; this is candidate replay, not independent model generation.",
             f"- Gate: **{report['status']}**; coverage: {len(report['results'])}/{report['suiteSize']}",
             f"- Engine: `{report['engineHash']}`; repository: `{report['repositorySnapshot']['commit']}`; clean: `{report['repositorySnapshot']['workingTreeClean']}`",
             "- Unknown generation tokens, time, cost and model remain null. Evidence lines are not total discovery reads.",
             "- Automatic checks verify explicit structure/location criteria. Human facts, conditions and comprehension require review.", "",
             "| Profile | Cases | Automatic pass | Human accepted | Node recall | Edge recall | Critical findings |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for profile, s in report["profiles"].items():
        pct = lambda v: "N/A" if v is None else f"{v:.0%}"
        lines.append(f"| {profile} | {s['cases']} | {s['autoPassed']} | {s['accepted']} | {pct(s['nodeRecall'])} | {pct(s['edgeRecall'])} | {s['criticalErrors']} |")
    lines += ["", "| Case | Auto | Final | Analysis | Behaviors / paths matched | Evidence files/lines | Review | Errors |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in report["results"]:
        error = "; ".join(r["errors"] + r["criticalErrors"]).replace("|", "\\|").replace("\n", " ") or "—"
        m = r["metrics"]
        behavior = f"{r.get('matchedBehaviors', 0)}/{r.get('requiredBehaviors', 0)} · {r.get('matchedPaths', 0)}/{r.get('requiredPaths', 0)}"
        lines.append(f"| {r['id']} | {r['autoStatus']} | {r['status']} | {r.get('analysisStatus', '—')} | {behavior} | {m.get('evidenceFiles', '—')}/{m.get('evidenceLines', '—')} | {r['reviewStatus']} | {error} |")
    return "\n".join(lines) + "\n"


def run(args):
    manifest_path = Path(args.manifest).resolve()
    suite, sources = load_suite(manifest_path)
    ids = set(args.case or [c["id"] for c in suite["cases"]])
    if ids - {c["id"] for c in suite["cases"]}:
        raise ValueError("Unknown requested case")
    output = Path(args.output).resolve()
    # A new run directory also protects candidates, previous HTML, and human answers.
    output.mkdir(parents=True, exist_ok=False)
    fingerprint = engine_hash()
    results = []
    for case in suite["cases"]:
        if case["id"] not in ids:
            continue
        ref = read(within(manifest_path.parent, case["expectation"]))
        candidate = (within(args.candidates, f"{case['id']}.json") if args.candidates else
                     within(manifest_path.parent, case["candidate"]))
        review_path = within(args.reviews, f"{case['id']}.json") if args.reviews else None
        # Malformed review files fail configuration; no approvals are silently discarded.
        review = read(review_path) if review_path and review_path.exists() else None
        result = evaluate_case(case, sources[case["source"]], ref, candidate,
                               within(args.source_cache, case["source"]), output, fingerprint, review,
                               "external-candidate" if args.candidates else case.get("origin", "unspecified"))
        results.append(result)
        print(f"{case['id']}: automatic={result['autoStatus']}; gate={result['status']}")
    status = ("failed" if any(r["status"] == "failed" for r in results) else
              "passed" if len(results) == len(suite["cases"]) and all(r["status"] == "passed" for r in results) else
              "pending-review" if len(results) == len(suite["cases"]) else "incomplete")
    report = dict(version=VERSION, createdAt=datetime.now(timezone.utc).isoformat(),
                  mode="candidate-evaluation" if args.candidates else "recorded-candidate-replay",
                  executionConditions=dict(targetCodeExecuted=False, modelInvoked=False,
                                           evidence="fresh source-file hash, anchor and range verification",
                                           generationMeasurements="not available in this replay"),
                  manifestHash=digest(suite), engineHash=fingerprint, repositorySnapshot=author.snapshot(ROOT),
                  sources=list(sources.values()), suiteSize=len(suite["cases"]), status=status,
                  results=results, profiles=summarize(results))
    author.write_json(output / "results.json", report, exclusive=True)
    (output / "report.md").write_text(markdown(report), encoding="utf-8")
    return 1 if status == "failed" or (args.strict and status != "passed") else 0


def compare(before, after, allow_suite_extension=False):
    """Report per-case regressions; changed reference/source criteria are incomparable."""
    if before["version"] != VERSION or after["version"] != VERSION:
        raise ValueError("Unsupported report version")
    if len({r["id"] for r in before["results"]}) != len(before["results"]) or len({r["id"] for r in after["results"]}) != len(after["results"]):
        raise ValueError("Duplicate report case IDs")
    regressions, incomparable = [], []
    old, new = ({r["id"]: r for r in report["results"]} for report in (before, after))
    extension = (allow_suite_extension and old.keys() < new.keys()
                 and after.get("suiteSize") == len(new) and before.get("suiteSize") == len(old)
                 and before["sources"] == after["sources"])
    if (before["manifestHash"] != after["manifestHash"] and not extension) or before["sources"] != after["sources"]:
        incomparable.append("suite-or-source-changed")
    for identifier, b in old.items():
        a = new.get(identifier)
        if a is None:
            regressions.append(f"{identifier}:missing-case")
            continue
        if a["expectationHash"] != b["expectationHash"]:
            incomparable.append(f"{identifier}:expectation-changed")
            continue
        if a["profile"] != b["profile"] or a["variant"] != b["variant"]:
            incomparable.append(f"{identifier}:classification-changed")
            continue
        if a["criticalErrors"]:
            regressions.append(f"{identifier}:critical-errors-present")
        if b["autoStatus"] == "passed" and a["autoStatus"] != "passed":
            regressions.append(f"{identifier}:automatic-check-regressed")
        if b["status"] == "passed" and a["status"] != "passed":
            regressions.append(f"{identifier}:accepted-result-lost")
        for kind in ("Nodes", "Edges", "Behaviors", "Paths", "Rules"):
            if a.get("matched"+kind, 0) < b.get("matched"+kind, 0):
                regressions.append(f"{identifier}:required-{kind.lower()}-lost")
        if set(a["errors"]) - set(b["errors"]):
            regressions.append(f"{identifier}:new-errors")
    for identifier in new.keys() - old.keys():
        if new[identifier]["status"] == "failed" or new[identifier]["criticalErrors"]:
            regressions.append(f"{identifier}:added-case-failed")
    return dict(status="regressed" if regressions else "incomparable" if incomparable else "no-regression",
                regressions=regressions, incomparable=incomparable,
                comparedCases=len(old.keys() & new.keys()), addedCases=sorted(new.keys()-old.keys()),
                note="No regression is not human acceptance; inspect each run's gate and profile results.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run")
    execute.add_argument("--manifest", default=str(ROOT / "eval/cases.json"))
    execute.add_argument("--source-cache", default=str(ROOT / ".cache/m1-sources"))
    execute.add_argument("--candidates", help="Directory containing one internal <case-id>.json per selected case")
    execute.add_argument("--reviews", help="Directory containing digest-bound <case-id>.json human reviews")
    execute.add_argument("--output", required=True, help="New output directory; existing directories are preserved")
    execute.add_argument("--case", action="append")
    execute.add_argument("--strict", action="store_true", help="Fail unless every suite case passes automatic and human gates")
    diff = commands.add_parser("compare")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--allow-suite-extension", action="store_true", help="Compare an expanded complete suite while retaining every prior source/reference/classification")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return run(args)
        result = compare(read(args.before), read(args.after), args.allow_suite_extension)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "no-regression" else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Evaluation configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

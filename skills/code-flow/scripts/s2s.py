#!/usr/bin/env python3
"""Validate evidence-backed graphs and render a self-contained, offline viewer."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit

import schema_validation

SKILL = Path(__file__).resolve().parents[1]
SCHEMA_DIR = SKILL / "references"
TEMPLATE = SKILL / "templates/flow-viewer-template.html"


class InvalidGraph(ValueError):
    pass


def schema(stage):
    return json.loads((SCHEMA_DIR / f"ir-{stage}-v0.1.0.schema.json").read_text(encoding="utf-8"))


def claims(data):
    for key in ("nodes", "edges", "stateTransitions", "rules", "regions"):
        for item in data[key]:
            yield item
            if key == "nodes":
                yield from item["actions"]
    for scenario in data["scenarios"]:
        yield from scenario["steps"]
    yield from (s for s in data["subjects"] if "scope" in s)
    yield from data.get("structureEntries", [])


def all_objects(data):
    yield from claims(data)
    for key in ("scenarios", "evidence", "warnings", "sources"):
        yield from data[key]
    yield from (s for s in data["subjects"] if "scope" not in s)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def relative_path(value):
    decoded = unquote(value)
    return (bool(decoded) and not urlsplit(decoded).scheme
            and not decoded.startswith(("/", "\\"))
            and "\\" not in decoded
            and not any(ord(c) < 32 for c in decoded))


def confirmed(item, evidence):
    return (not item.get("contextOnly")
            and item["confidence"] in ("exact", "resolved")
            and item["supportStatus"] == "supported"
            and all(evidence[x]["locationStatus"] == "passed" for x in item["evidenceIds"]))


def numerical_rule(rule):
    text = " ".join(strings({key: rule.get(key, "") for key in
                            ("plainText", "condition", "outcome", "rationale", "exceptions")}))
    return rule["numeric"] or bool(re.search(r"\d", text))


def validate(data, stage="internal"):
    contract = schema(stage)
    validate_schema(data, contract, stage)
    objects = list(all_objects(data))
    ids = [item["id"] for item in objects]
    if len(ids) != len(set(ids)):
        raise InvalidGraph("IDs must be globally unique.")
    known = set(ids)
    nodes = {n["id"]: n for n in data["nodes"]}
    edges = {e["id"]: e for e in data["edges"]}
    evidence = {e["id"]: e for e in data["evidence"]}
    sources = {s["id"] for s in data["sources"]}

    def check(values, targets, label):
        missing = set(values) - set(targets)
        if missing:
            raise InvalidGraph(f"{label}: unknown references {sorted(missing)}")

    for item in claims(data):
        check(item.get("evidenceIds", []), evidence, item["id"])
        check(item.get("sourceIds", []), sources, item["id"])
        check(item.get("nodeIds", []), nodes, item["id"])
        if stage == "render":
            status = ("context" if item.get("contextOnly") else
                      "confirmed" if confirmed(item, evidence) else
                      "unverified" if any(evidence[x]["locationStatus"] != "passed"
                                           for x in item["evidenceIds"]) else "uncertain")
            if item["displayStatus"] != status:
                raise InvalidGraph(f"{item['id']}: display status disagrees with evidence.")
    for edge in data["edges"]:
        check([edge["from"], edge["to"]], nodes, edge["id"])
    for scenario in data["scenarios"]:
        for step in scenario["steps"]:
            if "nodeId" in step:
                check([step["nodeId"]], nodes, step["id"])
            else:
                check([step["edgeId"]], edges, step["id"])
    for item in data["stateTransitions"]:
        check([item["subjectNodeId"]], nodes, item["id"])
    for item in data["subjects"]:
        check([item["nodeId"]], nodes, item["id"])
    entries = data.get("structureEntries", [])
    if entries and data["layer"] != "atlas":
        raise InvalidGraph("Structure entries belong only to a project atlas.")
    paths = set()
    for item in entries:
        path = item["path"]
        # Canonical, literal repository paths, not URLs. Containment only:
        # package membership must never create graph edges.
        if (not relative_path(path) or unquote(path) != path
                or ".." in PurePosixPath(path).parts or str(PurePosixPath(path)) != path):
            raise InvalidGraph(f"{item['id']}: structure path must be canonical and inside the source root.")
        if path in paths:
            raise InvalidGraph("Structure paths must be unique.")
        paths.add(path)
        local = [evidence[eid] for eid in item["evidenceIds"]
                 if evidence[eid]["kind"] in ("code", "config")]
        if not any(e["file"] == path if item["kind"] == "file" else
                   (path == "." or e["file"].startswith(path + "/")) for e in local):
            raise InvalidGraph(f"{item['id']}: structure needs code/config evidence at or inside its path.")
    for item in entries:
        if item["kind"] == "file" and any(p.startswith(item["path"] + "/") for p in paths):
            raise InvalidGraph(f"{item['id']}: a file cannot contain structure entries.")
    if data["layer"] == "atlas":
        memberships = [n for r in data["regions"] for n in r["nodeIds"]]
        if len(memberships) != len(set(memberships)):
            raise InvalidGraph("Atlas regions must have disjoint node membership; use edges for shared dependencies.")
    for warning in data["warnings"]:
        check(warning["relatedIds"], known, warning["id"])
    for item in data["evidence"]:
        if item["endLine"] < item["startLine"]:
            raise InvalidGraph(f"{item['id']}: reversed line range.")
        if not relative_path(item["file"]) or ".." in PurePosixPath(item["file"]).parts:
            raise InvalidGraph(f"{item['id']}: evidence path must stay inside the source root.")
        if stage == "render" and item["locationStatus"] == "passed":
            if item["contentHash"] is None or item.get("observedContentHash", item["contentHash"]) != item["contentHash"]:
                raise InvalidGraph(f"{item['id']}: passed evidence requires matching captured and observed hashes.")
    for source in data["sources"]:
        url = urlsplit(source["url"])
        if url.scheme not in ("https", "http") or not url.netloc:
            raise InvalidGraph(f"{source['id']}: external source must be an HTTP(S) URL.")
    for link in [*data["links"].values(), *(s["link"] for s in data["subjects"])]:
        if not relative_path(link["url"]):
            raise InvalidGraph("Generated-page links must be relative paths.")
    if data["subject"]["id"] != data["regeneration"]["subjectId"]:
        raise InvalidGraph("Regeneration subject differs from the graph subject.")
    if data["language"] != data["regeneration"]["language"]:
        raise InvalidGraph("Regeneration language differs from the graph language.")
    if data["analysis"]["status"] == "complete" and data["analysis"]["unresolved"]:
        raise InvalidGraph("Complete analysis cannot contain unresolved questions.")
    if stage == "render":
        for rule in data["rules"]:
            if numerical_rule(rule) and not confirmed(rule, evidence):
                raise InvalidGraph(f"{rule['id']}: unverified numerical rule reached the output.")
    return data


def validate_schema(data, contract, stage="internal", *, formats=True):
    try:
        return schema_validation.validate(data, contract, stage, formats=formats)
    except schema_validation.InvalidSchemaData as error:
        raise InvalidGraph(str(error)) from None


def check_schema(contract):
    schema_validation.check_schema(contract)


def verify_locations(data, source_root):
    root = Path(source_root).resolve()
    for item in data["evidence"]:
        item["observedContentHash"] = None
        try:
            path = (root / item["file"]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Evidence symlink leaves the source root.")
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            item["observedContentHash"] = digest
            lines = raw.decode("utf-8").splitlines()
            if item["endLine"] > len(lines):
                raise ValueError("The evidence range exceeds the file.")
            if item["anchorText"] not in lines[item["startLine"] - 1:item["endLine"]]:
                raise ValueError("The exact evidence anchor is absent from the selected range.")
            if item["contentHash"] is not None and item["contentHash"] != digest:
                raise ValueError("Source content changed since evidence capture.")
            item["contentHash"] = digest
            item["locationStatus"] = "passed"
            item["locationNote"] = ""
        except (OSError, ValueError, UnicodeError) as error:
            item["locationStatus"] = "failed"
            item["locationNote"] = str(error)
    return data


def read_embedded(path):
    content = Path(path).read_text(encoding="utf-8")
    match = re.search(r'<script id="s2s-data" type="application/json">([\s\S]*?)</script>', content)
    if not match:
        raise InvalidGraph("The page contains no Source to Sight metadata.")
    return json.loads(match.group(1))


def source_matches(left, right, source_root=None):
    a, b = left["snapshot"], right["snapshot"]
    if a["repository"] != b["repository"] or a["commit"] != b["commit"]:
        return False
    # A failed reread retains the reviewed hash for diagnosis, not as proof that
    # the current source still matches a previously generated page.
    for evidence in [*left["evidence"], *right["evidence"]]:
        if (evidence["locationStatus"] != "passed" or evidence["contentHash"] is None
                or evidence.get("observedContentHash", evidence["contentHash"]) != evidence["contentHash"]):
            return False
    def captured_hashes(data):
        result = {}
        for evidence in data["evidence"]:
            result.setdefault(evidence["file"], set()).add(evidence["contentHash"])
        return result
    hashes_a, hashes_b = captured_hashes(left), captured_hashes(right)
    common = set(hashes_a) & set(hashes_b)
    if any(len(values) != 1 or None in values for values in [*hashes_a.values(), *hashes_b.values()]):
        return False
    if any(hashes_a[k] != hashes_b[k] for k in common):
        return False
    if source_root is not None:
        # Git cleanliness says nothing about ignored files (generated settings,
        # installed dependencies, etc.). Reread both pages' complete evidence
        # scope, including files that only the linked page examined.
        root = Path(source_root).resolve()
        for file, hashes in (hashes_a | hashes_b).items():
            try:
                path = (root / file).resolve()
                if not path.is_relative_to(root):
                    return False
                if {hashlib.sha256(path.read_bytes()).hexdigest()} != hashes:
                    return False
            except (OSError, ValueError, RuntimeError):
                return False
    if (source_root is not None and a["commit"]
            and a["workingTreeClean"] is True and b["workingTreeClean"] is True):
        return True
    # Without a reread and shared clean commit, compare the entire recorded
    # evidence-file set. A shared subset cannot establish the rest of the scope.
    return bool(hashes_a) and hashes_a == hashes_b


def prepare(original, source_root, output_path=None, linked_pages=None):
    """Location checks are deterministic; supplied semantic reviews stay explicit."""
    validate(original)
    data = verify_locations(copy.deepcopy(original), source_root)
    evidence = {e["id"]: e for e in data["evidence"]}
    occupied = {obj["id"] for obj in all_objects(data)}
    ko = data["language"].lower().startswith("ko")

    def warn(kind, message, related=(), candidates=(), severity="medium"):
        index = 1
        while f"auto-{kind}-{index}" in occupied:
            index += 1
        identifier = f"auto-{kind}-{index}"
        occupied.add(identifier)
        data["warnings"].append({"id": identifier, "kind": kind, "severity": severity,
                                 "message": message, "relatedIds": list(related),
                                 "candidates": list(candidates)})

    for item in data["evidence"]:
        if item["locationStatus"] == "failed":
            message = (f"근거 위치를 다시 확인하지 못했습니다: {item['file']}" if ko
                       else f"Evidence could not be reverified: {item['file']}")
            warn("evidence-unverified", message, [item["id"]])

    def supported(item):
        if item.get("contextOnly") or item["supportStatus"] != "unsupported":
            return True
        label = item.get("label", item.get("plainText", item.get("caption", item["id"])))
        warn("claim-unsupported", ("근거가 설명을 뒷받침하지 않아 제외했습니다: " if ko
                                  else "Unsupported claim omitted: ") + label)
        return False

    data["nodes"] = [n for n in data["nodes"] if supported(n)]
    for node in data["nodes"]:
        node["actions"] = [a for a in node["actions"] if supported(a)]
    node_ids = {n["id"] for n in data["nodes"]}
    data["edges"] = [e for e in data["edges"]
                     if supported(e) and e["from"] in node_ids and e["to"] in node_ids]
    edge_ids = {e["id"] for e in data["edges"]}
    scenarios = []
    for scenario in data["scenarios"]:
        valid = all(supported(step) and
                    (step.get("nodeId") in node_ids if "nodeId" in step else
                     step.get("edgeId") in edge_ids) for step in scenario["steps"])
        if valid:
            scenarios.append(scenario)
        else:
            warn("coverage-limited", ("근거가 끊긴 시나리오를 제외했습니다: " if ko
                                      else "A scenario with a missing claim was omitted: ") + scenario["title"])
    data["scenarios"] = scenarios
    data["stateTransitions"] = [s for s in data["stateTransitions"]
                               if supported(s) and s["subjectNodeId"] in node_ids]
    data["regions"] = [r for r in data["regions"]
                       if supported(r) and set(r["nodeIds"]) <= node_ids]
    data["subjects"] = [s for s in data["subjects"] if s["nodeId"] in node_ids
                        and ("scope" not in s or supported(s))]
    if "structureEntries" in data:
        data["structureEntries"] = [s for s in data["structureEntries"] if supported(s)]
        for item in data["structureEntries"]:
            # A directory may remain documented after an unrelated owner was
            # omitted. Drop only the invalid navigation references.
            item["nodeIds"] = [n for n in item["nodeIds"] if n in node_ids]
    rules = []
    for rule in data["rules"]:
        if not supported(rule) or not set(rule["nodeIds"]) <= node_ids:
            continue
        if numerical_rule(rule) and not confirmed(rule, evidence):
            warn("claim-unsupported", (
                 "수치 규칙의 근거가 부족해 본문에서 제외했습니다." if ko else
                 "A numerical rule lacked verified support and was omitted."))
        else:
            rules.append(rule)
    data["rules"] = rules
    for item in claims(data):
        item["displayStatus"] = ("context" if item.get("contextOnly") else
            "confirmed" if confirmed(item, evidence) else
            "unverified" if any(evidence[x]["locationStatus"] != "passed" for x in item["evidenceIds"])
            else "uncertain")
    if sum(n["importance"] == "core" for n in data["nodes"]) > 7:
        warn("node-budget-exceeded", "핵심 부분이 많아 모두 표시합니다." if ko else
             "This explanation has more than seven core nodes; all are retained.")

    if output_path:
        directory = Path(output_path).resolve().parent
        entries = [(kind, link, data["subject"])
                   for kind, link in data["links"].items()]
        entries += [("behavior", s["link"], s) for s in data["subjects"]]
        for kind, link, expected in entries:
            path = directory / unquote(urlsplit(link["url"]).path)
            link["generated"] = False
            try:
                other = ((linked_pages or {}).get(path.resolve())
                         if path.resolve() in (linked_pages or {}) else read_embedded(path))
                validate(other, "render")
                if other["layer"] != kind:
                    raise InvalidGraph("Wrong target layer.")
                if kind != "atlas":
                    if not subject_matches(expected, other["subject"]):
                        raise InvalidGraph("Wrong target subject or scope.")
                elif not any(subject_matches(s, data["subject"]) for s in other["subjects"]):
                    raise InvalidGraph("The atlas does not contain this explanation's subject and scope.")
                if other["language"] != data["language"]:
                    raise InvalidGraph("Wrong target language.")
                if data["layer"] == "atlas" and kind == "behavior":
                    parent = other["links"].get("atlas")
                    if not parent or (path.parent / unquote(urlsplit(parent["url"]).path)).resolve() != Path(output_path).resolve():
                        raise InvalidGraph("The detail needs a return link to this project map.")
                    # Pages in this build resolve both directions in a second
                    # pass. Existing HTML must already expose an active return.
                    if path.resolve() not in (linked_pages or {}) and not parent["generated"]:
                        raise InvalidGraph("The detail's project map return link is inactive.")
                link["generated"] = True
                if not source_matches(data, other, source_root):
                    warn("snapshot-mismatch", (
                         "연결된 설명의 소스 시점이 다르거나 확인되지 않았습니다: " if ko
                         else "The linked explanation has a different or unconfirmed source snapshot: ") + link["url"])
                    if data["layer"] == "atlas" or kind == "atlas":
                        raise InvalidGraph("Atlas navigation requires a matching source snapshot.")
            except (OSError, ValueError, KeyError):
                link["generated"] = False
                if "command" not in link:
                    skill = "codebase-atlas" if kind == "atlas" else "code-flow"
                    suffix = " --explain" if kind == "logic" else ""
                    link["command"] = f"$" + skill + " " + expected.get("question", expected.get("label", data["subject"]["question"])) + suffix

    # Pruning a rejected claim must not leave dangling warning references.
    remaining = {item["id"] for item in all_objects(data)}
    for warning in data["warnings"]:
        warning["relatedIds"] = [i for i in warning["relatedIds"] if i in remaining]
    if not any(not n.get("contextOnly") for n in data["nodes"]):
        data["analysis"]["status"] = "insufficient"
        if not data["analysis"]["unresolved"]:
            data["analysis"]["unresolved"] = ["설명에 필요한 구현 근거가 부족합니다." if ko
                                                 else "There is not enough implementation evidence."]
    elif data["analysis"]["status"] == "complete" and (
        any(i["displayStatus"] in ("uncertain", "unverified") for i in claims(data))
        or any(w["kind"] in ("claim-unsupported", "coverage-limited") for w in data["warnings"])
    ):
        data["analysis"]["status"] = "partial"
        data["analysis"]["unresolved"].append("일부 관계나 설명을 확정하지 못했습니다." if ko
                                               else "Some relationships or claims remain unconfirmed.")
    anchors = [e["anchorText"] for e in data["evidence"]]
    for item in data["evidence"]:
        del item["anchorText"]
    validate(data, "render")
    ensure_no_source_bodies(data, anchors)
    return data


def subject_matches(expected, actual):
    """Legacy catalogs check IDs; scoped catalogs also bind the resolved target."""
    return expected["id"] == actual["id"] and all(
        expected[key] == actual.get(key) for key in ("scope", "kind", "module", "targets") if key in expected)


def ensure_no_source_bodies(data, anchors=()):
    code_line = re.compile(r"(^|\n)\s*(def\s+\w+\s*\(|(?:export\s+default\s+)?function\s+\w+\s*\(|class\s+\w+\s*[:{])")
    for value in strings(data):
        if "```" in value or code_line.search(value):
            raise InvalidGraph("Source-like code blocks must be rewritten as plain explanations.")
        if any(len(anchor.strip()) >= 12 and anchor in value for anchor in anchors):
            raise InvalidGraph("An evidence anchor was copied into an output text field.")


def render(data):
    validate(data, "render")
    ensure_no_source_bodies(data)
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for character, escaped in [("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                               ("\u2028", "\\u2028"), ("\u2029", "\\u2029")]:
        encoded = encoded.replace(character, escaped)
    vendor = (SKILL / "templates/vendor/dagre.min.js").read_text(encoding="utf-8")
    notices = (SKILL / "templates/vendor/dagre.NOTICES").read_text(encoding="utf-8")
    notices += "\n\n" + (SKILL / "templates/vendor/dagre.LICENSE").read_text(encoding="utf-8")
    notices += "\n\n" + (SKILL / "templates/vendor/NotoSansKR.LICENSE").read_text(encoding="utf-8")
    font = base64.b64encode((SKILL / "templates/vendor/NotoSansKR.woff2").read_bytes()).decode("ascii")
    font_css = '@font-face{font-family:S2S;src:url(data:font/woff2;base64,' + font + ') format("woff2");font-style:normal;font-weight:400 700;font-display:swap}'
    content = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__S2S_DATA__": encoded, "__S2S_LAYOUT__": vendor,
        "__S2S_NOTICES__": html.escape(notices),
        "__S2S_TITLE__": html.escape(data["summary"]["title"]),
        "__S2S_LANGUAGE__": html.escape(data["language"], quote=True),
        "__S2S_STYLE__": font_css + "\n" + (SKILL / "templates/viewer.css").read_text(encoding="utf-8"),
        "__S2S_VIEWER__": (SKILL / "templates/viewer.js").read_text(encoding="utf-8"),
    }
    # One pass: data containing a marker must never be interpreted as a template.
    return re.sub("|".join(map(re.escape, replacements)), lambda m: replacements[m.group()], content)


def check_output_paths(output, data_output=None, inputs=()):
    outputs = [Path(p).resolve() for p in (output, data_output) if p is not None]

    def same_file(left, right):
        return left == right or (left.exists() and right.exists() and left.samefile(right))

    if len(outputs) == 2 and same_file(*outputs):
        raise ValueError("HTML and render JSON must use different paths.")
    if any(same_file(Path(source).resolve(), target) for source in inputs for target in outputs):
        raise ValueError("Keep the internal evidence file separate from generated outputs.")


def check_output_identity(data, output):
    destination = Path(output).resolve()
    if destination.exists():
        previous = validate(read_embedded(destination), "render")
        identity = lambda graph: (graph["snapshot"]["repository"], graph["layer"],
                                  graph["subject"]["id"], graph["subject"]["scope"], graph["language"])
        if identity(previous) != identity(data):
            raise ValueError("The output belongs to another subject, scope, language, or repository. Choose another path.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("validate")
    check.add_argument("input", type=Path)
    check.add_argument("--stage", choices=["internal", "render"], default="internal")
    build = sub.add_parser("render")
    build.add_argument("input", type=Path)
    build.add_argument("--source-root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--data-output", type=Path)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "inspect":
            data = validate(read_embedded(args.input), "render")
            print(json.dumps(data["regeneration"], ensure_ascii=False, indent=2))
        else:
            original = json.loads(args.input.read_text(encoding="utf-8"))
            if args.action == "validate":
                validate(original, args.stage)
                print(f"Valid {args.stage} graph: {args.input}")
            else:
                check_output_paths(args.output, args.data_output, inputs=[args.input])
                data = prepare(original, args.source_root, args.output)
                check_output_identity(data, args.output)
                output = render(data)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(output, encoding="utf-8")
                if args.data_output:
                    args.data_output.parent.mkdir(parents=True, exist_ok=True)
                    args.data_output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"{args.output} ({data['analysis']['status']}; {len(data['warnings'])} warnings)")
    except (OSError, ValueError) as error:
        parser.exit(1, f"s2s: {error}\n")


if __name__ == "__main__":
    main()

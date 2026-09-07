#!/usr/bin/env python3
"""Local authoring helpers; the host agent supplies and reviews semantic claims."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import urlsplit

import s2s

PROFILES = ("cli-utility", "library-sdk", "framework-plugin", "ai-agent", "data-event", "web")
VERSION = "0.8.0"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def git(root, *args):
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                text=True, timeout=15, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def repository_name(remote, fallback):
    if not remote:
        return fallback
    # Do not copy credentials or local remote paths into a shareable page.
    if "://" not in remote:
        match = re.fullmatch(r"(?:[^@/:]+@)?([^/:]+):(.+)", remote)
        if not match:
            return fallback
        remote = "ssh://" + match[1] + "/" + match[2]
    parsed = urlsplit(remote)
    if parsed.scheme not in ("http", "https", "ssh", "git") or not parsed.hostname:
        return fallback
    name = parsed.path.strip("/").removesuffix(".git")
    return name if parsed.hostname == "github.com" else parsed.hostname + "/" + name


def snapshot(source_root, repository=None, model=None):
    root = Path(source_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("The source root must be a directory.")
    top = git(root, "rev-parse", "--show-toplevel")
    # An ignored source archive nested inside another repository has no snapshot
    # relationship to the containing tool's own Git commit.
    tracked = git(root, "ls-files", "--", ".") if top else None
    in_repo = bool(top and (Path(top).resolve() == root or tracked))
    commit = git(root, "rev-parse", "--verify", "HEAD") if in_repo else None
    status = git(root, "status", "--porcelain", "--untracked-files=normal") if in_repo else None
    remote = git(root, "remote", "get-url", "origin") if in_repo else None
    return {"repository": repository or repository_name(remote, root.name),
            "branch": git(root, "symbolic-ref", "--quiet", "--short", "HEAD") if in_repo else None,
            "commit": commit, "workingTreeClean": status == "" if status is not None else None,
            "generatedAt": now(), "skillVersion": VERSION, "model": model}


def subject_key(module, target, includes, excludes):
    identity = json.dumps([module, target, includes, excludes], ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(identity.encode()).hexdigest()[:12]
    stem = re.sub(r"[^a-z0-9]+", "-", (module + "-" + target).lower()).strip("-")[:70] or "subject"
    if not stem[0].isalpha():
        stem = "subject-" + stem
    return stem + "-" + digest


def draft(source_root, question, title, module, target, includes, excludes, profiles,
          language="ko", kind="capability", repository=None, model=None):
    ko = language.lower().startswith("ko")
    identifier = subject_key(module, target, includes, excludes)
    command = "$code-flow " + question + " | subject=" + identifier + " | language=" + language
    data = {"schemaVersion": "0.1.0", "layer": "behavior", "language": language,
            "provenance": {"kind": "source-traced", "humanReviewed": False,
                           "description": "소스 탐색 초안 · 내용 검토 전" if ko else "Source discovery draft; semantic review pending"},
            "snapshot": snapshot(source_root, repository, model),
            "subject": {"id": identifier, "kind": kind, "title": title, "question": question,
                        "module": module, "targets": [{"label": target}],
                        "scope": {"includes": includes, "excludes": excludes}},
            "analysis": {"status": "insufficient", "profiles": profiles, "searched": [],
                         "unresolved": ["구현 근거와 설명을 아직 검토하지 않았습니다." if ko else "Implementation evidence and claims have not been reviewed."],
                         "nextAttempts": ["선택한 대상과 관련 호출·등록·상태를 읽습니다." if ko else "Read the selected target and its calls, registration, and state."]},
            "summary": {"title": title, "purpose": question, "inputs": [], "outputs": [], "limitations": []},
            "links": {}, "regeneration": {"subjectId": identifier, "question": question,
                                            "language": language, "command": command}}
    for key in ("nodes", "edges", "scenarios", "stateTransitions", "rules", "regions", "subjects", "evidence", "warnings", "sources"):
        data[key] = []
    return s2s.validate(data)


def capture_evidence(source_root, identifier, file, symbol, start, end, anchor_line=None, kind="code"):
    if not s2s.relative_path(file) or ".." in PurePosixPath(file).parts:
        raise ValueError("Evidence must name a relative path inside the source root.")
    root = Path(source_root).resolve(strict=True)
    path = (root / file).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("The evidence symlink leaves the source root.")
    raw = path.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    if not 1 <= start <= end <= len(lines):
        raise ValueError("The evidence range is outside the file or reversed.")
    if anchor_line is None:
        anchor_line = next((i for i in range(start, end + 1) if lines[i - 1].strip()), None)
    if anchor_line is None or not start <= anchor_line <= end or not lines[anchor_line - 1].strip():
        raise ValueError("Choose a nonempty anchor line inside the evidence range.")
    return {"id": identifier, "kind": kind, "file": file, "symbolOrKey": symbol,
            "startLine": start, "endLine": end, "anchorText": lines[anchor_line - 1],
            "contentHash": hashlib.sha256(raw).hexdigest(), "locationStatus": "passed"}


def capture_into(data, source_root, **evidence_args):
    result = copy.deepcopy(data)
    identifier = evidence_args["identifier"]
    if identifier in {item["id"] for item in s2s.all_objects(result)}:
        raise ValueError("The evidence ID already exists. Reread dependent claims before replacing evidence.")
    result["evidence"].append(capture_evidence(source_root, **evidence_args))
    if evidence_args["file"] not in result["analysis"]["searched"]:
        result["analysis"]["searched"].append(evidence_args["file"])
    return s2s.validate(result)


def explain_draft(data, source_root):
    """Keep the behavior's facts; a new rules review is deliberately pending."""
    s2s.validate(data)
    if data["layer"] != "behavior":
        raise ValueError("Rules discovery starts from an internal behavior graph.")
    if data["snapshot"]["commit"] != snapshot(source_root)["commit"]:
        raise ValueError("The source commit changed. Rerun behavior discovery first.")
    result = copy.deepcopy(data)
    result["layer"] = "logic"
    result["links"].pop("logic", None)
    result["provenance"]["humanReviewed"] = False
    ko = data["language"].lower().startswith("ko")
    note = ("규칙의 조건·이유·예외를 원본에서 다시 검토해야 합니다." if ko else
            "Rule conditions, reasons and exceptions need a fresh source review.")
    result["provenance"]["description"] = note
    result["analysis"]["unresolved"].append(note)
    if result["analysis"]["status"] == "complete":
        result["analysis"]["status"] = "partial"
    for rule in result["rules"]:
        rule["supportStatus"] = "uncertain"
        rule["verificationNote"] = note
    result["regeneration"]["command"] = ("$code-flow " + data["subject"]["question"] +
                                           " --explain | subject=" + data["subject"]["id"] +
                                           " | language=" + data["language"])
    return s2s.validate(result)


def prepare_build(data, source_root, output, data_output=None, linked_pages=None):
    s2s.validate(data)
    result = copy.deepcopy(data)
    current = snapshot(source_root, result["snapshot"]["repository"], result["snapshot"]["model"])
    if result["snapshot"]["commit"] != current["commit"]:
        raise ValueError("The source commit changed or cannot be verified. Rerun discovery and semantic review.")
    destination = Path(output).resolve()
    s2s.check_output_paths(destination, data_output)
    s2s.check_output_identity(result, destination)
    result["snapshot"] = current
    return s2s.prepare(result, source_root, destination, linked_pages=linked_pages)


def build(data, source_root, output, data_output=None):
    destination = Path(output).resolve()
    prepared = prepare_build(data, source_root, destination, data_output)
    page = s2s.render(prepared)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")
    if data_output:
        write_json(data_output, prepared)
    return prepared


def write_json(path, data, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def doctor():
    for stage in ("internal", "render"):
        s2s.check_schema(s2s.schema(stage))
    required = ["SKILL.md", "references/discovery-protocol.md", "references/explainer-guide.md", "references/complex-behavior.md", "references/rule-checklist.md",
                "references/assembly-protocol.md", "references/renderer-contract.md",
                "templates/flow-viewer-template.html", "templates/viewer.js", "templates/viewer.css",
                "templates/vendor/dagre.min.js", "templates/vendor/dagre.LICENSE",
                "templates/vendor/dagre.NOTICES", "templates/vendor/NotoSansKR.woff2", "templates/vendor/NotoSansKR.LICENSE"]
    required += [f"references/profiles/{profile}.md" for profile in PROFILES]
    required += ["scripts/schema_validation.py", "scripts/vendor/__init__.py",
                 "scripts/vendor/fastjsonschema.LICENSE", "scripts/vendor/PROVENANCE.md"]
    required += [f"scripts/vendor/fastjsonschema/{name}.py" for name in
                 ("__init__", "__main__", "draft04", "draft06", "draft07", "draft2019",
                  "exceptions", "generator", "indent", "ref_resolver", "version")]
    for name in required:
        if not (s2s.SKILL / name).is_file():
            raise ValueError(f"Installed skill resource is missing: {name}")
    return {"skillVersion": VERSION, "schemaVersion": "0.1.0", "profiles": list(PROFILES),
            "resources": "present", "semanticAnalysis": "performed by the host agent"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("doctor")
    init = commands.add_parser("init")
    init.add_argument("--question", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--module", required=True)
    init.add_argument("--target", required=True)
    init.add_argument("--include", dest="includes", action="append", required=True)
    init.add_argument("--exclude", dest="excludes", action="append", default=[])
    init.add_argument("--profile", dest="profiles", action="append", choices=PROFILES, required=True)
    init.add_argument("--language", default="ko")
    init.add_argument("--kind", choices=("capability", "workflow", "lifecycle"), default="capability")
    init.add_argument("--repository")
    init.add_argument("--model")
    init.add_argument("--output", type=Path, required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("input", type=Path)
    capture.add_argument("--id", dest="identifier", required=True)
    capture.add_argument("--file", required=True)
    capture.add_argument("--symbol", required=True)
    capture.add_argument("--start", type=int, required=True)
    capture.add_argument("--end", type=int, required=True)
    capture.add_argument("--anchor-line", type=int)
    capture.add_argument("--kind", choices=("code", "config", "documentation", "test"), default="code")
    assemble = commands.add_parser("build")
    assemble.add_argument("input", type=Path)
    assemble.add_argument("--output", type=Path, required=True)
    assemble.add_argument("--data-output", type=Path)
    explain = commands.add_parser("explain", help="Draft a rules review from an internal behavior graph")
    explain.add_argument("input", type=Path)
    explain.add_argument("--output", type=Path, required=True)
    for command in (init, capture, assemble, explain):
        command.add_argument("--source-root", type=Path, required=True)
    args = vars(parser.parse_args(argv))
    action = args.pop("action")
    try:
        if action == "doctor":
            print(json.dumps(doctor(), indent=2))
        elif action == "init":
            output = args.pop("output")
            data = draft(**args)
            write_json(output, data, exclusive=True)
            print(data["subject"]["id"])
        elif action == "capture":
            path = args.pop("input")
            data = json.loads(path.read_text(encoding="utf-8"))
            write_json(path, capture_into(data, **args))
            print("Captured evidence location and hash; semantic review remains required.")
        elif action == "explain":
            data = json.loads(args["input"].read_text(encoding="utf-8"))
            write_json(args["output"], explain_draft(data, args["source_root"]), exclusive=True)
            print("Rules draft created; reread source and use visual-primer to build the paired pages.")
        else:
            path = args.pop("input")
            s2s.check_output_paths(args["output"], args["data_output"], inputs=[path])
            data = build(json.loads(path.read_text(encoding="utf-8")), **args)
            print(f"{args['output']} ({data['analysis']['status']}; {len(data['warnings'])} warnings)")
    except (OSError, ValueError) as error:
        parser.exit(1, f"author: {error}\n")


if __name__ == "__main__":
    main()

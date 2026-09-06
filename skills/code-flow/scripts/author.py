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
VERSION = "0.3.0"


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


def build(data, source_root, output, data_output=None):
    s2s.validate(data)
    result = copy.deepcopy(data)
    current = snapshot(source_root, result["snapshot"]["repository"], result["snapshot"]["model"])
    if result["snapshot"]["commit"] != current["commit"]:
        raise ValueError("The source commit changed or cannot be verified. Rerun discovery and semantic review.")
    destination = Path(output).resolve()
    if data_output and Path(data_output).resolve() == destination:
        raise ValueError("HTML and render JSON must use different paths.")
    if destination.exists():
        previous = s2s.validate(s2s.read_embedded(destination), "render")
        identity = lambda graph: (graph["snapshot"]["repository"], graph["layer"],
                                  graph["subject"]["id"], graph["subject"]["scope"], graph["language"])
        if identity(previous) != identity(result):
            raise ValueError("The output belongs to another subject, scope, language, or repository. Choose another path.")
    result["snapshot"] = current
    prepared = s2s.prepare(result, source_root, destination)
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
        s2s.Draft202012Validator.check_schema(s2s.schema(stage))
    required = ["SKILL.md", "references/discovery-protocol.md", "references/explainer-guide.md", "references/complex-behavior.md",
                "references/assembly-protocol.md", "references/renderer-contract.md",
                "templates/flow-viewer-template.html", "templates/viewer.js", "templates/viewer.css",
                "templates/vendor/dagre.min.js", "templates/vendor/dagre.LICENSE",
                "templates/vendor/dagre.NOTICES", "templates/vendor/NotoSansKR.woff2", "templates/vendor/NotoSansKR.LICENSE"]
    required += [f"references/profiles/{profile}.md" for profile in PROFILES]
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
    for command in (init, capture, assemble):
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
        else:
            path = args.pop("input")
            if path.resolve() in {Path(args["output"]).resolve(), Path(args["data_output"]).resolve() if args["data_output"] else None}:
                raise ValueError("Keep the internal evidence file separate from generated outputs.")
            data = build(json.loads(path.read_text(encoding="utf-8")), **args)
            print(f"{args['output']} ({data['analysis']['status']}; {len(data['warnings'])} warnings)")
    except (OSError, ValueError) as error:
        parser.exit(1, f"author: {error}\n")


if __name__ == "__main__":
    main()

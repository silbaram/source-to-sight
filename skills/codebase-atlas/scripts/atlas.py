#!/usr/bin/env python3
"""Author a reviewed project map and connect only the requested detail pages."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import quote, unquote, urlsplit

SKILL = Path(__file__).resolve().parents[1]


def companion(root=None):
    root = Path(root).resolve() if root else SKILL.parent / "code-flow"
    if not (root / "scripts/author.py").is_file():
        raise ValueError("Project maps need code-flow's shared renderer. Supply its installed --code-flow-root.")
    sys.path.insert(0, str(root / "scripts"))
    import author
    import s2s
    if s2s.SKILL != root:
        raise ValueError("Another code-flow installation is loaded; use a fresh process.")
    return s2s, author


def validate_atlas(data, s2s):
    s2s.validate(data)
    if data["layer"] != "atlas" or data["subject"]["kind"] != "project":
        raise ValueError("A project map must use the atlas layer and project subject kind.")
    nodes = {n["id"]: n for n in data["nodes"]}
    evidence = {e["id"]: e for e in data["evidence"]}
    for subject in data["subjects"]:
        if "scope" not in subject:
            raise ValueError("Map capabilities need their resolved targets, scope, question and evidence.")
        if nodes[subject["nodeId"]]["contextOnly"]:
            raise ValueError("A capability must belong to a source-backed component.")
        for target in subject["targets"]:
            if "file" in target and (not s2s.relative_path(target["file"]) or ".." in Path(target["file"]).parts):
                raise ValueError("A map capability needs a resolved target file inside the source root.")
        if not any(evidence[e]["kind"] in ("code", "config") for e in subject["evidenceIds"]):
            raise ValueError("Resolve capability entry locations in source code or configuration.")
    return data


def draft(source_root, code_flow_root=None, **options):
    s2s, author = companion(code_flow_root)
    result = author.draft(source_root, kind="project", **options)
    result["layer"] = "atlas"
    result["structureEntries"] = []
    result["regeneration"]["command"] = result["regeneration"]["command"].replace("$code-flow ", "$codebase-atlas ", 1)
    return validate_atlas(result, s2s)


def relative_url(target, origin):
    return quote(Path(os.path.relpath(target, origin.parent)).as_posix(), safe="/")


def generation_request(subject, language, atlas_url=None, locations=()):
    # This is a host request to copy, never a shell command to execute.
    text = "$code-flow " + subject["question"]
    text += " | subject=" + subject["id"] + " | language=" + language
    text += " | targets=" + json.dumps(subject["targets"], ensure_ascii=False, separators=(",", ":"))
    text += " | scope=" + json.dumps(subject["scope"], ensure_ascii=False, separators=(",", ":"))
    if locations:
        text += " | locations=" + json.dumps(list(locations), ensure_ascii=False, separators=(",", ":"))
    if atlas_url:
        text += " | atlas=" + atlas_url
    return text


def load_primer(root=None):
    root = Path(root).resolve() if root else SKILL.parent / "visual-primer"
    path = root / "scripts/rules.py"
    if not path.is_file():
        raise ValueError("Requested rules pages need visual-primer. Supply --visual-primer-root.")
    spec = importlib.util.spec_from_file_location("atlas_primer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_outputs(outputs):
    staged = []
    try:
        for path, text in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=".s2s-", delete=False) as stream:
                staged.append((Path(stream.name), path))
                stream.write(text)
        for temporary, destination in staged:
            temporary.replace(destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def internal_directory(output, internal_dir=None):
    output = Path(output).resolve()
    return Path(internal_dir).resolve() if internal_dir is not None else output.parent / "_internal" / output.stem


def graph_identity(graph):
    return (graph["snapshot"]["repository"], graph["layer"], graph["language"],
            {key: graph["subject"][key] for key in ("id", "kind", "module", "targets", "scope")})


def read_manifest(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError("The pages manifest must be a list of explicitly requested pages.")
    for entry in manifest:
        if not isinstance(entry, dict) or not {"behavior", "output"} <= entry.keys() or entry.keys() - {"behavior", "output", "logic", "layout", "logicOutput"}:
            raise ValueError("Each page needs behavior and output, optionally logic, layout and logicOutput together.")
        if any(k in entry for k in ("logic", "layout", "logicOutput")) and not all(k in entry for k in ("logic", "layout", "logicOutput")):
            raise ValueError("Supply logic, layout and logicOutput together.")
        if any(not isinstance(value, str) or not value.strip() for value in entry.values()):
            raise ValueError("Page manifest paths must be nonempty strings.")
    return manifest


def preserve_inputs(graphs, layouts, pages, output, root, s2s):
    """Prepare reusable, unpruned inputs; never load saved pages for rendering implicitly."""
    saved = {}

    def private_path(value):
        path = (root / value).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Saved authoring inputs must remain inside the internal directory.")
        return path

    def check_graph(path, graph):
        if path.exists():
            previous = s2s.validate(json.loads(path.read_text(encoding="utf-8")))
            if graph_identity(previous) != graph_identity(graph):
                raise ValueError("The internal JSON belongs to another repository, subject, scope, or language. Choose another internal directory.")

    atlas_path = private_path("atlas.internal.json")
    manifest_path = private_path("pages.json")
    if atlas_path == manifest_path:
        raise ValueError("Saved authoring files need distinct paths.")
    check_graph(atlas_path, graphs[output])
    if manifest_path.exists():
        if not atlas_path.exists():
            raise ValueError("An existing pages manifest needs its owning atlas.internal.json.")
        for entry in read_manifest(manifest_path):
            destination = (output.parent / entry["output"]).resolve()
            if destination in saved:
                raise ValueError("Saved pages must have distinct behavior outputs.")
            for key in ("behavior", "logic", "layout"):
                if key in entry:
                    private_path(entry[key])
            saved[destination] = entry

    # Graphs still contain evidence anchors and unpruned claims, unlike render JSON.
    documents = {atlas_path: graphs[output]}
    for item in pages:
        destination = Path(item["output"]).resolve()
        graph = graphs[destination]
        # Prefix Windows device names (e.g. CON); escape any schema-accepted control characters.
        key = "detail-" + quote(graph["subject"]["id"], safe="")
        entry = dict(saved.get(destination, {}))
        entry.update({"behavior": f"{key}.behavior.internal.json",
                      "output": Path(os.path.relpath(destination, output.parent)).as_posix()})
        entries = [(entry["behavior"], graph)]
        if "logic" in item:
            logic_path = Path(item["logicOutput"]).resolve()
            entry.update({"logic": f"{key}.logic.internal.json", "layout": f"{key}.layout.json",
                          "logicOutput": Path(os.path.relpath(logic_path, output.parent)).as_posix()})
            entries.extend(((entry["logic"], graphs[logic_path]), (entry["layout"], layouts[logic_path])))
        for name, document in entries:
            path = private_path(name)
            if path in documents or path == manifest_path:
                raise ValueError("Saved authoring files need distinct paths.")
            if "layer" in document:
                check_graph(path, document)
            elif path.exists() and name != saved.get(destination, {}).get("layout"):
                if json.loads(path.read_text(encoding="utf-8")) != document:
                    raise ValueError("An unrelated layout already exists in the internal directory.")
            documents[path] = document
        saved[destination] = entry
    documents[manifest_path] = list(saved.values())
    retained = {private_path(entry[key]) for entry in saved.values()
                for key in ("behavior", "logic", "layout") if key in entry}
    return documents, retained


def build_site(data, source_root, output, pages=(), data_output=None, code_flow_root=None, visual_primer_root=None,
               internal_dir=None):
    """pages contains explicitly supplied internal graphs, never discovery requests."""
    s2s, author = companion(code_flow_root)
    validate_atlas(data, s2s)
    output = Path(output).resolve()
    pages = list(pages)
    internal = internal_directory(output, internal_dir)
    atlas = copy.deepcopy(data)
    catalog = {s["id"]: s for s in atlas["subjects"]}
    graphs, layouts = {output: atlas}, {}
    primer = None

    def reserve(path, graph):
        path = Path(path).resolve()
        if path in graphs or (data_output and path == Path(data_output).resolve()):
            raise ValueError("Map, detail HTML and render JSON need distinct output paths.")
        graphs[path] = graph
        return path

    for item in pages:
        behavior = copy.deepcopy(item["behavior"])
        s2s.validate(behavior)
        subject = catalog.get(behavior["subject"]["id"])
        if behavior["layer"] != "behavior" or subject is None or not s2s.subject_matches(subject, behavior["subject"]):
            raise ValueError("The requested detail must match a catalog capability's target and scope.")
        if behavior["snapshot"]["repository"] != atlas["snapshot"]["repository"] or behavior["language"] != atlas["language"]:
            raise ValueError("Map and detail must use the same repository and language.")
        destination = reserve(item["output"], behavior)
        listed = (output.parent / unquote(urlsplit(subject["link"]["url"]).path)).resolve()
        if destination != listed:
            raise ValueError("The child output must match its catalog URL.")
        behavior["links"]["atlas"] = {"url": relative_url(output, destination), "generated": False,
                                        "command": atlas["regeneration"]["command"]}
        if "logic" in item:
            primer = primer or load_primer(visual_primer_root)
            logic = copy.deepcopy(item["logic"])
            primer.validate_shared(behavior, logic, s2s)
            primer.validate_layout(item["layout"], logic, s2s)
            added = {r["id"] for r in logic["rules"]} - {r["id"] for r in behavior["rules"]}
            if not added <= {r for section in item["layout"]["sections"] for r in section["ruleIds"]}:
                raise ValueError("Every new rule must appear in the explanation.")
            logic_path = reserve(item["logicOutput"], logic)
            logic["links"]["atlas"] = {"url": relative_url(output, logic_path), "generated": False,
                                         "command": atlas["regeneration"]["command"]}
            for source, target, origin, kind in ((behavior, logic_path, destination, "logic"), (logic, destination, logic_path, "behavior")):
                source["links"][kind] = {"url": relative_url(target, origin), "generated": False,
                                         "command": generation_request(subject, atlas["language"]) + (" --explain" if kind == "logic" else "")}
            layouts[logic_path] = item["layout"]

    if data_output and Path(data_output).resolve() in graphs:
        raise ValueError("Map, detail HTML and render JSON need distinct output paths.")
    for subject in atlas["subjects"]:
        locations = [{k: e[k] for k in ("file", "symbolOrKey", "startLine", "endLine")}
                     for e in atlas["evidence"] if e["id"] in subject["evidenceIds"]]
        subject["link"]["command"] = generation_request(subject, atlas["language"], output.name, locations)
    # Prepare every requested page before resolving links or writing any file.
    initial = {path: author.prepare_build(graph, source_root, path) for path, graph in graphs.items()}
    prepared = {path: author.prepare_build(graph, source_root, path, linked_pages=initial) for path, graph in graphs.items()}
    for path, graph in prepared.items():
        if path != output and not graph["links"]["atlas"]["generated"]:
            raise ValueError("The map and requested detail could not establish matching source evidence.")
    # The overview reuses each exact capability's checked public graph. Shared
    # owners and neighboring components never become an invented feature trace.
    if "composition" in atlas:
        previews = []
        for subject in prepared[output]["subjects"]:
            if not subject["link"]["generated"]:
                continue
            path = (output.parent / unquote(urlsplit(subject["link"]["url"]).path)).resolve()
            child = prepared.get(path)
            if child is None:
                child = s2s.read_embedded(path)
            s2s.validate(child, "render")
            if (child["layer"] == "behavior" and s2s.subject_matches(subject, child["subject"])
                    and s2s.source_matches(prepared[output], child, source_root)):
                previews.append(copy.deepcopy(child))
        prepared[output]["featureDetails"] = previews
    outputs = {}
    for path, graph in prepared.items():
        outputs[path] = (primer.render_rules(graph, layouts[path], s2s, original=graphs[path])[0]
                         if path in layouts else s2s.render(graph))
    if data_output:
        outputs[Path(data_output).resolve()] = json.dumps(prepared[output], ensure_ascii=False, indent=2) + "\n"
    documents, retained = preserve_inputs(graphs, layouts, pages, output, internal, s2s)
    if any(path.is_relative_to(internal) for path in graphs):
        raise ValueError("Keep HTML outside the private internal directory.")
    if outputs.keys() & (documents.keys() | retained):
        raise ValueError("Keep HTML, render JSON and saved authoring inputs at distinct paths.")
    outputs.update({path: json.dumps(document, ensure_ascii=False, indent=2) + "\n"
                    for path, document in documents.items()})
    write_outputs(outputs)
    return prepared


def read_pages(path, output):
    manifest = read_manifest(path)
    pages, inputs = [], {path.resolve()}
    for entry in manifest:
        page = {}
        for key, value in entry.items():
            resolved = (output.parent / value if key in ("output", "logicOutput") else path.parent / value).resolve()
            if key in ("output", "logicOutput"):
                page[key] = resolved
            else:
                inputs.add(resolved)
                page[key] = json.loads(resolved.read_text(encoding="utf-8"))
        pages.append(page)
    return pages, inputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-flow-root", type=Path)
    parser.add_argument("--visual-primer-root", type=Path)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("doctor")
    init = commands.add_parser("init")
    for name in ("question", "title", "module", "target"):
        init.add_argument("--" + name, required=True)
    init.add_argument("--include", dest="includes", action="append", required=True)
    init.add_argument("--exclude", dest="excludes", action="append", default=[])
    init.add_argument("--profile", dest="profiles", action="append", required=True)
    init.add_argument("--language", default="ko")
    init.add_argument("--repository")
    build = commands.add_parser("build")
    build.add_argument("input", type=Path)
    build.add_argument("--pages", type=Path)
    build.add_argument("--data-output", type=Path)
    build.add_argument("--internal-dir", type=Path,
                       help="Retained authoring JSON directory (default: HTML directory/_internal/HTML stem)")
    for command in (init, build):
        command.add_argument("--source-root", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
    args = vars(parser.parse_args(argv))
    action = args.pop("action")
    try:
        s2s, author = companion(args.get("code_flow_root"))
        if action == "doctor":
            author.doctor()
            for name in ("SKILL.md", "references/discovery.md", "references/assembly.md"):
                if not (SKILL / name).is_file():
                    raise ValueError("Missing atlas resource: " + name)
            print("Atlas and shared renderer resources present; source discovery is performed by the host.")
        elif action == "init":
            output = args.pop("output")
            args.pop("visual_primer_root")
            result = draft(**args)
            author.write_json(output, result, exclusive=True)
            print(result["subject"]["id"])
        else:
            input_path, pages_path = args.pop("input"), args.pop("pages")
            pages, inputs = read_pages(pages_path, args["output"]) if pages_path else ([], set())
            inputs.add(input_path.resolve())
            outputs = {args["output"].resolve(), *([args["data_output"].resolve()] if args["data_output"] else [])}
            outputs.update(p[k] for p in pages for k in ("output", "logicOutput") if k in p)
            if outputs & inputs:
                raise ValueError("Keep internal evidence, layout and page manifests separate from outputs.")
            result = build_site(json.loads(input_path.read_text(encoding="utf-8")), pages=pages, **args)
            print(f"{args['output']}: {len(result)} requested pages; {len(result[args['output'].resolve()]['subjects'])} catalog capabilities")
            print(f"Authoring inputs (private; do not publish): {internal_directory(args['output'], args['internal_dir'])}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"atlas: {error}\n")


if __name__ == "__main__":
    main()

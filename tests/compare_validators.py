"""Optional migration audit; jsonschema is a development-only dependency.

Run with --upstream PATH before migration to compare an unmodified fastjsonschema
checkout. Without it, compare the installed adapter. No result files are written.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from validation_cases import atlas_graph, graph, layout, mutations, render_graph
from authored_cases import story_case

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path)
    args = parser.parse_args()
    if args.upstream:
        sys.path.insert(0, str(args.upstream))
        import fastjsonschema
    else:
        import schema_validation

    cases = [("internal", ROOT / "skills/code-flow/references/ir-internal-v0.1.0.schema.json", graph()),
             ("atlas", ROOT / "skills/code-flow/references/ir-internal-v0.1.0.schema.json", atlas_graph()),
             ("render", ROOT / "skills/code-flow/references/ir-render-v0.1.0.schema.json", render_graph())]
    structure = atlas_graph()
    structure["structureEntries"] = story_case()[0]["structureEntries"]
    structure_render = render_graph()
    structure_render["layer"] = "atlas"
    structure_render["structureEntries"] = [
        {**deepcopy(entry), "displayStatus": "confirmed"} for entry in structure["structureEntries"]]
    cases += [
        ("atlas-structure", ROOT / "skills/code-flow/references/ir-internal-v0.1.0.schema.json", structure),
        ("atlas-structure-render", ROOT / "skills/code-flow/references/ir-render-v0.1.0.schema.json", structure_render),
    ]
    cases += [("layout-" + kind, ROOT / "skills/visual-primer/references/rule-layout.schema.json", layout(kind))
              for kind in ("conditions", "comparison", "states")]
    totals, differences, intentional = Counter(), Counter(), Counter()
    examples = []
    for stage, path, original in cases:
        contract = json.loads(path.read_text(encoding="utf-8"))
        reference = Draft202012Validator(contract, format_checker=FormatChecker())
        reference.validate(original)
        candidate = fastjsonschema.compile(contract, use_default=False, fast_fail=False) if args.upstream else None
        for label, data in mutations(original):
            errors = list(reference.iter_errors(data))
            if not stage.startswith("layout-"):
                errors.sort(key=lambda e: str(list(e.path)))
            old = tuple(errors[0].path) if errors else None
            try:
                if candidate:
                    candidate(deepcopy(data))
                else:
                    schema_validation.validate(data, contract, stage)
                new = None
            except Exception as error:
                if args.upstream:
                    errors_new = getattr(error, "errors", [error])
                    try:
                        paths = []
                        for e in errors_new:
                            location, current = [], data
                            for part in e.path[1:]:
                                key = int(part) if isinstance(current, list) else part
                                location.append(key)
                                current = current[key]
                            paths.append(tuple(location))
                        new = min(paths, key=lambda p: str(list(p)))
                    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
                        new = ("UNEXPECTED", type(error).__name__)
                elif isinstance(error, schema_validation.InvalidSchemaData):
                    new = error.path
                else:
                    raise
            totals[stage] += 1
            if old != new:
                # The old optional date-time checker may be absent even when
                # jsonschema itself is installed. The new runtime always checks it.
                if not args.upstream and old is None and new == ("snapshot", "generatedAt"):
                    value = data["snapshot"]["generatedAt"]
                    missing_checker = "date-time" not in FormatChecker.checkers
                    legacy_newline = (isinstance(value, str) and value.endswith("\n")
                                      and schema_validation.date_time(value[:-1]))
                    if not schema_validation.date_time(value) and (missing_checker or legacy_newline):
                        intentional["date-time enforcement"] += 1
                        continue
                if (not args.upstream and stage.startswith("layout-") and old is not None
                        and new == min((tuple(e.path) for e in errors), key=lambda p: str(list(p)))):
                    intentional["layout error ordering"] += 1
                    continue
                kind = "verdict" if (old is None) != (new is None) else "path"
                differences[kind] += 1
                if len(examples) < 20:
                    examples.append({"stage": stage, "case": label, "old": old, "new": new})
    print(json.dumps({"cases": totals, "differences": differences, "intentionalDifferences": intentional,
                      "examples": examples,
                      "referenceDateTimeChecker": "date-time" in FormatChecker.checkers}, indent=2))
    return bool(differences)


if __name__ == "__main__":
    sys.exit(main())

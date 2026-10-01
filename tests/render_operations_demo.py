#!/usr/bin/env python3
"""Render bilingual semantic-operation fixtures into a new QA directory."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys

from operation_cases import SOURCE, operation_case

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import s2s


def render_arrow_fixture(data, source, folder, language):
    """Presentation-only relationships exercise every line and review state."""
    arrows = deepcopy(data)
    # Repeating the caption makes a missing relationship label visible: color
    # alone must not be the reader's only way to distinguish these connections.
    for edge in arrows["edges"]:
        edge["label"] = "주문 처리" if language == "ko" else "Process order"
    for edge, kind in zip(arrows["edges"], ("invokes", "passes-data", "depends-on", "writes", "registers")):
        edge["type"] = kind
    arrows["edges"][3].update(supportStatus="uncertain", confidence="inferred")
    missing = deepcopy(arrows["evidence"][4])
    missing.update(id="ev-arrow-unverified", file="not-recorded.py")
    arrows["evidence"].append(missing)
    arrows["edges"][4]["evidenceIds"] = [missing["id"]]
    for index in (3, 4):
        step = arrows["scenarios"][0]["steps"][index]
        step["evidenceIds"] = deepcopy(arrows["edges"][index]["evidenceIds"])
        if index == 3:
            step.update(supportStatus="uncertain", confidence="inferred")
    (folder / "arrows.html").write_text(s2s.render(s2s.prepare(arrows, source)), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = root / "synthetic-source"
    source.mkdir()
    (source / "operations.py").write_text(SOURCE, encoding="utf-8")
    for language in ("ko", "en"):
        folder = root / language
        folder.mkdir()
        data = operation_case(language)
        (folder / "operations.html").write_text(s2s.render(s2s.prepare(data, source)), encoding="utf-8")
        legacy = deepcopy(data)
        for node in legacy["nodes"]:
            node.pop("operation")
        (folder / "legacy.html").write_text(s2s.render(s2s.prepare(legacy, source)), encoding="utf-8")
        uncertain = deepcopy(data)
        uncertain["nodes"][3].update(supportStatus="uncertain", confidence="inferred")
        (folder / "uncertain.html").write_text(s2s.render(s2s.prepare(uncertain, source)), encoding="utf-8")
        render_arrow_fixture(data, source, folder, language)
        print(folder / "operations.html")


if __name__ == "__main__":
    main()

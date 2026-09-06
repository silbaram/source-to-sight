"""Validate and render checked-in M1 agent readings; no model or target execution."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import author
import s2s


def build():
    sources = {s["id"]: s for s in json.loads((ROOT / "eval/m1/sources.json").read_text())}
    cases = json.loads((ROOT / "eval/m1/cases.json").read_text())
    results = []
    for case in cases:
        source = sources[case["source"]]
        root = ROOT / ".cache/m1-sources" / source["id"]
        data = json.loads((ROOT / "eval/m1" / case["graph"]).read_text())
        observed = author.snapshot(root)
        if observed["commit"] != source["commit"] or observed["workingTreeClean"] is not True:
            raise ValueError(f"The evaluation checkout must be clean at its pinned commit: {source['id']}")
        if data["snapshot"]["repository"] != source["repository"] or data["snapshot"]["commit"] != source["commit"]:
            raise ValueError(f"Case/source identity mismatch: {case['id']}")
        if data["subject"]["question"] != case["question"] or data["analysis"]["profiles"] != case["profiles"]:
            raise ValueError(f"Case question/profile mismatch: {case['id']}")
        output = ROOT / "build/m1" / case["output"]
        rendered = author.build(data, root, output, output.with_suffix(".render.json"))
        if any(e["locationStatus"] != "passed" for e in rendered["evidence"]):
            raise ValueError(f"M1 evidence failed: {case['id']}")
        page = output.read_text()
        if "anchorText" in page or any(e["anchorText"] in page for e in data["evidence"]):
            raise ValueError(f"An internal source anchor reached the page: {case['id']}")
        results.append({"id": case["id"], "status": rendered["analysis"]["status"],
                        "nodes": len(rendered["nodes"]), "evidence": len(rendered["evidence"]),
                        "claims": len(list(s2s.claims(rendered))), "humanReviewed": rendered["provenance"]["humanReviewed"]})
    if not set(author.PROFILES) <= {p for c in cases for p in c["profiles"]}:
        raise ValueError("The M1 cases do not cover all six initial profiles.")
    if len({c["source"] for c in cases}) < 4 or len({c["language"] for c in cases}) < 3:
        raise ValueError("M1 needs at least four repositories and three source languages.")
    author.write_json(ROOT / "build/m1/verification.json", results)
    for result in results:
        print(f"{result['id']}: {result['status']}; {result['evidence']} locations verified; humanReviewed={result['humanReviewed']}")


if __name__ == "__main__":
    build()

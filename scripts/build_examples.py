"""Render all checked-in fixtures; no source discovery or network requests."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"skills/code-flow/scripts"))
from s2s import prepare,render


def build():
    repositories={s["repository"]:s["id"] for s in json.loads((ROOT/"fixtures/source-repositories.json").read_text())}
    output=ROOT/"build/examples";output.mkdir(parents=True,exist_ok=True)
    fixtures=[(p,json.loads(p.read_text())) for p in sorted((ROOT/"fixtures").glob("*.json"))
              if p.name!="source-repositories.json"]
    # The second pass bakes the now-existing sibling links into each page.
    for _ in range(2):
        for path,data in fixtures:
            repo_id=repositories.get(data["snapshot"]["repository"])
            source_root=ROOT/".cache/sources"/repo_id if repo_id else ROOT
            if not source_root.exists():
                raise SystemExit("Fetch the pinned fixture sources first: python3 scripts/fetch_fixture_sources.py")
            target=output/(path.stem+".html")
            prepared=prepare(data,source_root,target)
            target.write_text(render(prepared),encoding="utf-8")
    print(f"Rendered {len(fixtures)} offline pages into {output}")


if __name__=="__main__":
    build()

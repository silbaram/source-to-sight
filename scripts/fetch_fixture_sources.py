"""Fetch only the pinned public source files needed for M0 evidence checks."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    for source in json.loads((ROOT / "fixtures/source-repositories.json").read_text()):
        for name in source["files"]:
            target = ROOT / ".cache/sources" / source["id"] / name
            url = f"https://raw.githubusercontent.com/{source['repository']}/{source['commit']}/{name}"
            content = urlopen(url, timeout=30).read()
            # Fixtures contain hashes captured during the original source review.
            expected = {e["contentHash"] for fixture in (ROOT / "fixtures").glob("*.json")
                        if fixture.name != "source-repositories.json"
                        for graph in [json.loads(fixture.read_text())]
                        if graph["snapshot"]["repository"] == source["repository"]
                        for e in graph["evidence"] if e["file"] == name}
            if expected and expected != {hashlib.sha256(content).hexdigest()}:
                raise SystemExit(f"Pinned file hash mismatch: {url}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        print(f"Fetched {source['repository']} @ {source['commit'][:12]}")

"""Fetch immutable, read-only evaluation checkouts; never run their project code."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def optional_git(root, *args):
    """Git uses exit 1 for an absent ref/config key; other failures are errors."""
    try:
        return git(root, *args)
    except subprocess.CalledProcessError as error:
        if error.returncode != 1:
            raise
        return None


def fetch(source):
    target = ROOT / ".cache/m1-sources" / source["id"]
    target.mkdir(parents=True, exist_ok=True)
    if not (target / ".git").exists():
        if any(target.iterdir()):
            raise ValueError(f"Leave the nonempty directory untouched: {target}")
        git(target, "init", "--quiet")

    head = optional_git(target, "rev-parse", "--verify", "--quiet", "HEAD")
    if head is not None:
        if head != source["commit"] or git(target, "status", "--porcelain"):
            raise ValueError(f"Leave the existing checkout untouched: {target} is changed or at another commit.")
    else:
        # A failed fetch leaves an unborn repository. Resume only an empty
        # worktree with the expected origin, including failure just after init.
        if git(target, "status", "--porcelain", "--untracked-files=all", "--ignored"):
            raise ValueError(f"Leave the unfinished checkout with local files untouched: {target}")
        expected = f"https://github.com/{source['repository']}.git"
        remote = optional_git(target, "config", "--get", "remote.origin.url")
        if remote is not None and remote != expected:
            raise ValueError(f"Leave the checkout with another origin untouched: {target}")
        if remote is None:
            git(target, "remote", "add", "origin", expected)
        git(target, "fetch", "--quiet", "--depth=1", "origin", source["commit"])
        git(target, "checkout", "--quiet", "--detach", source["commit"])
    if git(target, "rev-parse", "HEAD") != source["commit"]:
        raise ValueError(f"The checkout does not match the requested commit: {target}")
    print(f"{source['id']}: {source['commit']}", flush=True)


if __name__ == "__main__":
    for source in json.loads((ROOT / "eval/m1/sources.json").read_text()):
        fetch(source)

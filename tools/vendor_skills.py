#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Vendor each family skill directory wholesale, at a pinned commit.

``skills/vendored.json`` is the pin and the receipt: per skill the repository, the commit its directory was copied
from, that directory's path, and every copied file with its sha256. This script is the only writer of the vendored
tree — it reads the pin (``<repo>@<commit>`` on the command line re-pins one repository), copies ``skills/<name>/``
at that commit file for file, deletes what the commit no longer carries, and rewrites the manifest and
``skills/index.json``, whose description and allowed_tools are read back out of the copied SKILL.md. Re-running it
is a no-op; a hand-copied or half-copied tree fails ``--check``, and the same check runs in the repository's tests.

A source is a git checkout: ``$LOOMGROUND_SKILLS_ROOT/<repo>`` (the variable the parity tests and CI already use),
else a sibling checkout, else — only with ``--fetch`` — a temporary fetch of github.com/flxk1/<repo> at the pin.

    python3 tools/vendor_skills.py                       every skill, at the commit the manifest pins
    python3 tools/vendor_skills.py loomground-solver     one repository
    python3 tools/vendor_skills.py a2a-compliance@<sha>  re-pin one repository, then vendor it
    python3 tools/vendor_skills.py --check               writes nothing; exit 1 on any drift or incompleteness
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "src" / "loomground_mcp" / "skills"
MANIFEST_NAME = "vendored.json"
INDEX_NAME = "index.json"
GITHUB = "https://github.com/flxk1"
# a repository whose local checkout is not named after it
ALIASES = {"loomground": ["loomground-repos/Loomground Core"], "loomground-topos": ["legal-topology-grammar"]}
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")  # the Agent Skills name rule
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
# skills_lint's rule (flxk1/repo-standards tools/skills_lint.py): a relative path a body references must exist
REL_PATH = re.compile(r"(?<![\w/.$])((?:references|scripts|assets|docs)/[A-Za-z0-9_./-]+)")

sys.path.insert(0, str(ROOT / "src"))
from loomground_mcp.tools.skills import frontmatter_fields  # noqa: E402


class Fail(Exception):
    pass


def dumps(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def manifest(skills: Path = SKILLS) -> dict:
    return load(skills / MANIFEST_NAME)


def source_path(name: str) -> str:
    return f"skills/{name}"


def checkouts(repo: str):
    bases = [Path(b) for b in (os.environ.get("LOOMGROUND_SKILLS_ROOT"), ROOT.parent, ROOT.parent.parent) if b]
    for base in bases:
        for rel in [repo, *ALIASES.get(repo, []), f"loomground-repos/{repo}"]:
            yield base / rel


def git(checkout: Path, *args: str) -> bytes:
    r = subprocess.run(["git", "-C", str(checkout), *args], capture_output=True)
    if r.returncode != 0:
        raise Fail(f"git {' '.join(args)} in {checkout}: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout


def has_commit(checkout: Path, commit: str) -> bool:
    return subprocess.run(["git", "-C", str(checkout), "cat-file", "-e", f"{commit}^{{commit}}"],
                          capture_output=True).returncode == 0


def fetch(repo: str, commit: str, into: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(into)], check=True, capture_output=True)
    r = subprocess.run(["git", "-C", str(into), "fetch", "-q", "--depth", "1", f"{GITHUB}/{repo}", commit],
                       capture_output=True)
    if r.returncode != 0:
        raise Fail(f"cannot fetch {repo}@{commit[:7]}: {r.stderr.decode(errors='replace').strip()}")
    return into


def resolve(repo: str, commit: str, allow_fetch: bool, tmp: Path) -> Path:
    if not REPO_RE.match(repo):
        raise Fail(f"repository name not [A-Za-z0-9._-]: {repo!r}")
    if not SHA_RE.match(commit):
        raise Fail(f"{repo}: commit is not a 40-hex sha: {commit!r}")
    for co in checkouts(repo):
        if (co / ".git").exists() and has_commit(co, commit):
            return co
    if allow_fetch:
        return fetch(repo, commit, tmp / repo)
    raise Fail(f"{repo}@{commit[:7]} in no reachable checkout; set LOOMGROUND_SKILLS_ROOT or pass --fetch")


def tree(checkout: Path, commit: str, path: str) -> dict[str, tuple[str, str]]:
    out = git(checkout, "ls-tree", "-r", "-z", commit, "--", f"{path}/")
    files: dict[str, tuple[str, str]] = {}
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, _kind, sha = meta.decode().split()
        files[name.decode()[len(path) + 1:]] = (mode, sha)
    return files


def skill_dir(skills: Path, repo: str, name: str) -> Path:
    """Where a record's files live — a manifest record never names anything outside the vendored tree."""
    if not REPO_RE.match(repo) or not NAME_RE.match(name):
        raise Fail(f"manifest record names {repo!r}/{name!r}; repo is [A-Za-z0-9._-], name is [a-z0-9-]")
    return skills / repo / name


def target(dest: Path, rel: str) -> Path:
    p = (dest / rel).resolve()
    if not str(p).startswith(str(dest.resolve()) + os.sep) or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise Fail(f"refusing to write outside the skill directory: {rel!r}")
    return p


def prune(dest: Path, keep: set[str]) -> None:
    if not dest.exists():
        return
    for p in sorted(dest.rglob("*"), reverse=True):
        if p.is_file() and str(p.relative_to(dest)) not in keep:
            p.unlink()
        elif p.is_dir() and not any(p.iterdir()):
            p.rmdir()


def copy(checkout: Path, repo: str, name: str, commit: str, dest: Path) -> dict[str, str]:
    files = tree(checkout, commit, source_path(name))
    if "SKILL.md" not in files:
        raise Fail(f"{repo}@{commit[:7]} has no {source_path(name)}/SKILL.md")
    recorded: dict[str, str] = {}
    for rel, (mode, sha) in sorted(files.items()):
        if mode not in ("100644", "100755"):
            raise Fail(f"{repo}/{name}: {rel} is mode {mode}; only regular files are vendored")
        blob = git(checkout, "cat-file", "blob", sha)
        out = target(dest, rel)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        out.chmod(0o755 if mode == "100755" else 0o644)
        recorded[rel] = hashlib.sha256(blob).hexdigest()
    prune(dest, set(recorded))
    return recorded


def record(repo: str, name: str, commit: str, files: dict[str, str], private: bool) -> dict:
    r = {"repo": repo, "name": name, "commit": commit, "source": source_path(name),
         "url": f"{GITHUB}/{repo}/tree/{commit}/{source_path(name)}", "files": files}
    return {**r, "private": True} if private else r


def index_record(repo: str, name: str, commit: str, text: str, private: bool) -> dict:
    fm = frontmatter_fields(text)
    if fm.get("name") != name:
        raise Fail(f"{repo}/{name}: SKILL.md frontmatter names {fm.get('name')!r}")
    path = f"{source_path(name)}/SKILL.md"
    r = {"repo": repo, "name": name, "description": fm.get("description", ""),
         "allowed_tools": fm.get("allowed-tools", "").split(), "commit": commit, "path": path,
         "url": f"{GITHUB}/{repo}/blob/{commit}/{path}"}
    return {**r, "private": True} if private else r


def key(r: dict) -> tuple[str, str]:
    return r["repo"], r["name"]


def vendored_files(dest: Path) -> set[str]:
    """What is in a vendored skill directory, less what an install puts there (pip byte-compiles the scripts)."""
    if not dest.exists():
        return set()
    return {str(p.relative_to(dest)) for p in dest.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def check(skills: Path = SKILLS) -> list[str]:
    """Every finding that says the vendored tree is not what the manifest records, or is incomplete."""
    out: list[str] = []
    records = manifest(skills)["skills"]
    index = {key(e): e for e in load(skills / INDEX_NAME)}
    for r in records:
        repo, name, sid = r["repo"], r["name"], f"{r['repo']}/{r['name']}"
        dest = skill_dir(skills, repo, name)
        entry = index.get((repo, name))
        if entry is None:
            out.append(f"{sid}: vendored but not in {INDEX_NAME}")
        elif entry["commit"] != r["commit"]:
            out.append(f"{sid}: {INDEX_NAME} pins {entry['commit'][:7]}, manifest {r['commit'][:7]}")
        if r.get("private"):
            if dest.exists():
                out.append(f"{sid}: private repository, but a body is vendored")
            continue
        on_disk = vendored_files(dest)
        for rel in sorted(set(r["files"]) - on_disk):
            out.append(f"{sid}: vendored file missing: {rel}")
        for rel in sorted(on_disk - set(r["files"])):
            out.append(f"{sid}: file not in the manifest: {rel}")
        for rel in sorted(set(r["files"]) & on_disk):
            if hashlib.sha256(target(dest, rel).read_bytes()).hexdigest() != r["files"][rel]:
                out.append(f"{sid}: vendored file differs from the manifest: {rel}")
        if "SKILL.md" in on_disk:
            body = (dest / "SKILL.md").read_text(encoding="utf-8", errors="replace").split("\n---\n", 1)[-1]
            for rel in sorted(set(REL_PATH.findall(body))):
                if not (dest / rel.rstrip("/").rstrip(".")).exists() and not (dest / rel.rstrip("/")).exists():
                    out.append(f"{sid}: referenced path missing: {rel}")
    for k in sorted(set(index) - {key(r) for r in records}):
        out.append(f"{k[0]}/{k[1]}: in {INDEX_NAME} but not vendored (run tools/vendor_skills.py)")
    for body in sorted(skills.rglob("SKILL.md")):
        k = body.relative_to(skills).parts[:2]
        if len(k) == 2 and (k[0], k[1]) not in {key(r) for r in records}:
            out.append(f"{k[0]}/{k[1]}: a body no record vendored (delete it, or add it to the manifest)")
    return out


def vendor(targets: dict[str, str], skills: Path, allow_fetch: bool) -> list[str]:
    records = {key(r): r for r in manifest(skills)["skills"]}
    index = {key(e): e for e in load(skills / INDEX_NAME)}
    if set(targets) - {r[0] for r in records}:
        raise Fail(f"not in the manifest: {', '.join(sorted(set(targets) - {r[0] for r in records}))}")
    done = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, r in sorted(records.items()):
            repo, name = k
            if repo not in targets:
                continue
            commit = targets[repo]
            checkout = resolve(repo, commit, allow_fetch, Path(tmp))
            dest = skill_dir(skills, repo, name)
            if r.get("private"):
                files: dict[str, str] = {}
                text = git(checkout, "show", f"{commit}:{source_path(name)}/SKILL.md").decode("utf-8")
            else:
                dest.mkdir(parents=True, exist_ok=True)
                files = copy(checkout, repo, name, commit, dest)
                text = (dest / "SKILL.md").read_text(encoding="utf-8")
            records[k] = record(repo, name, commit, files, bool(r.get("private")))
            index[k] = index_record(repo, name, commit, text, bool(r.get("private")))
            done.append(f"{repo}/{name} @ {commit[:7]}: {len(files)} file(s)")
    (skills / MANIFEST_NAME).write_text(dumps({
        "_": manifest(skills)["_"],
        "skills": [records[k] for k in sorted(records)]}), encoding="utf-8")
    (skills / INDEX_NAME).write_text(dumps([index[k] for k in sorted(index)]), encoding="utf-8")
    return done


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*", metavar="REPO[@COMMIT]", help="default: every repository in the manifest")
    ap.add_argument("--check", action="store_true", help="verify the vendored tree against the manifest; no writes")
    ap.add_argument("--fetch", action="store_true", help="fetch a pinned commit from GitHub when no checkout has it")
    args = ap.parse_args(argv)
    try:
        pinned = {r["repo"]: r["commit"] for r in manifest()["skills"]}
        if args.check:
            findings = check()
            for f in findings:
                print(f"FAIL {f}")
            print(f"{len(pinned)} repositories, {len(manifest()['skills'])} skills, {len(findings)} finding(s)")
            return 1 if findings else 0
        targets = dict(pinned)
        if args.repos:
            targets = {}
            for spec in args.repos:
                repo, _, commit = spec.partition("@")
                if repo not in pinned:
                    raise Fail(f"{repo} is not in the manifest; add a record first")
                targets[repo] = commit or pinned[repo]
        for line in vendor(targets, SKILLS, args.fetch):
            print(line)
        findings = check()
        for f in findings:
            print(f"FAIL {f}")
        return 1 if findings else 0
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

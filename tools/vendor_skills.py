#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Vendor each family skill directory wholesale, at a pinned commit — and the checks this repository runs on itself.

``skills/vendored.json`` is the pin and the receipt: per skill the repository, the commit its directory was copied
from, that directory's path, and every copied file with its sha256. Each skill carries its own pin; a commit given
on the command line re-pins a repository's skills, and nothing else ever rewrites one. This script is the only
writer of the vendored tree — it copies ``skills/<name>/`` at the pinned commit file for file, deletes what the
commit no longer carries, and rewrites the manifest and ``skills/index.json``, whose description and allowed_tools
are read back out of the copied SKILL.md.

Re-running is a no-op. ``--check`` compares the two in both directions — every recorded file present, unaltered
and non-empty, and every file present recorded, walked from the disk so an added one cannot hide — re-derives each
index entry from the vendored body, and applies skills_lint's referenced-path rule. The repository's own tests run
the same check against the installed package, and hold the packaging globs to the same file list.

The manifest's ``tools`` section is the same mechanism pointed at a check rather than a skill: a linter this
repository holds itself to, copied by name out of another repository's ``tools/`` into ``tools/vendored/`` and
hashed the same way. It is vendored rather than fetched because a published product must not take a build input
from a working repository — one that can be renamed, reverted, or made private under it.

A source is a git checkout: ``$LOOMGROUND_SKILLS_ROOT/<repo>`` (the variable the parity tests and CI already use),
else a sibling checkout, else — only with ``--fetch`` — a temporary fetch of github.com/flxk1/<repo> at the pin.
Vendoring is a development act with a commit as its receipt; nothing in a build or a test run fetches anything.

    python3 tools/vendor_skills.py                       every skill and tool, at the commit the manifest pins
    python3 tools/vendor_skills.py loomground-solver     one repository
    python3 tools/vendor_skills.py a2a-compliance@<sha>  re-pin one repository, then vendor it
    python3 tools/vendor_skills.py repo-standards@<sha>  the same, for the vendored check
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
from loomground_mcp.tools.skills import frontmatter_fields, split_frontmatter  # noqa: E402


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


def copy_named(checkout: Path, commit: str, source: str, names, dest: Path, what: str) -> dict[str, str]:
    """Named files out of one directory of a repository — how a vendored tool is taken.

    A skill is copied wholesale, because a body pointing at a file that was left behind is the defect this whole
    mechanism exists for. A tool is not: we consume one check out of a repository of them, and sweeping in its
    siblings would vendor code nothing here runs. So a tool record lists its files, and the check holds the
    directory to exactly that list.
    """
    available = tree(checkout, commit, source)
    recorded: dict[str, str] = {}
    for name in sorted(names):
        if name not in available:
            raise Fail(f"{what}: {source}/{name} is not in {commit[:7]}")
        mode, sha = available[name]
        if mode not in ("100644", "100755"):
            raise Fail(f"{what}: {name} is mode {mode}; only regular files are vendored")
        blob = git(checkout, "cat-file", "blob", sha)
        out = target(dest, name)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        out.chmod(0o755 if mode == "100755" else 0o644)
        recorded[name] = hashlib.sha256(blob).hexdigest()
    prune(dest, set(recorded))
    return recorded


def tool_dest(root: Path, rec: dict) -> Path:
    rel = rec["target"]
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise Fail(f"tool record targets {rel!r}, which is not inside the repository")
    return root / rel


def tool_record(repo: str, commit: str, source: str, target_rel: str, files: dict[str, str]) -> dict:
    return {"repo": repo, "commit": commit, "source": source, "target": target_rel,
            "url": f"{GITHUB}/{repo}/tree/{commit}/{source}", "files": files}


def record(repo: str, name: str, commit: str, files: dict[str, str], private: bool) -> dict:
    r = {"repo": repo, "name": name, "commit": commit, "source": source_path(name),
         "url": f"{GITHUB}/{repo}/tree/{commit}/{source_path(name)}", "files": files}
    return {**r, "private": True} if private else r


def split_allowed_tools(raw: str) -> list[str]:
    """`allowed-tools` as a list: comma- or whitespace-separated, split only at paren depth
    zero, so the comma in `Bash(a:*, b:*)` stays inside its one grant."""
    depth, token, out = 0, [], []
    for ch in raw.strip():
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth:
            depth -= 1
        if depth == 0 and (ch.isspace() or ch == ","):
            if token:
                out.append("".join(token))
                token = []
            continue
        token.append(ch)
    if token:
        out.append("".join(token))
    return out


def index_record(repo: str, name: str, commit: str, text: str, private: bool) -> dict:
    fm = frontmatter_fields(text)
    if fm.get("name") != name:
        raise Fail(f"{repo}/{name}: SKILL.md frontmatter names {fm.get('name')!r}")
    path = f"{source_path(name)}/SKILL.md"
    r = {"repo": repo, "name": name, "description": fm.get("description", ""),
         "allowed_tools": split_allowed_tools(fm.get("allowed-tools", "")), "commit": commit, "path": path,
         "url": f"{GITHUB}/{repo}/blob/{commit}/{path}"}
    return {**r, "private": True} if private else r


def key(r: dict) -> tuple[str, str]:
    return r["repo"], r["name"]


def vendored_files(dest: Path) -> set[str]:
    """What is in a vendored skill directory, less the byte-code an install compiles there."""
    if not dest.exists():
        return set()
    return {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file() and not bytecode(p)}


def bytecode(p: Path) -> bool:
    """`pip install` compiles the vendored scripts in place; the wheel itself must carry none (see pyproject)."""
    return "__pycache__" in p.parts or p.suffix == ".pyc"


def tree_files(skills: Path) -> dict[str, Path]:
    """Everything under skills/ — walked from the disk, not from the manifest, so an *added* file is visible."""
    return {p.relative_to(skills).as_posix(): p for p in skills.rglob("*") if p.is_file() and not bytecode(p)}


def referenced(body: str) -> set[str]:
    _, text = split_frontmatter(body)
    return set(REL_PATH.findall(text))


def check(skills: Path = SKILLS) -> list[str]:
    """Every finding that says the vendored tree is not exactly what the manifest records.

    Both directions: every recorded file is present, unaltered and non-empty, and every file present is recorded —
    a directory holding no SKILL.md is not a hiding place. Per record the index entry is re-derived from the
    vendored SKILL.md and compared whole, so a fabricated description cannot pass, and each relative path the body
    reaches for has to exist and, when it names a file, be one.
    """
    out: list[str] = []
    records = manifest(skills)["skills"]
    index = {key(e): e for e in load(skills / INDEX_NAME)}
    present = tree_files(skills)
    expected: dict[str, tuple[str, str, str]] = {}
    for r in records:
        repo, name, sid = r["repo"], r["name"], f"{r['repo']}/{r['name']}"
        dest = skill_dir(skills, repo, name)
        for rel, sha in r["files"].items():
            target(dest, rel)  # a record never names a path outside its own directory
            expected[f"{repo}/{name}/{rel}"] = (sid, rel, sha)
        entry = index.get((repo, name))
        if entry is None:
            out.append(f"{sid}: vendored but not in {INDEX_NAME}")
        elif entry["commit"] != r["commit"]:
            out.append(f"{sid}: {INDEX_NAME} pins {entry['commit'][:7]}, manifest {r['commit'][:7]}")
        if r.get("private"):
            if dest.exists():
                out.append(f"{sid}: private repository, but a body is vendored")
            continue
        body_file = dest / "SKILL.md"
        if "SKILL.md" not in r["files"] or not body_file.is_file():
            out.append(f"{sid}: no vendored SKILL.md")
            continue
        body = body_file.read_text(encoding="utf-8", errors="replace")
        if entry is not None and entry != index_record(repo, name, r["commit"], body, False):
            out.append(f"{sid}: {INDEX_NAME} record disagrees with the vendored SKILL.md frontmatter")
        for ref in sorted(referenced(body)):
            rel = ref.rstrip(".")
            p = dest / rel.rstrip("/")
            if not p.exists():
                out.append(f"{sid}: referenced path missing: {ref}")
            elif not rel.endswith("/") and Path(rel).suffix and not p.is_file():
                out.append(f"{sid}: referenced path is not a file: {ref}")
    for path, (sid, rel, sha) in sorted(expected.items()):
        p = present.get(path)
        if p is None:
            out.append(f"{sid}: vendored file missing: {rel}")
            continue
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            out.append(f"{sid}: vendored file differs from the manifest: {rel}")
        elif not data:
            out.append(f"{sid}: vendored file is empty: {rel}")
    for path in sorted(set(present) - set(expected) - {MANIFEST_NAME, INDEX_NAME}):
        out.append(f"{path}: under skills/ and no record vendored it")
    for k in sorted(set(index) - {key(r) for r in records}):
        out.append(f"{k[0]}/{k[1]}: in {INDEX_NAME} but not vendored (run tools/vendor_skills.py)")
    return out


def check_tools(root: Path = ROOT, skills: Path = SKILLS) -> list[str]:
    """The vendored tools against their records: present, unaltered, non-empty, and nothing else in the directory.

    Separate from `check` because these live in the repository, not in the package — a check that ships would have
    nothing to look at. It is not conditional: a missing vendored tool is a finding, never a skip.
    """
    out: list[str] = []
    for rec in manifest(skills).get("tools", []):
        repo, commit = rec["repo"], rec["commit"]
        what = f"{repo}@{commit[:7]}"
        if not REPO_RE.match(repo) or not SHA_RE.match(commit):
            out.append(f"{what}: tool record names a repository or commit of the wrong shape")
            continue
        dest = tool_dest(root, rec)
        if rec["url"] != f"{GITHUB}/{repo}/tree/{commit}/{rec['source']}":
            out.append(f"{what}: tool record url does not name its own commit and source")
        present = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file() and not bytecode(p)} \
            if dest.exists() else set()
        for name, sha in sorted(rec["files"].items()):
            p = target(dest, name)
            if name not in present:
                out.append(f"{what}: vendored tool missing: {rec['target']}/{name}")
                continue
            data = p.read_bytes()
            if hashlib.sha256(data).hexdigest() != sha:
                out.append(f"{what}: vendored tool differs from the manifest: {rec['target']}/{name}")
            elif not data:
                out.append(f"{what}: vendored tool is empty: {rec['target']}/{name}")
        for name in sorted(present - set(rec["files"])):
            out.append(f"{what}: {rec['target']}/{name} is vendored and no record vouches for it")
    return out


def vendor_tools(targets: dict[str, str], root: Path, skills: Path, allow_fetch: bool) -> list[str]:
    records = {r["repo"]: r for r in manifest(skills).get("tools", [])}
    done = []
    with tempfile.TemporaryDirectory() as tmp:
        for repo, rec in sorted(records.items()):
            if repo not in targets:
                continue
            commit = targets[repo]
            checkout = resolve(repo, commit, allow_fetch, Path(tmp))
            dest = tool_dest(root, rec)
            dest.mkdir(parents=True, exist_ok=True)
            files = copy_named(checkout, commit, rec["source"], rec["files"], dest, f"{repo}@{commit[:7]}")
            records[repo] = tool_record(repo, commit, rec["source"], rec["target"], files)
            done.append(f"{repo}/{rec['source']} @ {commit[:7]} → {rec['target']}: {len(files)} file(s)")
    if done:
        doc = manifest(skills)
        doc["tools"] = [records[r] for r in sorted(records)]
        (skills / MANIFEST_NAME).write_text(dumps(doc), encoding="utf-8")
    return done


def vendor(targets: dict[tuple[str, str], str], skills: Path, allow_fetch: bool) -> list[str]:
    """Vendor each named skill at the commit `targets` gives it — one entry per skill, never per repository."""
    records = {key(r): r for r in manifest(skills)["skills"]}
    index = {key(e): e for e in load(skills / INDEX_NAME)}
    if set(targets) - set(records):
        raise Fail("not in the manifest: " + ", ".join(f"{r}/{n}" for r, n in sorted(set(targets) - set(records))))
    done = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, r in sorted(records.items()):
            repo, name = k
            if k not in targets:
                continue
            commit = targets[k]
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
    doc = manifest(skills)  # rewrite this section, leave the rest of the manifest as it stands
    doc["skills"] = [records[k] for k in sorted(records)]
    (skills / MANIFEST_NAME).write_text(dumps(doc), encoding="utf-8")
    (skills / INDEX_NAME).write_text(dumps([index[k] for k in sorted(index)]), encoding="utf-8")
    return done


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*", metavar="REPO[@COMMIT]", help="default: every repository in the manifest")
    ap.add_argument("--check", action="store_true", help="verify the vendored tree against the manifest; no writes")
    ap.add_argument("--fetch", action="store_true", help="fetch a pinned commit from GitHub when no checkout has it")
    args = ap.parse_args(argv)
    try:
        records = manifest()["skills"]
        tools = manifest().get("tools", [])
        pinned = {key(r): r["commit"] for r in records}
        tool_pinned = {r["repo"]: r["commit"] for r in tools}
        repos = {r["repo"] for r in records} | set(tool_pinned)

        def report(findings: list[str]) -> int:
            for f in findings:
                print(f"FAIL {f}")
            print(f"{len(repos)} repositories, {len(records)} skills, {len(tools)} vendored tool record(s), "
                  f"{len(findings)} finding(s)")
            return 1 if findings else 0

        if args.check:
            return report(check() + check_tools())
        targets, tool_targets = dict(pinned), dict(tool_pinned)
        if args.repos:
            targets, tool_targets = {}, {}
            for spec in args.repos:
                repo, _, commit = spec.partition("@")
                if repo not in repos:
                    raise Fail(f"{repo} is not in the manifest; add a record first")
                # no commit given: each skill keeps its own pin. One given: it re-pins that repository's skills.
                targets.update({k: commit or pinned[k] for k in pinned if k[0] == repo})
                if repo in tool_pinned:
                    tool_targets[repo] = commit or tool_pinned[repo]
        for repo in sorted({r["repo"] for r in records}):  # a per-skill pin is honoured, and said out loud
            spread = {pinned[k] for k in pinned if k[0] == repo}
            if len(spread) > 1:
                print(f"note: {repo} is pinned per skill at {', '.join(sorted(c[:7] for c in spread))}")
        for line in vendor(targets, SKILLS, args.fetch) + vendor_tools(tool_targets, ROOT, SKILLS, args.fetch):
            print(line)
        return report(check() + check_tools())
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

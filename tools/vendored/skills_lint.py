# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Agent Skills conformance (agentskills.io): one SKILL.md per skill dir.

Checks: frontmatter present; only allowed keys (name, description, license,
allowed-tools, metadata, compatibility, plus governance per skill-governance-block); name = lowercase [a-z0-9-], <= 64,
equals the folder name; description <= 1024 and states when to use it; no
platform-only path roots (${CLAUDE_PLUGIN_ROOT}); every relative path the body
references exists next to SKILL.md. Exit 0 conforms, 1 a finding, 2 the tool
could not decide (no SKILL.md found, or one could not be read/decoded --
reported by name, scan continues, 2 wins over 1). Usage: python3 skills_lint.py <root>... """
from __future__ import annotations
import argparse, os, re, sys
from pathlib import Path

from undecidable import ERROR, code, reason, read_regular, stat_kind

ALLOWED = {"name", "description", "license", "allowed-tools", "metadata", "compatibility",
           "governance"}  # governance: the skill-governance-block binding (flxk1/skill-governance-block); runtimes ignore it
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
WHEN_RE = re.compile(r"\b(use (this )?(skill )?when|when (the )?user|triggers?|use for|use it (to|when)|activates?|should be used when)\b", re.I)
PLATFORM_ROOT = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?|~/\.claude/|\.claude-plugin/")
REL_PATH = re.compile(r"(?<![\w/.$])((?:references|scripts|assets|docs)/[A-Za-z0-9_./-]+)")
SKIP_DIRS = {"node_modules", ".venv", "venv", "work", "_archive", ".git", "__pycache__", ".circle", ".cube"}


def frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if mm:
            key = mm.group(1)
            val = mm.group(2).strip()
            fm[key] = "" if val in (">", ">-", "|", "|-") else val
        elif key and (line.startswith(" ") or line.startswith("\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()   # folded / literal continuation
    return fm


def check(skill: Path) -> list[str]:
    out = []
    text, err = read_regular(skill)  # rejects non-regular files (a FIFO would otherwise
    if err is not None:              # block forever waiting for a writer) and strict-decodes
        return [f"ERROR: {err}"]     # (silently "replace"-d bytes would surface as a wrong
    if text is None:                 # FAIL, not the real reason the check could not run)
        return ["ERROR: not found"]  # listed a moment ago, gone now -- report, don't guess
    fm = frontmatter(text)
    if fm is None:
        return ["no frontmatter"]
    try:  # real YAML parse when a parser is available; the line reader above is the fallback
        import yaml  # type: ignore
        raw = re.match(r"^---\n(.*?)\n---\n", text, re.S).group(1)
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            out.append("frontmatter is not a YAML mapping")
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        out.append(f"frontmatter is not valid YAML: {str(e).splitlines()[0][:80]}")
    for k in fm:
        if k not in ALLOWED:
            out.append(f"key not in standard: {k} (put it under metadata)")
    name = fm.get("name", "")
    if not NAME_RE.match(name):
        out.append(f"name not [a-z0-9-] <= 64: {name!r}")
    if name != skill.parent.name:
        out.append(f"name {name!r} != folder {skill.parent.name!r}")
    desc = fm.get("description", "")
    if not desc:
        out.append("description missing")
    elif len(desc) > 1024:
        out.append(f"description {len(desc)} > 1024")
    elif not WHEN_RE.search(desc):
        out.append("description does not say when to use it")
    body = text.split("\n---\n", 1)[-1]
    if PLATFORM_ROOT.search(body):
        out.append("platform-only path root (${CLAUDE_PLUGIN_ROOT} / ~/.claude / .claude-plugin)")
    for rel in sorted(set(REL_PATH.findall(body))):
        p = skill.parent / rel.rstrip("/").rstrip(".")
        p2 = skill.parent / rel.rstrip("/")
        # a stat-based presence check, not .exists(): same swallow risk as elsewhere.
        # The reason was discarded here before -- a symlink loop or EACCES on an
        # intermediate component stated "missing", a decided and FALSE finding on input
        # the check could not actually inspect. Found via either form: no problem.
        # Neither found, but at least one was genuinely undecidable (not just absent):
        # report that, not a confident "missing" this check never actually confirmed.
        st1, err1 = stat_kind(p)
        st2, err2 = stat_kind(p2)
        if st1 is not None or st2 is not None:
            continue
        if err1 is not None or err2 is not None:
            out.append(f"ERROR: referenced path {rel}: {err1 or err2}")
        else:
            out.append(f"referenced path missing: {rel}")
    return out


def find_skill_md(root: Path, errors: list[str]) -> list[Path]:
    """os.walk, not Path.rglob: rglob's handling of an unreadable directory during traversal
    has changed across Python versions (silently skipped on some, raised on others), which
    made this scan's verdict depend on the interpreter. os.walk's onerror hook is stable."""
    found = []

    def onerr(exc: OSError):
        p = Path(exc.filename) if getattr(exc, "filename", None) else root
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = Path(p.name)
        errors.append(f"ERROR {rel}: {reason(exc)}")

    for dirpath, dirnames, filenames in os.walk(root, onerror=onerr):
        dp = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        # relative to the SCAN ROOT, not the absolute path: a root nested under a
        # directory that happens to be named e.g. "work" must not skip everything below it
        try:
            rel_parts = dp.relative_to(root).parts
        except ValueError:
            rel_parts = dp.parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if "SKILL.md" in filenames:
            found.append(dp / "SKILL.md")
    return found


def _label(s: Path, roots: list[Path]) -> str:
    """Never the absolute path passed in: relative to whichever scan root the skill was
    found under is enough to identify it -- and, with multiple roots now that `roots` is
    nargs="*", prefixed with that root's own name (not its path) so two same-named skill
    folders under two different roots render as two distinguishable findings, not one
    label repeated twice."""
    for r in roots:
        try:
            rel = s.relative_to(r)
        except ValueError:
            continue
        return f"{r.name}/{rel}" if len(roots) > 1 else str(rel)
    return f"{s.parent.name}/SKILL.md"  # unreachable in practice: s always came from some root


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True, description=__doc__)
    ap.add_argument("roots", nargs="*", default=["."])
    a = ap.parse_args(argv)
    errors: list[str] = []
    # the documented primary usage -- what a CI script writes as "$REPO" -- and an unset
    # variable gives an empty positional the SAME way it would an empty --flag elsewhere
    # in this family of tools; Path("") is ".", not "nothing", and must not become a
    # verdict about whatever directory the tool happened to be invoked from
    if "" in a.roots:
        print("ERROR roots: empty"); return ERROR
    roots = [Path(r) for r in a.roots]
    skills = []
    for r in roots:
        skills += find_skill_md(r, errors)
    for e in errors:
        print(e)
    if not skills:
        print("no SKILL.md found"); return ERROR
    bad = 0
    errored = bool(errors)
    for s in sorted(skills):
        try:
            findings = check(s)
        except Exception as ex:  # never a traceback on this path either
            findings = [f"ERROR: {reason(ex)}"]
        if findings:
            bad += 1
            # ANY finding, not just the first: check() can now return a semantic finding
            # (e.g. "description missing") alongside a referenced-path ERROR discovered
            # later in the same pass -- order must not decide the header word
            undecided = any(f.startswith("ERROR:") for f in findings)
            print(f"{'ERROR' if undecided else 'FAIL'} {_label(s, roots)}")
            for f in findings:
                print(f"     - {f}")
                if f.startswith("ERROR:"):
                    errored = True
    print(f"{len(skills) - bad}/{len(skills)} skills conform")
    return code(bad > 0, errored)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 flxk1
"""Generate the machine-derived blocks of skills/loomground/SKILL.md from the canonical
language sources, so the skill grows with the language instead of drifting
from it.

The skill has two layers:
  - hand-written judgment (the procedure, the per-declaration guidance) —
    drift-gated: every declaration in vocabulary/declarations.json MUST have a
    `### <name>` guidance heading, or --check fails naming what is missing;
  - generated facts (nodes, cords, token, verdicts, declarations table,
    well-formedness, litmus, out-of-scope, examples, vector index) — derived
    from vocabulary/*.json, schema/token.schema.json, language-card.json,
    conformance/manifest.json, and examples/*.lg between markers:

        <!-- generated:NAME:begin --> ... <!-- generated:NAME:end -->

Run:  python3 skills/loomground/make_skill.py           # rewrite SKILL.md in place
      python3 skills/loomground/make_skill.py --check   # CI mode: fail on drift or gaps
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = Path(__file__).resolve().with_name("SKILL.md")


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8").rstrip("\n")


def _strip_lg(text):
    """Drop SPDX/copyright comment lines from an embedded .lg example."""
    keep = [ln for ln in text.splitlines()
            if not re.match(r"#\s*(SPDX|Copyright)", ln)]
    return "\n".join(keep).strip("\n")


def build_sections() -> dict[str, str]:
    nodes = _load("vocabulary/node-classes.json")
    cords = _load("vocabulary/cords.json")["permitted"]
    verdicts = _load("vocabulary/verdicts.json")
    decls = _load("vocabulary/declarations.json")
    guard = _load("vocabulary/guard-domain.json")
    grades = _load("vocabulary/grades.json")
    risk = _load("vocabulary/risk.json")
    tok = _load("schema/token.schema.json")
    card = _load("language-card.json")
    man = _load("conformance/manifest.json")

    tok_fields = list(tok["required"]) + [
        p for p in tok["properties"] if p not in tok["required"]]

    s: dict[str, str] = {}

    s["language"] = "\n".join([
        f"- **Nodes ({len(nodes)}):** "
        + " · ".join(f"`{n['class']}` ({n['role']})" for n in nodes),
        f"- **Cords ({len(cords)}):** "
        + " · ".join(f"`{c['type']}` ({c['from']} → {c['to']})" for c in cords),
        "- **Token:** `{" + ", ".join(tok_fields) + "}`; "
        + f"`risk` ∈ {' < '.join(risk['levels'])}; "
        + "`tags` is an optional set of declared categories.",
        "- **Verdicts (join strictest-wins along pipes):** `"
        + "` ⊑ `".join(verdicts["alphabet"])
        + "`. The master releases iff the effective verdict is `auto` and every "
        "egress obligation is attached.",
        f"- **Autonomy grades:** active ladder `{' < '.join(grades['levels'])}` "
        "(policy, remappable); granted on an actor, required on a source gate; "
        "an ungated gate dispositions `auto` — declare a required grade to withhold.",
        "- **Guards** range over exactly `{" + ", ".join(guard["ranges_over"])
        + "}` — never `id`, `provenance`, `grade`, or any computed value.",
    ])

    s["declarations"] = "\n".join(
        ["| Declaration | Form | Effect |", "| --- | --- | --- |"]
        + [f"| {d['name']} | `{d['form']}` | {d['effect']} |" for d in decls])

    s["wellformed"] = "\n".join(f"- {w}" for w in card["well_formedness"])

    s["litmus"] = card["litmus"]

    s["outofscope"] = ("Outside the language (hand off to a host, never force "
                       "into a guard): " + ", ".join(card["out_of_scope"]) + ".")

    s["example"] = "\n".join([
        "A routine drafting gate and a reserving decide gate "
        "(`examples/draft-decide.lg`):",
        "", "```", _strip_lg(_read("examples/draft-decide.lg")), "```", "",
        "A principal chain rooted in a person — the delegator anchors "
        "answerability and confers no authority "
        "(`conformance/vectors/obo-human-root/input.lg`):",
        "", "```", _strip_lg(_read("conformance/vectors/obo-human-root/input.lg")),
        "```",
        "",
        "Both are conformance-tested: the first is a repository example, the "
        "second is a vector input — an invalid example in this skill is "
        "impossible by construction.",
    ])

    kinds: dict[str, int] = {}
    for v in man["vectors"]:
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    s["conformance"] = (
        f"The suite has **{len(man['vectors'])} vectors** ("
        + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
        + "), indexed in `conformance/manifest.json`. When unsure how a "
        "construct projects or which stage rejects it, read the matching "
        "vector: `expected.json` is the canonical observation; `reject.json` "
        "pins the stage.")

    return s


MARK = re.compile(
    r"(<!-- generated:(\w+):begin -->\n)(.*?)(<!-- generated:\2:end -->)",
    re.DOTALL)


def render(text: str, sections: dict[str, str]) -> str:
    seen = set()

    def sub(m):
        name = m.group(2)
        seen.add(name)
        if name not in sections:
            raise SystemExit(f"SKILL.md has unknown generated block {name!r}")
        return m.group(1) + sections[name] + "\n" + m.group(4)

    out = MARK.sub(sub, text)
    missing = set(sections) - seen
    if missing:
        raise SystemExit(f"SKILL.md lacks generated block(s): {sorted(missing)}")
    return out


def coverage_gaps(text: str) -> list[str]:
    decls = [d["name"] for d in _load("vocabulary/declarations.json")]
    return [d for d in decls
            if not re.search(rf"(?m)^###\s+{re.escape(d)}\b", text)]


def main() -> int:
    check = "--check" in sys.argv[1:]
    current = SKILL.read_text(encoding="utf-8")
    rendered = render(current, build_sections())
    gaps = coverage_gaps(rendered)
    if gaps:
        print("skill guidance gap — no `### <declaration>` section for: "
              + ", ".join(gaps))
        return 1
    if check:
        if rendered != current:
            print("skill drift — generated blocks are stale; "
                  "run: python3 skills/loomground/make_skill.py")
            return 1
        print("skill is in lockstep with the language")
        return 0
    SKILL.write_text(rendered, encoding="utf-8")
    print("skill regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

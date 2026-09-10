# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-topos: a statement-level reader for the `.lt` netlist.

Implements ``grammar/topos.ebnf`` (loomground-topos v0.1, main c71f81c) as a parser; the
grammar file is normative, this module only reads. Parse-vs-apply split as in the grammar:
any id parses, ladder/catalogue membership and the §10 invariants are for apply.

Two reader tolerances the examples rely on, both outside the one-line ``line`` rule: an
indented physical line (or an open ``[`` block) continues the statement above it, and a
prop block after a node declaration is kept as ``props`` with a warning.
"""
import re
from typing import Any, Optional

from ._result import tool

PLANE = "loomground-topos"

VERTICAL = ("outranks", "derives-authority-from", "level-contains", "has-primacy-over")
HORIZONTAL = ("co-equal-with", "reviews", "can-veto", "can-override", "appoints", "dissolves",
              "may-refer-to", "must-refer-to")
COUPLING = ("has-primacy-over", "applies-directly-in", "must-be-transposed-by", "confers-competence",
            "has-direct-effect", "may-refer-to", "must-refer-to")
RELATIONS = {name: [cls for cls, names in (("vertical", VERTICAL), ("horizontal", HORIZONTAL), ("coupling", COUPLING))
                    if name in names] for name in (*VERTICAL, *HORIZONTAL, *COUPLING)}

# node class -> attribute keyword -> value kind
DECLS = {
    "system": {"tradition": "id", "powers": "id", "levels": "id", "ranks": "id"},
    "organ": {"system": "id", "level": "id", "powers": "labels", "party": "id"},
    "level": {"system": "id", "rank": "number", "contains": "id"},
    "instrument": {"system": "id", "rank": "rank", "origin": "id", "direct-effect": "effect",
                   "directly-applicable": "flag"},
    "competence": {"system": "id", "allocation": "id", "holder": "id"},
}
FIELDS = {"direct-effect": "direct_effect", "directly-applicable": "directly_applicable"}
EFFECTS = ("none", "vertical", "horizontal")
PROP_VOCAB = {"resolution_mode": ("disapply", "invalidate", "void"),
              "state": ("pending", "transposed", "gap", "partial"),
              "status": ("asserted", "contested")}

_TOKEN = re.compile(r"""\s*(?:(?P<text>"[^"\n]*")|(?P<open_text>")|(?P<comment>\#.*)|(?P<date>\d+-\d+-\d+)
                        |(?P<number>\d+)|(?P<id>[A-Za-z][A-Za-z0-9_:#-]*)|(?P<punct>[\[\]{},=:])|(?P<bad>\S))""", re.X)


class ParseError(Exception):
    def __init__(self, line: int, reason: str):
        super().__init__(f"line {line}: {reason}")
        self.line, self.reason = line, reason


def _lex(line: str, n: int) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    pos = 0
    while pos < len(line):
        m = _TOKEN.match(line, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        kind = m.lastgroup
        if kind is None or kind == "comment":
            break
        if kind == "open_text":
            raise ParseError(n, "unterminated string")
        if kind == "bad":
            raise ParseError(n, f"unexpected character {m.group('bad')!r}")
        value = m.group(kind)
        out.append((kind, value[1:-1] if kind == "text" else value, n))
    return out


def _statements(text: str):
    """Group physical lines into statements: (first line number, tokens, source lines) — or, for a
    line the lexer rejects, (line number, None, reason); that line also ends the statement above it."""
    cur: Optional[list] = None
    depth = 0
    for n, raw in enumerate(text.splitlines(), 1):
        try:
            toks = _lex(raw, n)
        except ParseError as exc:
            if cur:
                yield cur
            cur, depth = None, 0
            yield [n, None, exc.reason]
            continue
        if not toks:
            continue
        continuation = cur is not None and (depth > 0 or raw[0] in " \t")
        if not continuation:
            if cur:
                yield cur
            cur = [n, [], []]
            depth = 0
        cur[1].extend(toks)
        cur[2].append(raw.strip())
        depth += sum(1 for k, v, _ in toks if k == "punct" and v == "[") - sum(1 for k, v, _ in toks if k == "punct" and v == "]")
    if cur:
        yield cur


class _Cursor:
    def __init__(self, tokens: list, line: int):
        self.t, self.i, self.line = tokens, 0, line

    def peek(self) -> Optional[tuple[str, str, int]]:
        return self.t[self.i] if self.i < len(self.t) else None

    def at(self) -> int:
        return self.t[self.i][2] if self.i < len(self.t) else self.t[-1][2]

    def take(self, kind: str, what: str) -> str:
        tok = self.peek()
        if tok is None:
            raise ParseError(self.at(), f"expected {what}, got end of statement")
        if tok[0] != kind:
            raise ParseError(tok[2], f"expected {what}, got {tok[1]!r}")
        self.i += 1
        return tok[1]

    def punct(self, ch: str) -> bool:
        tok = self.peek()
        if tok and tok[0] == "punct" and tok[1] == ch:
            self.i += 1
            return True
        return False

    def done(self) -> bool:
        return self.i >= len(self.t)


def _labels(c: _Cursor) -> list[str]:
    if not c.punct("{"):
        return [c.take("id", "a label")]
    labels = [c.take("id", "a label")]
    while c.punct(","):
        labels.append(c.take("id", "a label"))
    if not c.punct("}"):
        raise ParseError(c.at(), "expected ',' or '}' in label set")
    return labels


def _props(c: _Cursor, warnings: list, line: int) -> dict[str, Any]:
    props: dict[str, Any] = {}
    while True:
        key = c.take("id", "a prop key")
        if not c.punct("="):
            raise ParseError(c.at(), f"expected '=' after prop key {key!r}")
        tok = c.peek()
        if tok is None or tok[0] == "punct":
            raise ParseError(c.at(), f"expected a value for prop {key!r}")
        c.i += 1
        value: Any = int(tok[1]) if tok[0] == "number" else tok[1]
        if key in PROP_VOCAB and value not in PROP_VOCAB[key]:
            warnings.append({"line": tok[2], "reason": f"{key} = {value!r} is not in {list(PROP_VOCAB[key])}"})
        props[key] = value
        if c.punct("]"):
            return props
        if not c.punct(","):
            raise ParseError(c.at(), "expected ',' or ']' in prop block")


def _decl(kind: str, c: _Cursor, warnings: list, line: int) -> dict[str, Any]:
    rec: dict[str, Any] = {"kind": kind, "id": c.take("id", f"an id after '{kind}'"), "line": line}
    attrs = DECLS[kind]
    while not c.done() and not (c.peek()[0] == "punct" and c.peek()[1] == "["):
        tok = c.peek()
        if tok[0] != "id" or tok[1] not in attrs:
            raise ParseError(tok[2], f"{kind}: unknown attribute {tok[1]!r}, expected one of {sorted(attrs)}")
        c.i += 1
        key, want = tok[1], attrs[tok[1]]
        field = FIELDS.get(key, key)
        if want == "id":
            rec[field] = c.take("id", f"an id after '{key}'")
        elif want == "number":
            rec[field] = int(c.take("number", f"a number after '{key}'"))
        elif want == "rank":
            nxt = c.peek()
            if nxt and nxt[0] == "number":
                c.i += 1
                rec[field] = int(nxt[1])
            elif nxt and nxt[0] == "id" and nxt[1] == "null":
                c.i += 1
                rec[field] = None
            else:
                raise ParseError(c.at(), "expected a number or 'null' after 'rank'")
        elif want == "effect":
            v = c.take("id", "none|vertical|horizontal after 'direct-effect'")
            if v not in EFFECTS:
                raise ParseError(c.at() if c.done() else c.t[c.i - 1][2], f"direct-effect {v!r} not in {list(EFFECTS)}")
            rec[field] = v
        elif want == "flag":
            rec[field] = True
        elif want == "labels":
            rec[field] = _labels(c)
    if c.punct("["):
        rec["props"] = _props(c, warnings, line)
        warnings.append({"line": line, "reason": f"prop block on `{kind}` declaration is outside grammar v0.1; kept as props"})
    return rec


def _edge(c: _Cursor, rec: dict[str, Any], warnings: list, line: int) -> dict[str, Any]:
    rec["from"] = c.take("id", "an endpoint")
    rel = c.take("id", "a relation type")
    if rel not in RELATIONS:
        raise ParseError(c.t[c.i - 1][2], f"unknown relation type {rel!r}")
    rec["type"], rec["vocabulary"] = rel, RELATIONS[rel]
    rec["to"] = c.take("id", "an endpoint")
    rec["props"] = _props(c, warnings, line) if c.punct("[") else {}
    return rec


def _statement(line: int, tokens: list, warnings: list) -> dict[str, Any]:
    c = _Cursor(tokens, line)
    tok = c.peek()
    if tok[0] != "id" or tok[1] not in (*DECLS, "rel", "assert"):
        raise ParseError(tok[2], f"expected a statement keyword (system, organ, level, instrument, competence, rel, assert), got {tok[1]!r}")
    c.i += 1
    kw = tok[1]
    if kw in DECLS:
        rec = _decl(kw, c, warnings, line)
    elif kw == "rel":
        rec = _edge(c, {"kind": "rel", "line": line}, warnings, line)
    else:
        claimant = c.take("id", "a claimant id after 'assert'")
        if claimant.endswith(":"):  # `assert a1: …` — ':' is an id character, so it glues
            claimant = claimant[:-1]
        elif not c.punct(":"):
            raise ParseError(c.at(), "expected ':' after the claimant")
        if not claimant:
            raise ParseError(line, "expected a claimant id after 'assert'")
        nxt = c.peek()
        deny = bool(nxt and nxt[0] == "id" and nxt[1] == "NOT")
        if deny:
            c.i += 1
        rec = _edge(c, {"kind": "assert", "asserted_by": claimant, "polarity": "deny" if deny else "affirm", "line": line},
                    warnings, line)
    if not c.done():
        raise ParseError(c.at(), f"unexpected {c.peek()[1]!r} after a complete {kw} statement")
    return rec


def parse(text: str) -> dict[str, Any]:
    """Read `.lt` text into statement records; every failed statement is one error with its line."""
    statements: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for line, tokens, source in _statements(text):
        if tokens is None:
            errors.append({"line": line, "reason": source, "statement": text.splitlines()[line - 1].strip()})
            continue
        try:
            statements.append(_statement(line, tokens, warnings))
        except ParseError as exc:
            errors.append({"line": exc.line, "reason": exc.reason, "statement": " ".join(source)})
    counts: dict[str, int] = {}
    for s in statements:
        counts[s["kind"]] = counts.get(s["kind"], 0) + 1
    return {"valid": not errors, "n_statements": len(statements), "statements": statements, "errors": errors,
            "warnings": warnings, "counts": counts}


@tool(PLANE, "loomground_mcp.tools.topos.parse (grammar/topos.ebnf v0.1)")
def topos_parse(text: str) -> dict[str, Any]:
    """Read `.lt` netlist text (system/level/organ/instrument/competence declarations, `rel` edges, `assert` claims with `[props]`) into statement records. `errors` lists every statement the grammar rejects with its line and reason; `warnings` flags off-vocabulary prop values and reader tolerances; `valid` is `errors == []`. Membership in ladders/catalogues and the well-formedness invariants are apply-time, not checked here."""
    return parse(text)


TOOLS = [topos_parse]

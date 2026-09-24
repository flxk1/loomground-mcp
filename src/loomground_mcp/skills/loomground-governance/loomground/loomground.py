#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""An implementation of the Loomground language, bundled with the skill.

Stdlib-only. A *host* that realises the abstract semantics of the specification
so patches can be machine-validated. It is not part of the specification (the
spec + grammar + vectors it conforms to); it ships here solely as the
validation engine of the `loomground` skill. Conformance-gated against this
repository's current vector suite (tools/check_companion.py) rather than
pinned to a version number here, so it cannot go stale the way a hardcoded
version claim would.
"""
from __future__ import annotations
import json
import os
import re

RISK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
FULL_RISK = frozenset(RISK)
# fallback autonomy ladder, used only when vocabulary/grades.json is unreadable;
# the active ladder is policy (spec §6, §10) and is loaded by _load_grades()
_DEFAULT_GRADES = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def _load_grades():
    """The active ladder: policy supplies the levels and their order
    (vocabulary/grades.json `levels`); the language owns only the comparison
    rule. Falls back to the historical default ladder only when the vocab
    file is unavailable — a missing/malformed file marks a broken install,
    not a smaller ladder."""
    here = os.path.dirname(os.path.abspath(__file__))
    vocab = os.path.join(here, "..", "..", "standard", "vocabulary", "grades.json")
    try:
        with open(vocab, encoding="utf-8") as f:
            levels = json.load(f)["levels"]
        return {lvl: i for i, lvl in enumerate(levels)}
    except (OSError, KeyError, ValueError, TypeError):
        return dict(_DEFAULT_GRADES)


# module-load default; check() re-reads the active ladder at check-time so a
# policy-swapped grades.json takes effect without restarting the process
GRADES = _load_grades()
# restrictiveness chain: auto ⊑ human ⊑ refused ⊑ reserved ⊑ prohibited
VERDICT = {"auto": 0, "human": 1, "refused": 2, "reserved": 3, "prohibited": 4}
# ordered declared token properties (vocabulary/{reversibility,uncertainty}.json).
# Ascending in concern, like RISK: a ">=" guard catches the severe end.
REVERSIBILITY = {"reversible": 0, "compensable": 1, "irreversible": 2}
UNCERTAINTY = {"settled": 0, "contested": 1, "unknown": 2}
# every ordered guardable property, by field name — the language compares declared
# values and derives none of them
ORDERED = {"risk": RISK, "reversibility": REVERSIBILITY, "uncertainty": UNCERTAINTY}
GUARD_OPS = {"kind": {"="}, "party": {"="}, "risk": {">=", "="},
             "reversibility": {">=", "="}, "uncertainty": {">=", "="},
             "tags": {"contains"}}


class Reject(Exception):
    def __init__(self, stage, msg):
        super().__init__(f"{stage}: {msg}")
        self.stage = stage


# ---------------------------------------------------------------- rack pre-pass
def expand_racks(lines):
    racks, out, i = {}, [], 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"\s*rack\s+(\w[\w-]*)\s*\(([^)]*)\)\s*:\s*$", ln)
        if m:
            name, params = m.group(1), [p.strip() for p in m.group(2).split(",") if p.strip()]
            body, i = [], i + 1
            while i < len(lines) and lines[i].strip() != "end":
                body.append(lines[i]); i += 1
            if i >= len(lines):
                raise Reject("parse", f"rack {name} missing end")
            racks[name] = (params, body); i += 1; continue
        out.append(ln); i += 1
    prog, inst = [], {}
    for ln in out:
        m = re.match(r"\s*rack-use\s+(\w[\w-]*)\s*\(([^)]*)\)\s*$", ln)
        if not m:
            prog.append(ln); continue
        name = m.group(1)
        if name not in racks:
            raise Reject("parse", f"unknown rack {name}")
        params, body = racks[name]
        binds = {}
        for b in m.group(2).split(","):
            if "=" not in b:
                raise Reject("parse", f"bad binding {b!r}")
            k, v = b.split("=", 1); binds[k.strip()] = v.strip()
        if set(binds) != set(params):
            raise Reject("parse", f"rack {name} args {set(binds)} != params {set(params)}")
        n = inst.get(name, 0); inst[name] = n + 1
        for bl in body:
            s = bl
            for k, v in binds.items():
                # v is literal text, not a replacement template: a value with
                # \1, \g<...>, or a trailing backslash must substitute verbatim.
                s = re.sub(r"\$" + re.escape(k) + r"\b", lambda _m, v=v: v, s)
            s = s.replace("$0", str(n))
            if "$" in s:
                raise Reject("parse", f"undefined substitution in {bl!r}")
            prog.append(s)
    return prog


# --------------------------------------------------------------------- parsing
class Patch:
    def __init__(self):
        self.nodes = {}          # id -> {"class":..., attributes}
        self.order = []          # declaration order of declared nodes
        self.grants = {}         # gate -> {actor: {"kinds":set|None,"risks":set|None}}
        self.grant_order = []    # (actor, gate) in gate-declaration/clause order
        self.cords = []          # (frm, to) as written
        self.reservations = []   # {"kind","by","when","duration","on_elapse"}
        self.prohibitions = []   # {"kind","when"}
        self.obligations = []    # {"obligation","on"}
        self.redress = []        # {"kind","by","overturn","within"}
        self.obo = {}            # delegate -> [delegator, ...] (checked at apply)
        self.mandates = {}       # actor -> [purpose set, ...] (>1 checked at apply)
        self.transfers = []      # {kind, to, within} (policy-global)
        # populated by check():
        self.cords_typed = []    # projection order: grant conferrals, then written cords

    def mandate_of(self, aid):
        """The actor's declared mandate, or None when it declares none. None is
        NOT the empty set for projection (an undeclared mandate is not projected),
        but the attenuation check treats an undeclared delegator as holding
        nothing to confer."""
        ms = self.mandates.get(aid)
        return ms[0] if ms else None


def _guard(tokens):
    # generic <field> <op> <value>; the field domain and pairings are apply-checked
    if len(tokens) < 3:
        raise Reject("parse", f"incomplete guard {tokens!r}")
    field, op, val = tokens[0], tokens[1], tokens[2]
    if op not in (">=", "=", "contains"):
        raise Reject("parse", f"bad guard operator {op!r}")
    return {"field": field, "op": op, "val": val}, tokens[3:]


def _grant(tok):
    m = re.match(r"^([\w-]+)(?:\[([^\]]*)\])?$", tok)
    if not m:
        raise Reject("parse", f"bad grant {tok!r}")
    actor, inner = m.group(1), m.group(2)
    kinds = risks = None
    if inner is not None:
        if ":" in inner:
            kpart, rpart = inner.split(":", 1)
            kinds = {kpart.strip()}; risks = {r.strip() for r in rpart.split(",")}
        else:
            kinds = {k.strip() for k in inner.split(",")}
    return actor, {"kinds": kinds, "risks": risks}


def _target(rest):
    # target = role | role and role | <m> of { role, role }  ->  canonical string
    if len(rest) >= 2 and rest[0].isdigit() and rest[1] == "of":
        if len(rest) < 3 or rest[2] != "{":
            raise Reject("parse", "m-of-n target without {")
        roles, i = [], 3
        while i < len(rest) and rest[i] != "}":
            if rest[i] != ",":
                roles.append(rest[i])
            i += 1
        if i >= len(rest) or not roles:
            raise Reject("parse", "unterminated m-of-n target")
        return f"{rest[0]} of {{{', '.join(roles)}}}", rest[i + 1:]
    if not rest:
        raise Reject("parse", "missing target")
    if len(rest) >= 3 and rest[1] == "and":
        return f"{rest[0]} and {rest[2]}", rest[3:]
    return rest[0], rest[1:]


def parse(text):
    raw = [l.split("#", 1)[0].rstrip() for l in text.splitlines()]
    raw = expand_racks(raw)
    p = Patch()
    try:
        for line in raw:
            _statement(p, line)
    except IndexError:
        raise Reject("parse", f"truncated statement {line!r}")
    return p


def _purpose_set(tok):
    """`deploy` or `{deploy,rollback}` -> a set of purposes. A single purpose may
    be written without braces (SYNTAX); the set is declared, never computed."""
    body = tok[1:-1] if tok.startswith("{") and tok.endswith("}") else tok
    out = {q for q in (q.strip() for q in body.split(",")) if q}
    if not out:
        raise Reject("parse", f"empty mandate {tok!r}")
    return out


def _statement(p, line):
    if not line.strip():
        return
    t = line.split()
    kw = t[0]
    if kw == "actor":
        p.nodes[t[1]] = {"class": "actor"}; p.order.append(t[1]); i = 2
        while i < len(t):
            if t[i] == "party": p.nodes[t[1]]["party"] = t[i + 1]; i += 2
            elif t[i] == "on-behalf-of": p.obo.setdefault(t[1], []).append(t[i + 1]); i += 2
            elif t[i] == "grade": p.nodes[t[1]]["grade"] = t[i + 1]; i += 2
            elif t[i] == "mandate":
                p.mandates.setdefault(t[1], []).append(_purpose_set(t[i + 1])); i += 2
            elif t[i] == "name": break               # name is text-to-eol
            else: raise Reject("parse", f"bad actor clause {t[i]!r}")
    elif kw == "human":
        p.nodes[t[1]] = {"class": "human"}; p.order.append(t[1]); i = 2
        while i < len(t):
            if t[i] == "role": p.nodes[t[1]]["role"] = t[i + 1]; i += 2
            elif t[i] == "name": break
            else: raise Reject("parse", f"bad human clause {t[i]!r}")
    elif kw == "gate":
        gid = t[1]; p.nodes[gid] = {"class": "gate"}; p.order.append(gid)
        p.grants.setdefault(gid, {}); i = 2
        while i < len(t):
            if t[i] == "risk": p.nodes[gid]["risk_floor"] = t[i + 1]; i += 2
            elif t[i] == "grade": p.nodes[gid]["grade_required"] = t[i + 1]; i += 2
            elif t[i] == "consign": p.nodes[gid]["consignee"] = t[i + 1]; i += 2
            elif t[i] == "party": p.nodes[gid]["party"] = t[i + 1]; i += 2
            elif t[i] == "name": p.nodes[gid]["name"] = t[i + 1]; i += 2
            elif t[i] == "grant":                    # MUST be last: consumes the rest
                for gt in t[i + 1:]:
                    a, spec = _grant(gt)
                    p.grants[gid][a] = spec
                    p.grant_order.append((a, gid))
                break
            else: raise Reject("parse", f"bad gate clause {t[i]!r}")
    elif kw == "cord":
        if len(t) != 4 or t[2] != "->":
            raise Reject("parse", "cord must be `cord <endpoint> -> <endpoint>`")
        p.cords.append((t[1], t[3]))
    elif kw == "reserve":
        if len(t) < 4 or t[2] != "by":
            raise Reject("parse", "reserve without by")
        # separate {, }, , and : so a quorum target and a temporal window tokenize
        rest = " ".join(t[3:])
        rest = re.sub(r"([{},:])", r" \1 ", rest).split()
        by, rest = _target(rest)
        entry = {"kind": t[1], "by": by, "when": None, "duration": None, "on_elapse": None}
        while rest:
            if rest[0] == "when":
                entry["when"], rest = _guard(rest[1:])
            elif rest[0] == "duration":
                if len(rest) < 4 or rest[2] != ":":
                    raise Reject("parse", "duration without `<duration> : <on-elapse>`")
                if rest[3] not in ("halt", "proceed"):
                    raise Reject("parse", f"bad on-elapse {rest[3]!r}")
                entry["duration"], entry["on_elapse"] = rest[1], rest[3]
                rest = rest[4:]
            else:
                raise Reject("parse", f"bad reserve clause {rest[0]!r}")
        p.reservations.append(entry)
    elif kw == "prohibit":
        entry = {"kind": t[1], "when": None}
        if len(t) > 2:
            if t[2] != "when":
                raise Reject("parse", f"bad prohibit clause {t[2]!r}")
            entry["when"], extra = _guard(t[3:])
            if extra:
                raise Reject("parse", f"trailing tokens {extra!r}")
        p.prohibitions.append(entry)
    elif kw == "obligation":
        if len(t) != 4 or t[2] != "on":
            raise Reject("parse", "obligation must be `obligation <obligation> on <gate>`")
        p.obligations.append({"obligation": t[1], "on": t[3]})
    elif kw == "transfer":
        # transfer <kind> to <consignee> within <purpose set>
        if len(t) != 6 or t[2] != "to" or t[4] != "within":
            raise Reject("parse", "transfer needs: <kind> to <consignee> within <purposes>")
        p.transfers.append({"kind": t[1], "to": t[3], "within": _purpose_set(t[5])})
    elif kw == "redress":
        if len(t) < 4 or t[2] != "by":
            raise Reject("parse", "redress without by")
        entry = {"kind": t[1], "by": t[3], "overturn": False, "within": None}
        i = 4
        while i < len(t):
            if t[i] == "overturn":
                entry["overturn"] = True; i += 1
            elif t[i] == "within":
                entry["within"] = t[i + 1]; i += 2
            else:
                raise Reject("parse", f"bad redress clause {t[i]!r}")
        p.redress.append(entry)
    else:
        raise Reject("parse", f"unknown keyword {kw!r}")


# ------------------------------------------------------------- well-formedness
def cord_type(p, frm, to):
    if to == "master":
        if p.nodes.get(frm, {}).get("class") != "gate":
            raise Reject("apply", f"only a gate may egress to master ({frm})")
        return "egress"
    cf = p.nodes.get(frm, {}).get("class")
    ct = p.nodes.get(to, {}).get("class")
    if cf is None or ct is None:
        raise Reject("apply", f"cord into undeclared node {frm}->{to}")
    if cf == "human" or ct == "human":
        raise Reject("apply", "a human may not be a cord endpoint")
    if cf == "actor" and ct == "gate":
        return "authority"
    if cf == "gate" and ct == "gate":
        return "pipe"
    raise Reject("apply", f"illegal cord {cf}->{ct}")


def _check_guard(g):
    if g is None:
        return
    if g["field"] not in GUARD_OPS:
        raise Reject(
            "apply",
            f"guard over {g['field']!r} "
            "(domain is kind/risk/reversibility/uncertainty/party/tags)")
    if g["op"] not in GUARD_OPS[g["field"]]:
        raise Reject("apply", f"guard pairing {g['field']} {g['op']} is invalid")
    scale = ORDERED.get(g["field"])
    if scale is not None and g["val"] not in scale:
        raise Reject(
            "apply", f"guard {g['field']} {g['val']!r} outside the domain")


def _risk_set(spec, kind):
    """The granted risk set of `spec` over `kind`; empty when not granted."""
    if spec is None:
        return frozenset()
    if spec["kinds"] is not None and kind not in spec["kinds"]:
        return frozenset()
    return FULL_RISK if spec["risks"] is None else frozenset(spec["risks"])


def check(p):
    global GRADES
    GRADES = _load_grades()  # active ladder, read at check-time (spec §6, §10)
    # declared values in their domains
    for nid, n in p.nodes.items():
        if "risk_floor" in n and n["risk_floor"] not in RISK:
            raise Reject("apply", f"unknown risk {n['risk_floor']}")
        for attr in ("grade", "grade_required"):
            if attr in n and n[attr] not in GRADES:
                raise Reject("apply", f"grade {n[attr]!r} is not a level of the active ladder")
    for gate, gr in p.grants.items():
        for spec in gr.values():
            if spec["risks"] is not None and not spec["risks"] <= set(RISK):
                raise Reject("apply", f"grant risk set outside the domain at {gate}")
    # an obligation attaches to a declared gate (SYNTAX §3; spec v0.8)
    for ob in p.obligations:
        if p.nodes.get(ob["on"], {}).get("class") != "gate":
            raise Reject("apply", f"obligation on undeclared gate {ob['on']}")
    # guards range over {kind, risk, party, tags} only — never id/provenance
    for r in p.reservations:
        _check_guard(r["when"])
    for pr in p.prohibitions:
        _check_guard(pr["when"])
    # type every written cord; an explicit authority cord denotes a (bare) conferral
    written = []
    for frm, to in p.cords:
        ty = cord_type(p, frm, to)
        if ty == "authority" and frm not in p.grants.get(to, {}):
            p.grants.setdefault(to, {})[frm] = {"kinds": None, "risks": None}
            p.grant_order.append((frm, to))
        written.append((frm, to, ty))
    # projection order: grant conferrals first, then written cords, duplicates removed
    p.cords_typed = [(a, g, "authority") for a, g in p.grant_order]
    granted_pairs = set(p.grant_order)
    for frm, to, ty in written:
        if ty == "authority" and (frm, to) in granted_pairs:
            continue
        p.cords_typed.append((frm, to, ty))
    pipes = [(f, t) for f, t, ty in written if ty == "pipe"]
    # acyclic pipe relation
    succ = {}
    for f, t in pipes:
        succ.setdefault(f, []).append(t)
    WHITE, GREY, BLACK = 0, 1, 2
    col = {}

    def dfs(u):
        col[u] = GREY
        for v in succ.get(u, []):
            if col.get(v, WHITE) == GREY:
                raise Reject("apply", "pipe cycle")
            if col.get(v, WHITE) == WHITE:
                dfs(v)
        col[u] = BLACK
    for g in [n for n, d in p.nodes.items() if d["class"] == "gate"]:
        if col.get(g, WHITE) == WHITE:
            dfs(g)
    # a required grade sits only on a source gate (no incoming pipe)
    piped_into = {t for _, t in pipes}
    for g in piped_into:
        if "grade_required" in p.nodes.get(g, {}):
            raise Reject("apply", f"required grade on piped (non-source) gate {g}")
    # reachability: every gate on a pipe∪egress path to master
    reaches = {f for f, t, ty in written if ty == "egress"}
    changed = True
    while changed:
        changed = False
        for f, t in pipes:
            if t in reaches and f not in reaches:
                reaches.add(f); changed = True
    for g, d in p.nodes.items():
        if d["class"] == "gate" and g not in reaches:
            raise Reject("apply", f"gate {g} on no path to master")
    # on-behalf-of: at most one delegator, declared actor-or-human targets, acyclic
    for aid, ms in p.mandates.items():
        if len(ms) > 1:
            raise Reject("apply", f"{aid} declares more than one mandate")
    for delegate, delegators in p.obo.items():
        if len(delegators) > 1:
            raise Reject("apply", f"{delegate} declares more than one delegator")
        cls = p.nodes.get(delegators[0], {}).get("class")
        if cls not in ("actor", "human"):
            raise Reject("apply", f"on-behalf-of names {delegators[0]!r}, not a declared actor or human")
    p.delegations = {d: ds[0] for d, ds in p.obo.items()}
    for start in p.delegations:
        seen, cur = set(), start
        while cur in p.delegations:
            if cur in seen:
                raise Reject("apply", "cycle in the on-behalf-of relation")
            seen.add(cur)
            cur = p.delegations[cur]
    # a consignee names where a gate's release goes; only a terminal gate
    # (one that egresses to the master) has a release to consign.
    terminal = {f for f, t, ty in p.cords_typed if ty == "egress"}
    consigning = {}          # consignee -> {gate, ...}
    for gid, n in p.nodes.items():
        c = n.get("consignee")
        if c is None:
            continue
        if gid not in terminal:
            raise Reject("apply", f"consignee on non-terminal gate {gid}")
        consigning.setdefault(c, set()).add(gid)
    for tr in p.transfers:
        if not tr["within"]:
            raise Reject("apply", f"transfer of {tr['kind']!r} declares no purpose")
        gates = consigning.get(tr["to"])
        if not gates:
            raise Reject("apply", f"transfer to {tr['to']!r}, which no gate consigns to")
        # transfer attenuation: an actor cannot license onward a purpose it was
        # not itself given. Lateral, not a delegation - no principal chain here.
        for gate in sorted(gates):
            for actor in sorted(p.grants.get(gate, {})):
                if not _risk_set(p.grants[gate].get(actor), tr["kind"]):
                    continue          # not granted over this kind at this gate
                m = p.mandate_of(actor)
                if m is None or not tr["within"] <= m:
                    raise Reject(
                        "apply",
                        f"transfer widens beyond {actor}'s mandate at {gate}")

    # no-amplification, pairwise over actor→actor links only (a human delegator
    # anchors answerability and constrains no grant)
    for delegate, delegator in p.delegations.items():
        if p.nodes[delegator]["class"] != "actor":
            continue
        dg, lg = p.nodes[delegate].get("grade"), p.nodes[delegator].get("grade")
        if dg is not None and (lg is None or GRADES[dg] > GRADES[lg]):
            raise Reject("apply", f"delegation grade amplifies: {delegate} above {delegator}")
        # mandate attenuation: a delegate's mandate is a subset of its delegator's,
        # and a delegator declaring none holds the empty set, so its delegate must
        # declare none either — an actor cannot confer a purpose it was not given.
        dm, lm = p.mandate_of(delegate), p.mandate_of(delegator)
        if dm is not None and (lm is None or not dm <= lm):
            raise Reject("apply", f"delegation widens mandate: {delegate} beyond {delegator}")
        for gate, gr in p.grants.items():
            ds = gr.get(delegate)
            if ds is None:
                continue
            ls = gr.get(delegator)
            kinds = ds["kinds"]
            if kinds is None:              # granted over all kinds
                if ls is None or ls["kinds"] is not None:
                    raise Reject("apply", f"delegate {delegate} granted at {gate} beyond {delegator}")
                kinds = {None}             # compare unnarrowed risk sets directly
            for k in kinds:
                if k is None:   # both grants unnarrowed over kind
                    dset = FULL_RISK if ds["risks"] is None else frozenset(ds["risks"])
                    lset = FULL_RISK if ls["risks"] is None else frozenset(ls["risks"])
                else:
                    dset, lset = _risk_set(ds, k), _risk_set(ls, k)
                if not dset <= lset:
                    raise Reject("apply", f"delegation amplifies risk over {k or 'any kind'} at {gate}")
    return p


# --------------------------------------------------------------- patch (authored form)
def to_patch(p):
    """The patch's canonical JSON serialization (standard/schema/patch.schema.json):
    the authored interchange form of the netlist, distinct from project()'s
    post-evaluation observation. Call after check() (needs cords_typed, delegations)."""
    nodes = []
    for nid in p.order:
        d = p.nodes[nid]
        e = {"id": nid, "class": d["class"]}
        for key in ("role", "party", "risk_floor", "grade", "grade_required", "name"):
            if key in d: e[key] = d[key]
        if nid in p.delegations: e["on_behalf_of"] = p.delegations[nid]
        if p.mandate_of(nid) is not None: e["mandate"] = sorted(p.mandate_of(nid))
        if "consignee" in p.nodes[nid]: e["consignee"] = p.nodes[nid]["consignee"]
        nodes.append(e)
    grants = []
    for actor, gid in p.grant_order:
        spec = p.grants[gid][actor]
        e = {"gate": gid, "actor": actor}
        if spec["kinds"] is not None: e["kinds"] = sorted(spec["kinds"])
        if spec["risks"] is not None: e["risks"] = sorted(spec["risks"], key=RISK.get)
        grants.append(e)
    cords = [{"from": f, "to": t, "type": ty} for f, t, ty in p.cords_typed]
    reservations = []
    for r in p.reservations:
        e = {"kind": r["kind"], "by": r["by"]}
        if r["when"]:
            g = r["when"]
            e["when"] = f'{g["field"]} {g["op"]} {g["val"]}'
        if r["duration"]:
            e["duration"] = r["duration"]; e["on_elapse"] = r["on_elapse"]
        reservations.append(e)
    prohibitions = []
    for pr in p.prohibitions:
        e = {"kind": pr["kind"]}
        if pr["when"]:
            g = pr["when"]
            e["when"] = f'{g["field"]} {g["op"]} {g["val"]}'
        prohibitions.append(e)
    out = {"nodes": nodes, "cords": cords}
    if grants: out["grants"] = grants
    if reservations: out["reservations"] = reservations
    if prohibitions: out["prohibitions"] = prohibitions
    if p.obligations: out["obligations"] = [dict(o) for o in p.obligations]
    if p.redress: out["redress"] = [dict(r) for r in p.redress]
    return out


# --------------------------------------------------------------- projection
def _resolved_party(p, nid):
    """The declared party, or a partyless delegate's party resolved along the
    (acyclic) principal chain to the nearest declared party."""
    cur = nid
    while cur is not None:
        n = p.nodes[cur]
        if "party" in n:
            return n["party"]
        cur = p.delegations.get(cur) if n["class"] == "actor" else None
    return None


def project(p):
    nodes = []
    for nid in p.order:
        d = p.nodes[nid]
        e = {"id": nid, "class": d["class"]}
        if "role" in d: e["role"] = d["role"]
        if "risk_floor" in d: e["risk_floor"] = d["risk_floor"]
        if "grade" in d: e["grade"] = d["grade"]
        if "grade_required" in d: e["grade_required"] = d["grade_required"]
        if nid in p.delegations: e["on_behalf_of"] = p.delegations[nid]
        if p.mandate_of(nid) is not None: e["mandate"] = sorted(p.mandate_of(nid))
        if "consignee" in p.nodes[nid]: e["consignee"] = p.nodes[nid]["consignee"]
        if d["class"] == "actor":
            party = _resolved_party(p, nid)
            if party is not None: e["party"] = party
        elif "party" in d:
            e["party"] = d["party"]
        nodes.append(e)
    nodes.append({"id": "master", "class": "master"})
    cords = [{"from": f, "to": t, "type": ty} for f, t, ty in p.cords_typed]
    res = []
    for r in p.reservations:
        e = {"kind": r["kind"], "by": r["by"]}
        if r["when"]:
            g = r["when"]
            e["when"] = f'{g["field"]} {g["op"]} {g["val"]}'
        if r["duration"]:
            e["duration"] = r["duration"]; e["on_elapse"] = r["on_elapse"]
        res.append(e)
    out = {"nodes": nodes, "cords": cords, "reservations": res}
    if p.transfers:
        out["transfers"] = [{"kind": t["kind"], "to": t["to"],
                             "within": sorted(t["within"])} for t in p.transfers]
    if p.redress:
        out["redress"] = [{"kind": r["kind"], "by": r["by"],
                           "overturn": r["overturn"], "within": r["within"]}
                          for r in p.redress]
    return out


# --------------------------------------------------------------- evaluation
def _guard_holds(g, token, floored):
    if g is None:
        return True
    if g["field"] == "kind":
        return token["kind"] == g["val"]
    if g["field"] == "party":
        return token.get("party") == g["val"]
    if g["field"] == "risk":
        return floored >= RISK[g["val"]] if g["op"] == ">=" else floored == RISK[g["val"]]
    if g["field"] in ("reversibility", "uncertainty"):
        # No gate floor: a gate raises a token's effective risk and nothing else
        # (specification, The token). An absent property satisfies no ordered
        # guard — fail-closed, never a defaulted level.
        scale = ORDERED[g["field"]]
        have = scale.get(token.get(g["field"]))
        if have is None:
            return False
        want = scale[g["val"]]
        return have >= want if g["op"] == ">=" else have == want
    if g["field"] == "tags":
        return g["val"] in token.get("tags", [])
    return False


def own_verdict(p, gate, token, actor):
    n = p.nodes[gate]
    floored = max(RISK[token["risk"]], RISK.get(n.get("risk_floor"), -1))
    # (1) prohibited — invariant under any privilege
    for pr in p.prohibitions:
        if pr["kind"] == token["kind"] and _guard_holds(pr["when"], token, floored):
            return "prohibited"
    # (2) refused — no authorizing grant over this kind at this risk (default-deny)
    spec = p.grants.get(gate, {}).get(actor)
    floor_name = [k for k, v in RISK.items() if v == floored][0]
    if floor_name not in _risk_set(spec, token["kind"]):
        return "refused"
    # (3) reserved
    for r in p.reservations:
        if r["kind"] == token["kind"] and _guard_holds(r["when"], token, floored):
            return "reserved"
    # (4) the auto/human disposition; the grade comparison at a source gate
    if "grade_required" in n:
        g = p.nodes.get(actor, {}).get("grade")
        if g is None or GRADES[g] < GRADES[n["grade_required"]]:
            return "human"   # fail-closed for an ungraded actor
    return "auto"            # ungated step (4): policy default in these vectors


def evaluate(p, activations):
    """One evaluation per activation. Returns (per-gate results, ordered log)."""
    pipes = [(f, t) for f, t, ty in p.cords_typed if ty == "pipe"]
    succ, preds = {}, {}
    for f, t in pipes:
        succ.setdefault(f, []).append(t)
        preds.setdefault(t, []).append(f)
    egress = {f for f, t, ty in p.cords_typed if ty == "egress"}
    decl_pos = {nid: i for i, nid in enumerate(p.order)}
    results, log = {}, []
    for act in activations:
        actor, src, token = act["actor"], act["source"], act["token"]
        # gates activated: reachable from the source over pipes (incl. the source)
        reach, stack = set(), [src]
        while stack:
            u = stack.pop()
            if u in reach:
                continue
            reach.add(u)
            stack += succ.get(u, [])
        eff = {}

        def effective(g):
            if g in eff:
                return eff[g]
            v = own_verdict(p, g, token, actor)
            for h in preds.get(g, []):
                if h in reach and VERDICT[effective(h)] > VERDICT[v]:
                    v = effective(h)
            eff[g] = v
            return v
        # evaluation order: predecessors first; ties by declaration order
        indeg = {g: sum(1 for h in preds.get(g, []) if h in reach) for g in reach}
        ready = sorted((g for g in reach if indeg[g] == 0), key=decl_pos.get)
        ordered = []
        while ready:
            g = ready.pop(0)
            ordered.append(g)
            for t in succ.get(g, []):
                if t in reach:
                    indeg[t] -= 1
                    if indeg[t] == 0:
                        ready.append(t)
            ready.sort(key=decl_pos.get)
        for g in ordered:
            verdict = effective(g)
            log.append({"gate": g, "verdict": verdict})
            entry = results.setdefault(g, {})
            entry["verdict"] = verdict
            if g in egress:
                entry["master"] = "act" if verdict == "auto" else "withhold"
    return results, log


# --------------------------------------------------------------- token check
def validate_token(tok):
    if not isinstance(tok, dict):
        return False
    for f in ("id", "kind", "party"):
        if not isinstance(tok.get(f), str):
            return False
    if tok.get("risk") not in RISK:
        return False
    prov = tok.get("provenance")
    if not isinstance(prov, list) or not all(isinstance(x, str) for x in prov):
        return False
    for field, scale in (("reversibility", REVERSIBILITY), ("uncertainty", UNCERTAINTY)):
        if field in tok and tok[field] not in scale:
            return False
    if "tags" in tok:
        tags = tok["tags"]
        if not isinstance(tags, list) or not all(isinstance(x, str) for x in tags):
            return False
    return True

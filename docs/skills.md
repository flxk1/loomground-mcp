<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Prompts and skills

The server serves 26 public skills as MCP prompts, one per vendored SKILL.md.

- `prompts/list` — one prompt per skill.
- `prompts/get` — the skill body under one header line:
  `Skill <name> from <repo> @ <commit>; tools: <allowed-tools>`.
- `loomground_skill(name?)` — the same index and bodies as a tool. Without `name` it returns the
  index; with `name` (or `<repo>/<name>` when the name is shared) the record plus `body`, the
  SKILL.md with its frontmatter stripped. An unknown or ambiguous name returns `unavailable`.

## The index

The index carries 26 records, one per conformant public Agent Skill. A record is `repo`, `name`,
`description`, `allowed_tools`, `commit`, `path`, `url`, `prompt`. The format keeps room for a
metadata-only record from a private repository (`private: true`): no body, and never a prompt.

The one shared skill name is qualified: `loomground/loomground` and
`loomground-governance/loomground`.

## Vendoring and parity

A skill is vendored whole, not as a body alone: `tools/vendor_skills.py` copies
`skills/<name>/` out of its repository at a pinned commit into
`src/loomground_mcp/skills/<repo>/<name>/`, with every reference, script and agent file the
instructions reach for, and records what it copied in `skills/vendored.json` — repository,
commit, source directory, URL, and each file's sha256. Re-running it is a no-op; it is the only
writer of that tree, and package-data ships the directory whole, so what an instruction points at
is in the wheel.

Three checks hold that:

- `tools/vendor_skills.py --check`, and `tests/test_skills_vendoring.py` with it, compare the tree
  to the manifest in both directions: every recorded file present, unaltered and non-empty, and
  every file under `skills/` recorded — enumerated from the disk, so a directory carrying no
  SKILL.md is not a hiding place. Each index entry is re-derived from the vendored body, so a
  description cannot drift from the skill it describes, and every relative path a body reaches for
  has to exist and, when it names a file, be one. Neither needs a checkout or a network.
- the same tests hold `pyproject.toml`'s `package-data` minus its `exclude-package-data` to exactly
  that file list plus the two records, so a skill cannot be whole in the repository and truncated
  in the wheel, and nothing the manifest does not vouch for — an editor's backup, compiled
  byte-code — can ride along.
- `tests/test_skills_parity.py` compares the vendored directory to its repository at the pinned
  commit, file for file. A checkout that is absent skips locally; in CI
  `test_ci_has_every_pinned_source` fails instead, because there a lost fetch would silently stop
  asserting parity.

`skills_lint` is the family's Agent Skills conformance linter, and it holds the three rules nothing
else here holds: description length, the allowed frontmatter key set, and that a description says
when to use the skill. It is **vendored the same way the skills are** — `tools/vendored/`, from
[repo-standards](https://github.com/flxk1/repo-standards) at the commit `skills/vendored.json`
pins, each file recorded with its sha256, so `--check` detects a vendored copy that has drifted
from the commit it claims. Nothing in the build or in CI reads from that repository: it is a
working repo, where the rules are drafted, and a published product must not take a build input
from one — `tests/test_build_inputs.py` holds every repository this repository fetches or pins to
the catalogue's list of published ones. The linter runs unconditionally over the vendored tree, its
verdict line is asserted as well as its exit code (its own exit 2 means it linted nothing), and
three tests prove the vendored copy still enforces each of the three rules.

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
  to the manifest — a dropped, added or altered file fails, as does a body referencing a path that
  is not beside it. Neither needs a checkout or a network, so they never skip.
- the same tests hold `pyproject.toml`'s package-data against the manifest, so a skill cannot be
  whole in the repository and truncated in the wheel.
- `tests/test_skills_parity.py` compares the vendored directory to its repository at the pinned
  commit, file for file. A repository that cannot be fetched leaves its checkout absent and its
  parity items skip, so a missing checkout is never a false green.

`skills_lint` from [repo-standards](https://github.com/flxk1/repo-standards) is the family's
conformance linter; CI fetches it at a pinned commit and runs it over the vendored tree.

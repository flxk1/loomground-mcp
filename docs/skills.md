<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Prompts and skills

The server serves 22 skills as MCP prompts, one per vendored SKILL.md.

- `prompts/list` — one prompt per skill.
- `prompts/get` — the skill body under one header line:
  `Skill <name> from <repo> @ <commit>; tools: <allowed-tools>`.
- `loomground_skill(name?)` — the same index and bodies as a tool. Without `name` it returns the
  index; with `name` (or `<repo>/<name>` when the name is shared) the record plus `body`, the
  SKILL.md with its frontmatter stripped. An unknown or ambiguous name returns `unavailable`.

## The index

The index carries 22 records — the family's conformant Agent Skills in public repositories, each
at its repository's pushed main commit. A record is `repo`, `name`, `description`,
`allowed_tools`, `commit`, `path`, `url`, `prompt`.

The one shared skill name is qualified: `loomground/loomground` and
`loomground-governance/loomground`.

## Vendoring and parity

Every body is vendored at `src/loomground_mcp/skills/<repo>/<name>/SKILL.md`, and
`tests/test_skills_parity.py` checks each one byte for byte against its repository at the commit
`skills/index.json` pins. A repository that cannot be fetched leaves its checkout absent and its
parity items skip, so a missing checkout is never a false green.

---
name: agent-doc-bootstrap
description: Use when creating or updating AGENTS.md, CLAUDE.md, repo agent guides, project instructions, or reusable agent/skill configuration for a new or existing repo. Trigger on "agent.md", "AGENTS.md", "CLAUDE.md", "global agent config", "project instructions", "make a repo guide", "bootstrap instructions", "reuse my style", "look at other projects", or "scalable agent docs".
---

# Agent Doc Bootstrap

Goal: create thin, durable repo adapters that inherit global style and shared skills without duplicating them. These docs are operating manuals, not repo snapshots.

## Load Order

1. Inspect the active harness's loaded instructions and discover any user-level guide it uses. Read that guide when accessible; do not assume a particular username, home path or harness. If no global guide exists, keep the repo guide self-contained.
2. Inspect existing local docs:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `.claude/skills/`
   - README/docs/package scripts
3. Search memories/transcripts only for repeated behavior patterns, not to recreate a project summary.
4. Draft the repo guide as an adapter, not a memoir.

## What Goes Global

- Collaboration style.
- Source-of-truth-first behavior.
- Code and semantic validation: do not introduce regex-driven product logic or
  tests for AI prompts, pipelines, API contracts, structured payloads, or
  user-visible results. Use parsers, schemas, typed fields, explicit state,
  domain invariants, persisted/provider payloads, and real runtime output.
  Regex is only for narrow lexical checks or candidate search when no structured
  boundary is practical; it is never proof of semantic correctness.
- Model/cost/subagent policy.
- Shared design, motion, UI polish, copy, audit, and verification concepts.
- Pushback rules: challenge false abstractions and stale assumptions; do not challenge precise corrections or short factual asks.

## What Goes Repo-Local

- Durable paths or file families to inspect, not current values copied out of them.
- Command discovery and stable verification entrypoints.
- Ownership boundaries between app, package, spec, API, DB, and design system.
- Product vocabulary and stable coding taste.
- Known classes of sharp edges, phrased as checks to perform.
- Slack/Drive/GitHub routing only when it is a durable workflow contract.
- Repo-specific pushback zones, phrased as layer-boundary checks rather than old incident summaries.

Avoid:

- Current defaults that can drift.
- Current branch names, PR numbers, row counts, IDs, or one-off paths.
- Repeating README architecture summaries.
- Storing answers that the agent should recompute from the repo.
- Long command tables when `package.json`, Makefiles, or docs can be inspected.
- Copying transcript anecdotes. Extract the durable rule and discard the story.

## Repo Guide Template

```md
# Agent Guide

## Scope
## Load Order
## Shared Skills
## Source Of Truth
## Commands
## UI / Product Taste
## Backend / API / Data
## Testing / Verification
## Git / PR / Handoff
## Pushback Zones
## Contradictions To Avoid
```

## Symlink Policy

- Prefer `AGENTS.md` as the canonical repo guide for Codex.
- Add `CLAUDE.md -> AGENTS.md` only when no meaningful Claude-specific file exists.
- If `CLAUDE.md` already contains detailed useful guidance, keep it and make `AGENTS.md` point to it or summarize the deltas.
- Do not duplicate the same long text into both files.

## Shared Skill Completion

Follow the user's existing skill layout. If they maintain a canonical shared
folder, edit that source and use their existing links. Otherwise use the
requested repository or the active tool's documented skill directory.

For a user who wants to share a skill across tools, a single checkout with
symlinks avoids independent copies. Discover the actual target directories
from each tool's configuration; common defaults include `~/.claude/skills`,
`~/.codex/skills` and `~/.cursor/skills`. Create only the missing link for the
selected skill. Preserve an existing file, directory or dangling symlink and
report the conflict instead of replacing it.

Verify that each intended link resolves to the canonical `SKILL.md`. Do not
depend on a private linking script or install a background watcher as a side
effect. Keep repo-private skills in their repository.

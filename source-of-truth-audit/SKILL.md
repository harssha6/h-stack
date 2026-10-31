---
name: source-of-truth-audit
description: Trace a disputed or current claim to its authoritative runtime, data, code, or Git owner. Use for why/source-of-truth questions and read-only diagnosis before edits.
---

# Source Of Truth Audit

Goal: answer from the runtime owner, not from memory or labels.

## Operating Bias

- Treat UI labels, README text, and prior memory as leads, not proof.
- Treat regex hits as leads, not proof. For semantic behavior, follow the
  structured value through its parser, runtime owner, persisted payload, and
  output surface before reaching a conclusion.
- If the user asks "why", "discuss", "actual", "from db", "current", or "is this pushed", stay read-only until the owner is identified.
- Name the truth layer in the answer: local file, runtime config, DB row, API response, rendered UI, remote branch, hosted check, or system tool.
- Push back when the requested explanation skips the authoritative layer.

## Workflow

1. Name the claim or behavior being checked.
2. Identify possible truth surfaces: code path, DB row, config, env, API response, artifact, rendered UI, Git remote, PR/check state, or logs.
3. Inspect the cheapest authoritative surface first.
4. If multiple layers can override each other, report them separately.
5. State whether the answer is exact, inferred, stale, or an upper bound.
6. If the user asked to discuss, stop after the read-only diagnosis unless they authorize edits.
7. If editing follows, verify the same layer again after the change.

## Common Layer Splits

- App defaults vs script/runner overrides.
- Current local branch vs remote branch.
- An offline database copy vs the live app database.
- UI label vs persisted payload.
- Schema shape vs live row counts.
- Local tests vs hosted PR/check/Bugbot state.
- Spec/design docs vs executable code.
- Rendered browser/simulator output vs JSX/SwiftUI source intent.
- Device/system route vs generic process guesses.

## Output Format

Use this structure when useful:

- **Short answer**: the direct conclusion.
- **Evidence**: exact files, commands, rows, routes, or UI states inspected.
- **Why this looked confusing**: the layer split or stale assumption.
- **Next action**: edit, verify, or leave alone.

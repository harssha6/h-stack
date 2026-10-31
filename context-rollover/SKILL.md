---
name: context-rollover
description: Use when a long Codex or Claude Code conversation should be compacted into a high-fidelity handoff and continued in a genuinely fresh work thread. Trigger on "compact this conversation", "roll this into a new thread", "start fresh with the context", "make a handoff", "new chat with everything important", or "summarize and continue elsewhere".
---

# Context Rollover

Turn a long conversation into a durable, decision-aware handoff and, when requested, start a fresh task with that handoff as its first prompt. This is a deliberate rollover, not a fork: the original thread remains intact and the new thread starts with compacted context.

## Modes

### Handoff only

Use when the user asks to compact, summarize, or prepare context but does not ask to create a new task. Produce the handoff in the response and optionally save it to the requested artifact location.

### Rollover to a new task

Use only when the user explicitly asks to start a new thread, new chat, fresh
task or continue elsewhere.

1. Build the handoff below from the conversation. Preserve the causal chain behind important decisions.
2. Inspect the active harness's supported task/thread creation tools and their current schemas. Use a tool only when it is available and its documented behavior creates the kind of task the user requested. Do not invent tool names, directives or capabilities.
3. Resolve the actual project and working checkout through that tool's supported project selection. Use a separate worktree only when requested or needed for safe concurrent work; follow the tool's isolation contract.
4. Create the task with the handoff as its first prompt. Keep the original conversation intact. Do not fork, archive, rename or mutate it unless separately requested.
5. Return the link or identifier the tool actually provides and report whether creation succeeded.
6. The new task must begin by rechecking current source of truth before editing. The handoff is context, not proof that the code or runtime still matches the conversation.

If creation is unavailable, unsupported or fails, return the complete handoff
in a copy-ready code block so the user can open a new task manually. Do not
pretend that a task was created or silently switch to another provider.

## Handoff Contract

Use this structure. Omit empty sections, but do not silently omit uncertainty.

```md
# Context Handoff

## Continuation Objective
- The exact outcome the next agent should achieve.
- What is explicitly out of scope.

## Current State
- What is complete.
- What is in progress.
- Current branch, working tree, task/thread, runtime, or environment when known.

## User Intent And Constraints
- Exact product intent and visible behavior.
- Preferences, terminology, taste, platform constraints, and non-negotiables.

## Decisions And Why
- Decision: ...
  - Why: ...
  - Evidence: exact / inferred / stale / memory-derived.

## Rejected Approaches
- Approach: ...
  - Rejected because: ...

## Source Of Truth To Recheck
- Files, routes, DB/API surfaces, persisted state, branch/PR state, browser/simulator surfaces, logs, or artifacts the next agent must inspect.

## Changes And Artifacts
- Files changed or expected to change.
- Commands, generated artifacts, links, or external records.

## Verification
- Checks that passed, with the surface tested.
- Checks that were not run or are unavailable.

## Open Risks And Questions
- Known uncertainty, blockers, regressions, or decisions that still need the user.

## Next Action
- One concrete first action for the new task.
```

## Fidelity Rules

- Keep exact paths, route names, identifiers, command names, error messages, and user corrections when they matter.
- Preserve why a decision was made, not just what was chosen.
- Separate facts from proposals. Mark claims as exact, inferred, stale, upper bound, or memory-derived when relevant.
- Preserve failed attempts when they prevent the next agent from repeating them.
- Prefer a small set of source-of-truth pointers over copying a stale repo snapshot.
- Distinguish completed changes from intended changes.
- Include the last known user request and the next action separately; they are often not the same.
- Do not include secrets, tokens, private credentials, or unnecessary raw transcript/tool output.
- Do not claim tests, renders, commits, deployments, or external writes that were not verified.
- Do not compress away a user correction just because it appears repetitive. Repeated corrections are often the strongest taste signal.

## Fresh-Task Prompt

When creating the new task, wrap the handoff with this instruction:

> You are continuing work from a previous task. Treat the handoff below as context, not as current proof. First inspect the current source of truth and working-tree state, reconcile any drift, then continue from the stated next action. Preserve the user's constraints and terminology. Do not redo completed work unless verification shows it is missing or wrong. Report what you verified before making broad changes.

Then include the full `# Context Handoff` block.

## Avoiding Context Debt

- Do not put the handoff into global `AGENTS.md` or a repo guide unless the user explicitly wants a durable workflow decision there.
- Do not save a repo snapshot as if it were a durable instruction.
- Do not carry unrelated conversation topics into the new task.
- Do not use a new task to hide unresolved ambiguity. Put the ambiguity in `Open Risks And Questions` and ask only when it materially changes the next action.
- Keep the original task available as an audit trail until the new task is verified.

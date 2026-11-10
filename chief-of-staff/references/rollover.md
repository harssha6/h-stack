# Orchestrator rollover runbook

A long orchestrator thread gets slow to read and expensive to continue. Roll it over into a fresh thread automatically. The owner should not notice a difference, and nothing (context, ideas, progress) may be lost. The files are the memory; the thread is only the conversation.

Copy this file into the orchestrator folder as `ROLLOVER.md` and adjust the thresholds.

## When

- The morning brief checks the current orchestrator thread (id in `ORCHESTRATOR.md`) as its last step. Roll over when the thread has more than about 1,500 items, or the last rollover was 7 or more days ago, and no run in the thread is mid-task on something the owner is waiting for.
- Also whenever the owner asks.
- Never during the owner's quiet hours, and never while one of their messages is unanswered.

## What carries over

Everything in the orchestrator folder: `NOW.md`, `BOARD.md`, `LEDGER.md`, `LOG.md`, `PULSE.md`, `ORCHESTRATOR.md`, this file and any optional files. Plus shared skills and any memory service the agents use.

## Steps (old thread)

0. Commit the folder (`git add -A && git commit -m 'Before rollover <date>'`, local history).
1. Bring `NOW.md`, `BOARD.md` and `LEDGER.md` up to date with everything from the current conversation. Anything said only in chat and not written down is lost after this step.
2. Write `HANDOFF.md` (overwrite): continuation objective, current state, open conversations with the owner (unanswered questions, promises made), decisions since the last rollover and why, the owner's corrections and tone notes. Under 150 lines; point to files instead of copying them. The `context-rollover` skill has the full handoff shape.
3. Launch the new thread in the orchestrator's project (so it starts in the folder and loads `AGENTS.md`), with the same title and model as `ORCHESTRATOR.md` and an idempotency key like `orchestrator-rollover-<date>`. First message: "You are the orchestrator, continuing from thread <old id>. Follow ROLLOVER.md section 'First run'."
4. Do not archive yourself yet. The new thread does that after its checks pass.

## First run (new thread)

1. Read, in order: `ROLLOVER.md`, `HANDOFF.md`, `NOW.md`, `BOARD.md`, `LEDGER.md`, the first 40 lines of `LOG.md` (newest first), `PULSE.md`, and the owner's global agent guide if `NOW.md` **Config** names one.
2. Take over the schedules. List scheduled tasks. For every enabled task bound to the old thread (the morning brief at least), create the same task (same title, prompt and schedule) bound to yourself, then disable the old one. Do not change any prompt text other than thread ids.
3. Update `ORCHESTRATOR.md`: your thread id, the date, and move the old id under "Previous threads".
4. Pin yourself. Unpin and archive (settle) the old thread.
5. Verify: no enabled task is bound to the old id; the pulse prompt reads `ORCHESTRATOR.md` and hardcodes no thread id; `ORCHESTRATOR.md` shows your id; the old thread is archived; you are pinned. Add one line at the top of `LOG.md`.
6. Post one short message to the owner: "Fresh thread. Board is current." plus anything from `HANDOFF.md` that waits on them today. Nothing else.

## Failure

If any first-run step fails, leave the old thread active, add the failure at the top of `LOG.md` and post it in both threads.

If your harness cannot create threads or rebind schedules, roll over by hand: run "Steps (old thread)" 0 to 2, start a new thread yourself in this folder with the step 3 message, and move the schedules yourself. Never leave the owner with zero orchestrator threads or two half-working ones.

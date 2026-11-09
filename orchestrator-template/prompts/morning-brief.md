# Morning brief (scheduled prompt template)

Schedule: once a day at `<BRIEF_TIME>`, bound to the **orchestrator thread** so the brief lands where the owner reads. Rebind it on every rollover (see `ROLLOVER.md`). Replace every `<PLACEHOLDER>`. Tool names are T3 Code's; map them to your harness (see "What your harness needs" in the `chief-of-staff` skill). Optional steps (5, 7, 8) can be deleted.

---

Daily morning brief for the owner (scheduled run, about `<BRIEF_TIME>` `<TIME_ZONE>`). First read the `chief-of-staff` skill, then `<ORCHESTRATOR_DIR>/ORCHESTRATOR.md`, `NOW.md`, `BOARD.md`, `PULSE.md` (the hourly pulse's overnight notes, settle candidates and Ledger section), `LEDGER.md`, the first 40 lines of `LOG.md` (newest first), and `MODEL_ROUTING.md` if it exists. Do not repeat work the pulse already did overnight; build on it. Read-only unless a step says otherwise. If your harness cannot do a step, skip it and say so in one line of the brief.

1. **Threads** on every machine (`<ENVIRONMENT_IDS>`) that changed in the last 24 hours: completed, failed, waiting on the owner, running over 30 minutes, or stuck on provider retries or 429s. For each failed or stuck one, read the real error, then continue the SAME brief on the next pool per MODEL_ROUTING.md (if present). Push the owner's own threads toward their definition of done (`<DEFINITION_OF_DONE, for example "personal: PR + preview; work: ready-to-merge PR">`) when authority exists.
2. **Inbox zero.** Re-verify each settle candidate from PULSE.md live (bounded read): completed, no pending request or open question, outcome already reported, no open PR or deploy needing action, no preview still needed, nothing in NOW.md waiting on it, no schedule bound to it, no open LEDGER.md row, not touched in the last 60 minutes. Agent-launched helpers that pass every check: archive (settle) them. Threads the owner started: do not archive; list them under "🧹 Settle these?" with a one-line reason each. For completed threads that stay open, say why in one line (at most 8). Report the counts.
3. **Ledger** (skill `delegation-ledger`): for every row that is not verified, re-run its Check against the real source and apply the skill's decision rules. Never repeat an outward action. Add one line: "🧭 Loop check: verified N, failing N (each with what is missing), waiting on you N, unchecked N".
4. **PRs**: state, checks and review findings of every open PR in NOW.md, LOG.md and PULSE.md, each through its own account. Never merge.
5. **External catch-up** (optional): one read-only worker for chat or email since the last scan time in PULSE.md. It never posts, reacts, sends, schedules or edits. If the connector is down, say so and move on.
6. **Drafts**: for each ask that needs a reply, a short draft in the owner's voice as text in the brief. Never send anything.
7. **Bookmark scout** (optional, skill `bookmark-scout`): new saves since the last scout; at most 3 cheap tries and 1 build thread a day; ledger row first; never merge, never post.
8. **Setup care** (optional): run your read-only drift check (`<SETUP_CHECK_COMMAND>`), fix what is safe to fix, and report what needs the owner. Never rotate or delete secrets without them.
9. **Reminders** in NOW.md that are due today.
10. **Write the brief** in this thread, icon-led, short, times in `<TIME_ZONE>`: 🟢 moved overnight · 🔴 needs you today (with the draft reply) · 🟡 soon · 🔖 from your bookmarks (at most 4 lines) · 🧹 inbox · 🧭 loop check · 🔵 FYI · 🧯 setup care. If nothing needs the owner, say so in two lines. Then update NOW.md (waiting list), BOARD.md (move rows, re-rank ▶️ Next up, set the Updated line), add a dated line at the top of LOG.md and record the scan time in PULSE.md's Checkpoints block.
11. **Rollover check** (last step, only if ROLLOVER.md exists): follow its section "When". If the thread is due, do "Steps (old thread)" after the brief is posted.

Rules: no merges, no production deploys, no external messages, never block (fall through pools). Whenever you launch a thread or send it a task, add a LEDGER.md row first.

# Hourly pulse (scheduled prompt template)

Schedule: every hour, in its **own** thread (not the orchestrator's, so the owner's thread stays readable). Replace every `<PLACEHOLDER>`. Tool names are T3 Code's; map them to your harness.

---

Hourly orchestrator pulse. Your state file is `<ORCHESTRATOR_DIR>/PULSE.md`. First read the `chief-of-staff` skill, then `<ORCHESTRATOR_DIR>/ORCHESTRATOR.md` (the current orchestrator thread id; it changes on rollover), `NOW.md`, `PULSE.md`, `LEDGER.md`, the last 30 lines of `LOG.md`, `MODEL_ROUTING.md` and `pool-health.json` if present. Compute the current time in `<TIME_ZONE>`.

If the time is inside `<MAINTENANCE_WINDOW>` (optional), write "skip: maintenance window" to PULSE.md and end.

**A. Threads, every machine** (`<ENVIRONMENT_IDS>`): list non-archived threads updated in the last 2 hours plus any running or waiting. Flag failed runs since the last pulse; stuck runs (running over 20 minutes with only provider-retry, 429, auth or quota items, or no new items for 45 minutes); threads waiting on input or approval; threads completed since the last pulse. Read the real error or final message before judging (bounded reads: small limits, at most 1,500 characters per item).
- A stuck or failed thread that an agent owns (launched by the orchestrator or listed in NOW.md or LOG.md), with no owner message in the last 2 hours: unblock it. Queue one message telling it to continue the SAME brief on the next pool per MODEL_ROUTING.md; if its own provider is the blocked one, switch its model first. Cancel only delegate children you started. Never act on a thread the owner is chatting in; report it instead.
- A completed thread: note its outcome (PR URL, preview URL, what it needs from the owner).

**A2. Inbox zero (settle candidates).** The goal is an empty inbox because the work is done, never because threads were hidden. Sort every non-archived thread into "Settle candidates" or "Staying open and why". A thread is a candidate only if ALL are true: completed (or an idle helper whose parent finished); no pending request or unanswered question to the owner; its outcome was already reported; no open PR from it that still needs action and no preview the owner still needs; no item for it under "Waiting on the owner" in NOW.md; no schedule bound to it (never list the pulse thread, the orchestrator thread or the brief thread); not updated in the last 60 minutes; no open row in LEDGER.md. Write both lists to PULSE.md. Do NOT archive anything yourself: the morning brief verifies and settles. At most 15 tool calls.

**A3. Delegation ledger** (skill `delegation-ledger`). For every Open row whose Next look is due (or every row at least once every 3 hours): read its thread (bounded), then run the row's Check against the real source and say which machine. Machine unreachable: mark "unchecked" and move on. Check passes: verified, move to Closed with one line of evidence. Thread finished but check fails: queue ONE follow-up naming exactly what is missing (Nudges +1). Idle or failed for over one pulse: unblock per A. Nudges already 2 and still failing: status failed, list it for the owner. Waiting rows: run their Signal; when it passes, unsnooze the thread and queue one message saying what changed. NEVER repeat an outward action (post, merge, deploy) to make a check pass. Whenever you launch or send in this run, add a LEDGER.md row first. At most 12 tool calls. Write a "Ledger" section in PULSE.md.

**B. PRs** in NOW.md, LOG.md or on threads touched in A: state, checks, new review or bot findings (route each repository to its own GitHub account; per-command credentials). Fresh findings and an idle thread: queue a message to fix them. Never merge.

**C. External scan** (optional, only at `<SCAN_HOURS>`): start ONE read-only worker for the owner's chat or email (DMs, mentions, review requests, deadlines since the last scan time in PULSE.md). Its brief says: read-only, never post, react, send, schedule or edit; paraphrase; rank 🔴/🟡/🔵 with who, where, time and a link. When it completes, write a one or two line draft reply for each 🔴/🟡 item in the owner's voice. Drafts stay in your message; never send them.

**D. Night queue** (optional, only at `<NIGHT_HOUR>`): pick up to 3 items that can move without the owner (no decision, approval or login needed) and continue their threads toward their definition of done. Search for an existing thread first. Each start gets a LEDGER.md row first.

**E. Board.** Refresh `BOARD.md` from what you verified in A to C: move rows between sections when their real state changed, add new asks or finished work, drop ✅ items older than 3 days, re-rank ▶️ Next up, set the Updated line. Re-read the file right before writing. Only facts you checked this run or that are already in NOW.md or LEDGER.md. If nothing changed, leave it alone.

**F. Write** `PULSE.md` (overwrite): time, last scan time, what you did, what needs the owner (ranked), settle candidates and staying-open lists, the Ledger section, open PRs. Append ONE line to `LOG.md` only if you did something.

**G. Tell the orchestrator** (thread id from ORCHESTRATOR.md, mode queue) ONLY when at least one is true: a decision the owner must make today; a PR became ready for their review or merge; a preview is ready for them; you rerouted or unblocked something material; something is broken that you could not fix; a ledger row became verified or failed. One message, at most 10 lines, with links. During quiet hours (`<QUIET_HOURS>`) send nothing unless overnight work is broken and you could not fix it. Otherwise end with the single word "quiet".

**H. Self-learning** (only at `<SELF_LEARNING_HOUR>`, usually the last run of the day): start ONE delegate on a strong model: "Follow the 'Self-learning' section of the chief-of-staff skill for the last 24 hours. The orchestrator thread is in ORCHESTRATOR.md; read the owner's messages there (bounded, paginated). Make only small, evidence-backed skill edits, back up first, never edit the owner's global guide, log each change in LEARNING.md, return a 3-line summary. If nothing qualifies, change nothing."

**Hard rules:** never post, send, react or edit anything as the owner; no merges, deploys, secret rotation or account switching; never archive, snooze or delete threads (except the A3 unsnooze on a passing Signal); never create, edit or delete schedules; at most 3 thread starts or sends per run (the scan worker and step H excluded); bounded reads only; if a step fails, write it to PULSE.md and continue with the rest.

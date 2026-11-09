---
name: delegation-ledger
description: Close the loop on work handed to other threads or agents. Use whenever you launch a thread, send a task to an existing thread, delegate a task, or hand work to another machine, and whenever a scheduled pulse or brief checks what is still open. Every handoff gets one ledger row with a proof check; a row closes only when the check passes against the real source, never because the thread said "done".
---

# Delegation ledger

A thread saying "posted", "deployed" or "done" is a claim, not evidence. Threads report a Slack video as posted when it never reached the channel. Handoffs also go quiet: an idle thread, a machine that never answers, a half answer. The ledger makes every handoff checkable and gives a scheduled pulse something to chase.

The ledger is one Markdown file, `LEDGER.md`, in the orchestrator folder (see [`chief-of-staff`](../chief-of-staff/SKILL.md) and [`orchestrator-template/LEDGER.md`](../orchestrator-template/LEDGER.md)). Any thread that hands work to another may add a row. Only a passing check closes it.

## When you hand work off

1. Before or right after the send, add a row to the Open table, newest at the top:

   | ID | Thread | Machine | Asked | Done when (proof, source) | Check (run on) | Next look | Nudges | Status |

   - **ID:** a short slug plus the date, for example `docs-deploy-0611`.
   - **Done when:** an observable fact in the real owner of the state, never a thread message. Good: "`curl -sI https://example.com/page` shows `x-robots-tag: noindex`", "PR #124 has an approving review", "the channel read shows the file post", "the file exists at `<path>` and renders". Bad: "thread says finished".
   - **Check:** the exact command or tool call that proves it, runnable by the pulse without asking anyone. Name the machine it runs on.
   - **Next look:** a time, normally the next pulse, or later for slow work.
   - **Status:** `open`, `waiting-on-owner`, `waiting-on-other` (name the role, for example "repo admin"), `verified`, `failed`, `stale`.
2. Put the Done-when sentence in the brief you send, so the thread knows what proof is expected and reports it.
3. Tell the owner the row exists only if it needs them.

## When you review the ledger

Every pulse and every morning brief, for each row that is not `verified`:

1. Read the thread (small limits) for its status and last result.
2. Run the **Check** against the real source. Say which machine you ran it on.
3. Decide:
   - **Check passes:** mark `verified` with the date and one line of evidence, and move the row to Closed.
   - **Thread finished but the check fails:** send one follow-up naming exactly what is missing and count it in `Nudges`. Never accept a second "done" without the check passing.
   - **Thread idle, failed or interrupted with no result for more than one pulse:** nudge once, then relaunch on another provider pool if it still sits. Never block.
   - **Needs the owner or another person:** set `waiting-on-owner` or `waiting-on-other`, and surface it in the brief with the one decision or action needed. A `waiting-on-other` row can carry a **Signal** (a structured check that flips when that person acts) so the pulse wakes the thread by itself.
   - **Two nudges and still failing:** set `failed` and tell the owner plainly what failed and what you tried.
4. Archive (settle) a thread only after its row is `verified`, or `waiting-on-*` with an owner. Never archive a thread with an open row.

## Rules

- Verify in the owning source: a channel read, the PR's state from the GitHub API, `curl` against the live URL, the file on disk, `docker ps`, the deployment's commit. Say which machine and whether the evidence is exact or inferred.
- **Outward actions never retry blindly.** If a post, merge or deploy claimed success but the check fails, do not post, merge or deploy again; report and ask. Repeating an outward action to make a check pass is how duplicates reach real people.
- A machine may not answer. If a check cannot run there, mark the row `unchecked: <machine> unreachable`, retry next pulse and say so in the brief. Unchecked is not passed.
- Keep rows short. Move closed rows to the Closed table and drop closed rows older than 14 days.
- No secrets in the ledger. Reference secret names and paths only.

## Example rows

```markdown
| ID | Thread | Machine | Asked | Done when (proof, source) | Check (run on) | Next look | Nudges | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| og-image-0911 | <thread link> | server | 9 Nov 02:20 | PR open (not merged) with a 1200x630 og.png; the preview's HTML has og:image and twitter:card | server: `gh pr view <n> --json state,headRefOid`; `curl -s <preview> \| grep -c og:image` | 03:00 | 0 | open |
| repo-access-0811 | <thread link> | laptop | 8 Nov 15:00 | the build can read the dependency repo | Signal: `gh api repos/<owner>/<repo>` returns 200 | every pulse | 0 | waiting-on-other (repo admin) |
```

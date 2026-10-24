---
name: pr-babysitter
description: Finish GitHub PR closeout after creating or updating any PR, or when asked to babysit, monitor CI, handle Bugbot/security/reviewer findings, or get a PR ready. Discover live org gates, repair valid in-scope issues, and verify the final head before handoff. Keep status-only and discussion requests read-only.
---

# PR Babysitter

Paths like `<skill-dir>/scripts/...` are relative to this skill's folder; replace `<skill-dir>` with wherever you installed it.

Own the loop from an open PR to a verified handoff. A push, green local checks,
or a successful bot check is progress, not completion. Use this after creating
or updating a PR by default; cover every requested layer of a stack.

## Authority

- Status checks, audits and discussion stay read-only. Selecting/installing this
  skill does not authorize live PR changes.
- A request to fix/babysit an agent-owned PR, or create/update and finish it,
  authorizes narrow repairs, relevant verification, scoped fix commits, normal
  pushes and bot-thread closeout. Carry existing authorization forward.
- Read human feedback too. Reply to/resolve human threads only with explicit
  communication authorization. If a human joins a bot thread, apply this boundary.
  Prepare the exact reply before asking; name the action requiring approval.
- This explicitly invoked workflow permits one attributed `[agent]` reply on a
  bot-only thread with the repair SHA/evidence, followed by resolution once the
  repair is remote and verified. Do not auto-resolve disputed findings or waive
  security findings. False positives receive evidence, not cosmetic dismissal.
- Merge, auto-merge/queue enrollment, deployment, force pushes, remote branch
  migration/deletion, review dismissal, bot autofix, paid manual bot runs and repo
  settings need separate authority. Slack/email announcements need authorization.

## Identify the real target

1. Accept a PR URL, number plus repo, current branch, or explicit set. Inspect
   workspace guides, dirty state, remotes/upstream and existing open PRs. Reuse a
   PR only if its topic fits; never assume the base is main.
2. If you use multiple GitHub accounts, make sure the right one is active for
   the repository. Inspect origin; if absent or aimed elsewhere, verify the
   selected PR/upstream remote. The repo's own contribution guide owns checkout
   choice. Verify API identity, inspect commit identity before writes, and
   restore temporary account switches. Do not run watchers/writers across
   conflicting accounts. The helper never switches accounts itself; set
   `PR_SNAPSHOT_EXPECTED_ACCOUNT` to make it fail when the active `gh` login
   differs.
3. Follow the repo's own contribution conventions before writes: branch and
   title naming, ticket references and any live ticket-validity checks. Report
   old mismatches; do not silently migrate a published branch.
4. Use T3 `link_pull_request` for each PR worked on when available, and reconcile
   with `list_thread_pull_requests` before handoff. Report linking failures.
   Research-only reference PRs are not task targets.
5. Discover effective rules on the exact base, including inherited org rules
   and classic protection. Read [references/evidence.md](references/evidence.md)
   for commands, permission gaps, test-merge checks and review freshness.

## Collect, inspect, repair, repeat

The dependency-free helper is read-only. Its JSON is evidence, not a verdict:

```sh
python3 <skill-dir>/scripts/pr_snapshot.py --pr auto
python3 <skill-dir>/scripts/pr_snapshot.py --repo OWNER/REPO --pr NUMBER
python3 <skill-dir>/scripts/pr_snapshot.py --pr https://github.com/OWNER/REPO/pull/NUMBER
```

Run from the chosen checkout or give an explicit target for an audit. Save large
snapshots privately. API errors/limitations stay visible; empty data is no pass.

On every cycle:

1. Stop on merged/closed state. Closure is not proof of merge/deployment or
   permission to open a follow-up PR.
2. Read new published feedback before rerunning old CI. Inspect all review
   submissions, PR comments and unresolved inline threads, including older/
   outdated threads and follow-ups. Ignore unpublished pending reviews. Do not
   filter by `[bot]` suffix: inspect Bugbot, security scanners, Codex, Copilot,
   CodeRabbit and every actual author. Neutral/success checks can have findings.
3. Verify each finding against current code and its owning runtime. Classify as
   valid, already repaired, false positive, subjective/scope change or externally
   blocked. Keep a small session ledger keyed by thread/comment ID, updated time,
   observed SHA, disposition, repair SHA, reply and resolution. Existing unresolved
   findings count, not just comments arriving after monitoring starts.
4. Inspect every emitted check and legacy status, missing required contexts/
   workflows, security findings, approvals, conflicts, base freshness, draft and
   queue state. Diagnose logs before repair/rerun. Separate branch regressions,
   reproduced baseline failures, outages, inaccessible scanners and permissions.
5. Repair confirmed in-scope issues in coherent batches. Preserve unrelated
   tracked/untracked/ignored work. Dirt alone is no reason to stop, stash, reset,
   switch branches or create a worktree. Isolate only actual concurrent-edit
   conflicts, following workspace rules. Fetch selected base/head before conflict
   repair and preserve both sides' intended behavior. Check history policy first;
   if repair requires rewriting published history, prepare a concrete plan and
   report the blocker instead of force-pushing.
6. Run repo checks/hooks, add regression coverage where behavior warrants it,
   and verify UI, gestures, routing, auth and contracts at the owning runtime.
   Source/build checks are not browser/backend/provider proof. Discover commands
   from manifests/guides; no boilerplate tests for punctuation-only changes.
7. Inspect the scoped diff, commit only owned repairs, push normally, and verify
   the remote PR contains the repair. Then close eligible bot threads with
   evidence. Already-repaired findings also need remote proof. Human threads
   follow the communication boundary above.
8. Collect immediately after a push, rerun, reply or resolution. Changed head/base
   invalidates old readiness evidence. Re-read approvals: stale dismissal,
   CODEOWNER or last-push policy can block even with an APPROVED review displayed.

For diagnosed transient Actions failures, allow at most **two failed-job reruns
per workflow and head SHA** unless the user chooses another budget. Track attempts;
use `gh run rerun RUN_ID --failed --repo OWNER/REPO`. Skip reruns if a repair push
is imminent. Do not retry deterministic failures, create empty commits, or rerun
deployment workflows as routine CI. For external checks, inspect provider links;
do not fabricate Actions reruns. Prefer automatic bot update reviews; manual
Bugbot runs can incur spend and require specific authorization.

## Duration and stopping

- Default create/update/babysit mode ends at verified handoff, terminal PR state,
  or a concrete external blocker. This does not merge.
- Explicit until-merged/closed or time-window requests keep watching after
  readiness, until the requested condition, cancellation or a blocker making
  further work impossible. A couple of sample polls does not satisfy monitoring.
- Use interruptible 30–60 second waits during pending checks/bot reviews/GitHub
  computation. Keep one owned loop per PR; resume in the same turn after repair.
  Do not detach a watcher and claim triage continues after the turn ends. Say
  when monitoring stops; an always-on service/schedule is a separate request.
- At apparent completion, wait another interval and take a fresh full sweep:
  unchanged head/base, completed expected bot evidence or proven intentional skip,
  no new actionable feedback, satisfied live gates. Two quiet polls never prove
  a missing bot ran or a hidden rule passed.
- Before handing off for human approval, finish all agent repairs, eligible bot
  closeout and pending checks. Say `CI/bot repairs complete; awaiting CODEOWNER/
  latest-push approval`, not `ready to merge`. A human thread needing an authorized
  response is a separate gate.
- Diagnose stalled/missing checks using trigger policy and recent durations.
  After two diagnosis cycles without actionable progress, report the external
  blocker, run IDs, elapsed time, evidence gap and next owner/action. Timeout is
  pending/blocked, never passed. Respect explicit longer monitoring when new
  progress is possible; don't repeatedly retry an exhausted failure.

## Handoff

Use the strongest supported state:

- **Ready to merge:** stable final head/base, applicable required gates satisfied,
  emitted checks acceptable, bot findings triaged, no unresolved actionable
  findings, conversation policy met, required CODEOWNER/last-push approvals,
  not draft, mergeability and queue policy satisfied. Investigate BLOCKED,
  UNKNOWN, DIRTY, BEHIND or UNSTABLE instead of inferring readiness from green CI.
- **Agent work complete, external gate remains:** name missing approval, human
  response, scanner access, queue result or required workflow.
- **Pending/blocked:** failures, incomplete bot reviews, conflicts, evidence gaps
  or exhausted retries remain. An inaccessible scanner is not clean.
- **Merged/closed:** verified GitHub state; deployment is separate evidence.

Final output: each PR link and final short SHA, repairs and verification,
check/bot status, unresolved findings and exact remaining gate. Recheck local
dirty state and T3 links before ending. Keep updates concise; avoid duplicate
external announcements. General lessons and
public documentation links live in [references/research.md](references/research.md);
use it for maintenance, never as current policy.

# Delegation ledger

Every handoff gets a row before or right after the send. A thread saying "done" is a claim, not proof: a row closes only when its Check passes against the real source. Skill: `delegation-ledger`.

Status values: open, waiting-on-owner, waiting-on-other (name the role), verified, failed, stale, unchecked (machine unreachable).

## Open

| ID | Thread | Machine | Asked | Done when (proof, source) | Check (run on) | Next look | Nudges | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| example-0101 | <thread link> | <machine> | <date time> | <observable fact in the real owner, for example "PR #12 open, not merged, preview returns 200"> | <machine>: `<exact command>` | <time> | 0 | open |

## Closed

| ID | Closed | Evidence |
| --- | --- | --- |
| <id> | <date time> | <machine>: <one line of evidence from the check> |

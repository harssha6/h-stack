# Model routing and fall-through

Copy this into the orchestrator folder as `MODEL_ROUTING.md` and fill in your own pools. A **pool** is one provider account as your harness exposes it (for example a personal Claude account, a work Codex account, a Cursor seat). Keep work and personal pools apart: work sources stay on work pools.

## Route by task type

| Work | Preferred route | Fallback |
|---|---|---|
| Design and substantial UI implementation | `<strongest design model>` on `<pool>` | same model on the next pool, then the closest equivalent |
| Backend, algorithms, system design | `<strongest reasoning model>` on `<pool>` | next pool, then equivalent |
| Bounded quick fixes (two prompts or fewer) | `<fast model>` on `<pool>` | any fast model |
| Browser or computer-use testing | a model with the required tools on `<pool>` | report the blocker; do not fake the test |
| Cheap workers (extraction, summaries, checks) | `<small model>` on `<pool>` | another small model |

A short prompt does not make a risky migration a quick fix. Estimate scope before launch.

## Pool health

Keep a small `pool-health.json` next to this file:

```json
{"pools": {"<pool id>": {"status": "ok|blocked", "since": "<ISO time>", "evidence": "429 on <task>", "until": "<reset time or null>"}}}
```

1. Read it before choosing a pool. Skip a pool marked blocked.
2. Record a new 429, usage-limit or auth block with evidence and time. Clear it when a real task succeeds on that pool. An unknown quota is not a block; an observed 429 is.
3. Never spend a model request only to probe whether a pool works.

## The stall guard

A provider limit does not always fail a run. Some harnesses leave a run "running" with one error item ("Provider retry: exceeded retry limit, last status: 429") and never end it. Workers can hang like that for hours.

1. Check every thread or worker about 10 minutes after launch, then every 15 minutes while it runs.
2. A run whose only new items are provider retries, 429s, auth or quota errors, or that shows no progress, is dead. Cancel it (only the parent that started it can) and rerun the same brief on the next route, carrying over partial output.
3. When a whole pool goes down, move every thread it stalled, not only the next one you notice. Example: one night a personal account hit its rate limit at 02:20; the orchestrator switched four running threads, the pulse included, to another provider and told each to continue. None of them waited for morning.

## Spare quota

Subscriptions reset on a schedule. When a pool will reset soon with quota left, use it for queued work that needs no decision, while keeping headroom for the owner's own sessions.

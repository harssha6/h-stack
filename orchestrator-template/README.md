# Orchestrator template

Blank skeletons for a chief-of-staff orchestrator thread (skill [`chief-of-staff`](../chief-of-staff/SKILL.md)). This folder has no `SKILL.md` on purpose: copy it somewhere private and fill it in; do not link it as a skill.

```sh
cp -R ~/.agents/h-stack/orchestrator-template ~/orchestrator
cd ~/orchestrator && git init -q && git add -A && git commit -qm 'Orchestrator from template'
```

Keep the copy private. Once it runs, it holds links, names and work context.

## What is here

| File | Purpose |
|---|---|
| `AGENTS.md` | Short contract that loads every turn when the orchestrator runs in this folder |
| `ORCHESTRATOR.md` | The current orchestrator thread id; the only place it is written |
| `BOARD.md` | The owner's view: ▶️ next up, needs you, waiting, running, done, ideas, parked |
| `NOW.md` | Standing rules, decisions, waiting list, reminders |
| `LEDGER.md` | Every handoff with its proof check (skill [`delegation-ledger`](../delegation-ledger/SKILL.md)) |
| `LOG.md` | Dated one-liners, newest first |
| `PULSE.md` | The hourly pulse's notes, overwritten each run |
| `prompts/pulse.md` | Hourly pulse prompt, for its own scheduled thread |
| `prompts/morning-brief.md` | Daily brief prompt, bound to the orchestrator thread |

Optional files the skill describes: `ROLLOVER.md` ([runbook](../chief-of-staff/references/rollover.md)), `MODEL_ROUTING.md` and `pool-health.json` ([routing](../chief-of-staff/references/model-routing.md)), `HANDOFF.md`, `LEARNING.md`.

## Fill in, in this order

1. `NOW.md` standing rules: who may merge, what counts as work versus personal, commit identities, quiet hours, time zone.
2. Start the orchestrator thread with this folder as its project, then write its id into `ORCHESTRATOR.md`.
3. Copy `MODEL_ROUTING.md` from the reference and list your provider pools.
4. Replace every `<PLACEHOLDER>` in the two prompts and schedule them: the pulse hourly in a new thread, the brief daily in the orchestrator thread.
5. Ask the orchestrator for something. It should add a ledger row, launch a thread and put the ask on the board in the same turn. If it only answers in chat, point it at `AGENTS.md`.

`grep -rnE '<[A-Z_]{3,}' ~/orchestrator` lists the capitalised placeholders you have not filled yet.

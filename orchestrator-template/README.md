# Orchestrator template

Blank skeletons for a chief-of-staff orchestrator thread (skill `chief-of-staff` in h-stack). This folder has no `SKILL.md` on purpose: copy it somewhere private and fill it in; do not link it as a skill. Links below are relative to the h-stack checkout, so read this file there, not in your copy.

```sh
HSTACK=~/.agents/h-stack          # where you cloned h-stack
cp -R "$HSTACK/orchestrator-template" ~/orchestrator
cp "$HSTACK/chief-of-staff/references/rollover.md" ~/orchestrator/ROLLOVER.md
cp "$HSTACK/chief-of-staff/references/model-routing.md" ~/orchestrator/MODEL_ROUTING.md
cd ~/orchestrator && ln -s AGENTS.md CLAUDE.md
git init -q && git add -A && git commit -qm 'Orchestrator from template'
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
| `LOG.md` | Dated one-liners, newest first (add at the top) |
| `PULSE.md` | The hourly pulse's notes, overwritten each run except its Checkpoints block |
| `ROLLOVER.md`, `MODEL_ROUTING.md` | Copied from `chief-of-staff/references/` by the commands above |
| `prompts/pulse.md` | Hourly pulse prompt, for its own scheduled thread |
| `prompts/morning-brief.md` | Daily brief prompt, bound to the orchestrator thread |

Created later, when needed: `HANDOFF.md` (rollover), `pool-health.json` (blocked pools), `LEARNING.md` (self-learning).

## Fill in, in this order

1. `NOW.md` standing rules and **Config**: who may merge, what counts as work versus personal, commit identities, quiet hours, time zone, ideas file, definition of done.
2. Start the orchestrator thread with this folder as its project, then write its name, title and id into `ORCHESTRATOR.md`.
3. List your provider pools in `MODEL_ROUTING.md`, or delete the file if you use one account.
4. Replace every `<PLACEHOLDER>` in the two prompts and schedule them: the pulse hourly in a new thread, the brief daily in the orchestrator thread.
5. Ask the orchestrator for something small. It should add a ledger row, launch a thread and put the ask on the board in the same turn. If it only answers in chat, point it at `AGENTS.md`. Then run the pulse prompt once by hand and check `PULSE.md`.

See "What your harness needs" in the `chief-of-staff` skill for the steps that need thread tools and what to do without them.

`grep -rnE '<[A-Z_]{3,}' ~/orchestrator` lists the capitalised placeholders you have not filled yet.

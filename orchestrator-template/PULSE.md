# Orchestrator pulse

Overwritten by every full pulse run, except the **Checkpoints** block, which each run carries over and updates. The morning brief and the orchestrator read it.

## Checkpoints (carry over on every run, including skipped ones)
- Last run: <DATE TIME TZ> (<full | skipped: reason>)
- Last external scan (chat, email): <TIME or n/a>
- Last bookmark scout: <TIME or n/a>

## Did
- <what this run checked and changed>

## Needs the owner (ranked)
- <item>: <the one thing needed>

## Settle candidates
- <thread link>: <why it is done (verified row, outcome reported, no open PR)>

## Staying open and why
- <thread link>: <PR awaiting merge | asks the owner X | ledger row open | still running>

## Ledger
verified N · failing N · waiting N · unchecked N
- <failing row id>: <what is missing>

## Open PRs
- <repo#n>: <state, checks, review>

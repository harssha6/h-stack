# Current orchestrator thread (single source of truth)

Every schedule, pulse and helper that needs to message the orchestrator reads the thread id from here. Never hardcode it anywhere else.

- name: <NAME, for example Friday>
- title: <THREAD TITLE, reused by the rollover>
- threadId: <THREAD_ID>
- environment: <ENVIRONMENT_ID or machine label>
- project: <PROJECT_ID>, workspace <PATH TO THIS FOLDER>
- model: <PROVIDER POOL> / <MODEL>
- since: <DATE TIME, TIME ZONE>

## Previous threads (archived, read-only history)
- <OLD_THREAD_ID> (<from> to <to>)

---
name: hum
description: Run and inspect development servers, workers, watchers, and tunnels in a shared Herdr terminal session through the bundled hum executable. Use for managed long-running processes and their logs, readiness, ownership, and cleanup.
---

# hum

Use `<skill-dir>/scripts/hum`, or an existing installation of this executable.
Run `hum --help` for syntax. [README.md](README.md) covers dependency discovery,
an explicit installation, optional host templates, and compatibility limits.
Installing this skill does not install Herdr, start services, or enable cleanup.

## Before running work

- Check the repository's start command, then run `hum ls` from its checkout.
  Reuse an existing environment when suitable. Each checkout, including a
  worktree, gets its own workspace; each named server gets a tab.
- `hum doctor` reports configuration without contacting a service. If Herdr is
  unavailable, report the missing dependency or ask for the intended executable.
  Do not install dependencies or alter host services just to answer a status request.
- Use an explicit session and state directory when testing this package beside
  another hum installation. Existing sessions and registered state are live
  resources, not disposable fixtures.

## Start, observe, and hand off

```sh
hum up web --lifetime task --owner 'manual:review-task' --purpose 'Verify the app' --ttl 2h --wait Ready -- npm run dev
hum logs web -n 120
hum wait web Ready --timeout 180
hum keep web --owner 'manual:review-task' --ttl 2h
hum release web --owner 'manual:review-task'
```

Choose the actual task owner instead of copying the example. Readiness text
must come from the current run's output; a process launch alone is not proof the
service works. Report the project, server name, URL, owner and preview expiry in
the user's timezone. Preserve other owners' claims when reusing an environment.

Use `--` followed by ordinary command arguments. Arguments retain their quoting;
if a pipeline or shell expression is required, pass an explicit `sh -c '...'`.
Commands and paths are retained in local state and logs. Keep secrets out of
command arguments; use the project's existing secret-injection mechanism.

`hum restart web` and `hum down web` stop the verified foreground process tree.
They can interrupt other owners: use them only within the user's authorization.
Never stop Herdr's whole server/session to repair one project's service.

## Lifetimes and safe cleanup

- New environments default to a two-hour **preview** lease. Use a bounded preview
  for human testing and renew it while needed.
- **Task** environments belong to the active job. Release your own claim when
  the job succeeds, fails, or is cancelled. Last release may stop the bound run.
- **Persistent** environments never expire. Reserve them for explicitly lasting
  services; declaring a database temporary does not make its data disposable.
- A `t3:<thread-id>` owner must identify an actual T3 thread, not a provider
  session. Cleanup protects an active owner and fails closed if its status is
  unknown. Without T3, use explicit renewable manual/task owners.

Inspect `hum cleanup --dry-run --json` before enabling any scheduled cleanup.
Cleanup considers registered local environments only. Missing/invalid policy,
unknown ownership, stale process births and mismatched pane/run identities stay
protected. It retains logs, commands and application data.

On Linux with `/proc` and pidfd support, `hum close web` can close a finished
terminal after its owners release it. `hum cleanup --empty-only --dry-run --json`
previews that separate operation. Focused panes, live foreground/background or
disowned jobs, uncertain shell identity and parent worktree groups remain
protected. On macOS, empty-terminal close is unavailable; leave the terminal for
the user. Do not use `rm`, injected `exit`, or whole-workspace close to bypass it.

`hum rm web` is an explicit stop-and-remove operation, not ordinary shared-owner
cleanup. Use it only when removal is authorized. Archived output remains
available through `hum logs`; `hum up` can recreate a safely closed terminal.

## Optional sharing and notifications

`hum share web --port <app-port>` uses the user's existing Tailscale Serve setup
for a tailnet HTTPS URL. It does not provision a tailnet or expose a public
Funnel. Start the app on loopback, confirm the right app port, and verify the URL
from the intended peer. Unknown existing Serve routes are left untouched; a
matching upstream alone does not establish ownership. New routes get a local
receipt after creation is verified. Legacy shares without that receipt require
manual inspection. Reuse/removal requires the exact recorded root/TLS layout;
extra paths or public Funnel flags protect the port. Do not race another
Serve/Funnel configuration writer; the CLI cannot perform conditional updates.

`hum ls --all` reads machines already saved in Herdr. `hum relay` follows their
existing event logs over SSH; it does not register peers or create remote files.
Do not add machines or configure SSH/Tailscale without the user's request.

Local start/restart/stop/remove events are recorded. Desktop notifications are
opt-in through `HUM_NOTIFY`; a notification backend or remote relay requires
separate host setup. A crashed process or a command stopped directly in its
terminal does not emit an event. Do not claim continuous crash monitoring.

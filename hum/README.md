# hum

Harssha's shared dev-server wrapper, exported with its lifecycle and terminal
helpers. It uses [Herdr](https://github.com/herdrdev/herdr) as a separate terminal
backend. hum is covered by h-stack's MIT license; Herdr is Apache-2.0 and is not
bundled here.

The package starts servers in visible panes, records their run identities, and
shares renewable ownership leases. It includes the executable, two required
Python helpers, offline tests, an explicit installer and optional host templates.
Nothing installs or enables itself when the skill is loaded.

## Requirements and compatibility

- Python 3.10+ on Linux or macOS. No pip packages are required.
- A separately installed Herdr CLI. The adapter uses its JSON `session list`,
  `workspace list/create/get/rename`, `pane list/get/process-info/run/rename/close`,
  `tab create/rename/close` and `machine list` interfaces, plus plain-text
  `pane read --source recent-unwrapped`. Herdr releases with another command or
  response shape need adapter changes; no release version is certified here.
- Git identifies checkout/worktree roots. Outside Git, the current directory
  becomes the project. `ps` is used for local process inspection.
- Optional: Portless for a default dev command; `lsof` to discover app ports;
  an existing Tailscale installation for sharing; OpenSSH for remote inventory
  and event relay; a T3 CLI for exact `t3:` owner lookups.
- Optional favicon rendering uses existing `sips`/Quick Look on macOS or
  `ffmpeg` on Linux. Without them, workspace initials still work.

The imported lifecycle and terminal tests use mocked process/Herdr surfaces.
Additional package tests use temporary directories and a fake Herdr executable.
They never start a real session, contact a peer, or enable a service.
Linux pidfd guard tests skip on other platforms. macOS empty-terminal close is
deliberately unsupported. A passing portable test suite does not certify real
Herdr or desktop integration on either OS; perform an isolated host smoke test
before enabling cleanup automation.

## Try it without a global install

From the h-stack checkout, these commands only read configuration:

```sh
python3 hum/scripts/hum --help
python3 hum/scripts/hum doctor
```

To copy the runtime to a new directory you choose:

```sh
python3 hum/scripts/install.py --directory /chosen/new/hum-runtime
python3 hum/scripts/install.py --directory /chosen/new/hum-runtime --apply
/chosen/new/hum-runtime/hum --help
```

The first command previews. The second creates only the executable, its two
sibling modules and the MIT license; it refuses existing destination entries. It does not edit PATH,
install Herdr, register a session, or configure services. Keep the three files
together. Parent directories must be trusted and stable during installation.
If a write fails, the tool reports an error and may leave a partial installation
in the newly chosen directory; it does not delete or overwrite existing content.

Configure a separate session and state location before a host smoke test:

```sh
export HUM_SESSION=hum-trial
export XDG_STATE_HOME=/chosen/private/state
export HUM_HERDR_BIN=/chosen/path/to/herdr
export HUM_MACHINE=local
HUM_BIN=/chosen/new/hum-runtime/hum
"$HUM_BIN" doctor
```

After reviewing the chosen configuration, run from a test checkout:

```sh
"$HUM_BIN" ls
"$HUM_BIN" up web --owner manual:trial --purpose 'Local smoke test' --ttl 30m --wait Ready -- npm run dev
"$HUM_BIN" logs web
"$HUM_BIN" release web --owner manual:trial
"$HUM_BIN" cleanup --dry-run --json
```

Use the app's actual readiness output and start command. `ls`/`up` can create the
selected Herdr session; `doctor`, `--help` and an offline cleanup do not. Tests,
builds and other one-shot commands do not need a managed server.

## Configuration

| Setting | Behavior |
| --- | --- |
| `HUM_HERDR_BIN` | Explicit Herdr executable. Otherwise discover `herdr` on PATH, then conventional local/Homebrew paths. |
| `HUM_SESSION` | Session name, default `hum`; a single path component without control characters. Use a distinct name beside an existing installation. |
| `XDG_STATE_HOME` | State root, default `~/.local/state`; hum uses `hum/<session>/` below it. |
| `HUM_OWNER` | Default explicit owner; command `--owner` takes precedence. Otherwise a provider session or local username supplies a renewable claim. |
| `HUM_MACHINE` | Display label; otherwise read `$XDG_CONFIG_HOME/hum/machine`, then discover platform/hostname. |
| `XDG_CONFIG_HOME` | Config root, default `~/.config`. |
| `T3CODE_CLI_PATH` | Optional exact T3 executable. Otherwise conventional T3 CLI paths are discovered. Unknown exact thread status protects the environment. |
| `HUM_NOTIFY` | `none` by default; `desktop` uses macOS Notification Center or Linux `notify-send`; `ghostty` uses a discovered Ghostty terminal on macOS, falling back to Notification Center. |
| `HUM_REMOTE_EVENT_PATH` | Remote event file for `relay`. Default `.local/state/hum/<session>/events.jsonl`, relative to the SSH user's home. Set explicitly when remote state uses another root. |

State records command strings, local paths, owner IDs, shares and process births.
Keep it private and outside the repository. Do not put secrets in command-line
arguments; they also appear in the visible terminal and event log. Managed JSON,
launch artifacts and archived logs use private permissions.

`--` preserves individual command arguments. Use an explicit `sh -c '...'` if
you want shell syntax such as a pipeline, rather than accidental interpretation
of an argument's spaces or punctuation.

## Ownership and stopping

Preview and task claims expire after two hours unless given another positive
TTL, up to 30 days. Reuse renews/adds a claim without restarting. Release affects
only the named owner; the final release may stop the bound run. Persistent
environments do not expire. Cleanup refuses legacy/unclassified records,
unknown owner status and mismatched run or process identities.

Explicit `restart`, `down` and `rm` can interrupt shared work. They require the
caller's authority; the CLI is not an authorization service. `rm` is the explicit
stop-and-remove command, rather than a way to bypass cleanup protections.

On Linux, signaling uses pidfds when available and rechecks process births.
macOS has no equivalent pidfd path here; stopping rechecks the birth timestamp
immediately before signaling, but does not provide Linux's atomic PID pinning.
Safe empty-terminal close is Linux-only and requires `/proc` plus pidfds. It
protects active jobs, focused panes, parent worktree groups and unknown identities,
then archives scrollback while retaining command, policy and application data.
The source and state directories must remain trusted; this is not a security
boundary for hostile users who can rewrite the same account's process state.

## Optional host setup

The files under `templates/` are examples, not an installer. Replace their
explicit path placeholders and match the same session/state/Herdr executable
used interactively. Nothing copies, loads or enables them automatically.

- **Linux:** `templates/systemd` contains a user service, fifteen-minute timer,
  and optional empty-terminal drop-in. Both commands initially use `--dry-run`.
  Review their JSON results before choosing actual cleanup and explicitly
  installing/enabling the timer. Empty-terminal pruning is a separate choice.
- **macOS:** the launchd example runs `hum relay` with desktop notifications.
  It requires explicitly saved Herdr SSH machines and existing remote event
  files. Loading it starts a relay; review the paths and notification choice
  first. No macOS terminal-pruning service is included.

Notifications cover commands sent through hum. Crashes and manual Ctrl-C do not
emit events. Event recording runs in a short child process and is best effort;
a completed `up` is not delivery confirmation. `relay` tails only new remote
lines, retries lost connections, and never creates a remote directory/file.
Sharing uses Tailscale Serve, not Funnel. New shares use a free port and save a
local ownership receipt only after the created root route is verified. Existing
unowned routes are never adopted, even if their proxy points at the same app.
Legacy share records without a receipt require manual inspection and remain
protected. A recorded route is reused or removed only when its hostname, sole
`/` handler, proxy and HTTPS layout still match its fingerprint. An added path,
another hostname on the port, or any active Funnel flag prevents changes. Ports
with leftover `AllowFunnel: true` flags are excluded from new allocation too.
Bind apps to loopback and confirm the app port and peer access.

Tailscale has no per-route ownership token or conditional-update API here: the
receipt is local evidence, not provider-enforced ownership. Serialize other
Serve/Funnel configuration writers. An external route recreated with an
identical layout cannot be distinguished, and changes after verification cannot
be atomically excluded. If post-creation verification fails, hum reports the
failure without adopting or deleting an unverified route; inspect it manually.

## Offline checks

```sh
python3 -m unittest discover -s hum/scripts/tests -v
python3 hum/scripts/install.py --help
```

These tests cover shared ownership, expiry, exact owner checks, recycled process
identities, run generations, lock ordering, dry-run behavior, route preservation,
focused/live/changed terminals, retained logs, private artifacts, safe argument
handling, optional notifications and non-overwriting installation. The fake
Herdr test proves an offline cleanup cannot start a server. It does not prove
the installed Herdr's real API, SSH, Tailscale, desktop delivery or a real process
stop/close round trip.

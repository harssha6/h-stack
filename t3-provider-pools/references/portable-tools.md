# Portable provider tools

These tools package the portable parts of the local provider workflow. They
have no default account, executable, account directory, model list, upstream
gateway or live settings path. They do not read credential files themselves.
Native authentication stays with the user-selected native client/account home.

Python 3.10+, macOS or Linux is required. All commands below use `<skill-dir>`
for this installed skill's directory. None of the tools installs dependencies,
modifies a provider, starts an inference turn or copies an OAuth credential.

## Native apps over stdio

`scripts/codex-apps-bridge.py` serves a local newline-JSON MCP connection on
stdin/stdout. Its child process is the explicitly selected native Codex
executable with `app-server --stdio`. There is no HTTP listener, remote admin
endpoint or bearer-token argument. Access is controlled by the process owner,
the host's MCP permissions and the native account. Do not expose this stdio
connection through an unauthenticated network relay.

Create a private JSON config using the [bridge config schema](bridge-config.schema.json):

```json
{
  "version": 1,
  "nativeExecutable": "/absolute/path/to/codex",
  "nativeHome": "/absolute/path/to/selected-native-account",
  "allowedTools": {
    "saved_link_search": "exact.native.tool.name.from.your.client"
  },
  "timeoutSeconds": 30
}
```

Use the installed native client's supported tool-discovery surface to obtain
the original tool names. Do not guess tool names or derive a write/read policy
from naming patterns. Only explicitly configured aliases are published. No
wildcard/all-tools mode is provided. Permission to expose a capability does not
authorize every action it can perform; the calling agent must still honor the
user's authority for external writes and paid operations.

Validate without starting Codex:

```sh
python3 <skill-dir>/scripts/codex-apps-bridge.py --config /absolute/path/bridge.json --validate-only
```

For an authorized MCP setup, point the host to this command with its ordinary
stdio transport. Edit only the selected host configuration after checking its
current schema and user authority:

```sh
python3 <skill-dir>/scripts/codex-apps-bridge.py --config /absolute/path/bridge.json
```

The adapter performs native initialization, creates one ephemeral thread, and
discovers the `codex_apps` server's tool schemas. It does not submit a model
turn. It preserves input/output schemas and annotations while omitting connector
metadata. It forwards an allowed `tools/call` once to that exact native tool.
Native account permissions remain in force. Approval/login requests from the
native server receive a refusal directing the user back to the native client.

The child inherits a small OS environment allowlist plus the selected
`CODEX_HOME`; inference tokens, API keys, proxy variables and other provider-home
selectors are not inherited. This is account routing, **not an OS sandbox**.
The child still runs as the same OS user and can access files that user can.
Use separate OS users or another real isolation boundary when that is required.
No credential is accepted in this tool's JSON config or CLI flags. Keep the
config private because account paths/tool choices can themselves be sensitive.

Native RPC errors and stderr are not forwarded. An app result with `isError`
true becomes a fixed generic tool error; its content and structured payload are
not forwarded. That reported app failure leaves the session usable, without an
automatic retry. Successful app results go to the
authorized MCP caller and may contain private data; this is not a content
redaction service. Never publish those results or use tools that return secrets
without the appropriate authority.

Requests have bounded message sizes, queues, pagination and timeouts. Native
RPC errors or timeouts disable that route until an explicit adapter restart. A
timed-out call might already have changed external state: inspect its outcome
before deciding whether to retry. The adapter never retries calls. It supports
sequential requests only; cancellation cannot prove a remote action was undone.

### Protocol compatibility

The outer adapter supports MCP JSON-RPC 2.0 over stdio, with protocol version
2025-06-18, `initialize`,
`notifications/initialized`, `ping`, `tools/list` and `tools/call`. It publishes
one complete allowlisted tool page. It does not implement HTTP, SSE, resources,
prompts, subscriptions or concurrent request execution.
If a client requests another protocol version, initialization reports
2025-06-18; the client must accept that version or disconnect. The adapter does
not mislabel output schemas, structured content or resource links as an older
MCP version.

Native Codex app-server is a separate, experimental protocol. This release uses
the local workflow's `initialize`, `initialized`, `thread/start`,
`mcpServerStatus/list` and `mcpServer/tool/call` contract. Native envelopes may
omit the `jsonrpc` field. Installed versions can differ; inspect their current
schemas. Unsupported responses fail visibly. Fake-native tests prove this
adapter's contract and failure behavior, not compatibility with every version.
Real native-account and T3-host interoperability remains unverified in this
release because no real account was probed during packaging.

## Discovery-only diagnostics

```sh
python3 <skill-dir>/scripts/check-apps-bridge.py --config /absolute/path/bridge.json --validate-only
python3 <skill-dir>/scripts/check-apps-bridge.py --config /absolute/path/bridge.json
```

The first checks local configuration only. The second starts the selected native
process and checks initialization and discovery. It **does not call an app
tool**, use a search query, submit a model turn or claim an authenticated app
read passed. Discovery may refresh native connection state; run it only within
the user's authorized account-diagnosis task. An app read needs a separate,
authorized harmless read through the actual calling host.

## Candidate-only account alignment

`scripts/align-t3-providers.py` reads an explicitly selected settings document
and an explicit update spec. It supports existing `codex` and `claudeAgent`
instances with `config.homePath`; it does not invent a T3 driver, migrate IDs,
create providers or replace the user's native configuration.

Create an update spec using the [alignment schema](alignment-spec.schema.json):

```json
{
  "version": 1,
  "updates": [
    {
      "id": "existing-instance-id",
      "expectedDriver": "codex",
      "homePath": "/absolute/path/to/selected-native-account",
      "binaryPath": "/absolute/path/to/codex",
      "displayName": "Selected account"
    }
  ]
}
```

Without `--output`, validation is read-only:

```sh
python3 <skill-dir>/scripts/align-t3-providers.py --settings /absolute/path/settings.json --spec /absolute/path/updates.json
```

An explicit output writes a **new** mode-0600 candidate file:

```sh
python3 <skill-dir>/scripts/align-t3-providers.py --settings /absolute/path/settings.json --spec /absolute/path/updates.json --output /absolute/path/new-settings-candidate.json
```

The command refuses existing output paths, symlinks and the source path. It
preserves stable IDs, unknown settings, unrelated providers, models and fields
outside the specified display name, executable path and account-home path.
Expected drivers must match, duplicate updates fail, and changed account homes
must not overlap another native instance's home. Existing ancestor identities
(device/inode) catch physical aliases after symlink resolution. NFC-normalized
casefold suffixes conservatively reject aliases and nesting for missing homes,
including on case-sensitive hosts, so a candidate is portable to macOS.
All native instances in the settings document must have explicit homes; an
implicit/default home prevents this tool from establishing path isolation.
The native directories are not created or inspected for credentials.

The candidate contains the existing settings, which may themselves include
secrets. It stays local with private permissions. No settings body, account
identifier or home path is printed by this command. Do not commit it. Compare
the private candidate and current settings yourself, validate against the
installed T3 schema, and obtain the task's authority before applying it through
T3's supported configuration surface. There is deliberately no apply/reload
flag. A candidate does not prove account authentication, model entitlement,
quota isolation or connector access.

## Deliberately deferred

The private gateway shim is not copied. Its upstream identity injection,
authentication and quota semantics are specific to a separate gateway contract.
A generic HTTP relay would not prove those behaviors work or release the
gateway. A future adapter needs an explicit public upstream protocol, separate
protected local/upstream credentials, TLS verification, streaming contract and
failure/accounting tests. No private gateway endpoint, identity or model catalog
is included here.

Proxy installation, account login, native-app registration and automatic live
settings mutation also remain outside this package.

## Offline verification

```sh
python3 -m unittest discover -s <skill-dir>/scripts -p 'test_*.py' -v
python3 <skill-dir>/scripts/codex-apps-bridge.py --help
python3 <skill-dir>/scripts/check-apps-bridge.py --help
python3 <skill-dir>/scripts/align-t3-providers.py --help
```

Fixtures use temporary directories and a fake native process. They cover
handshake and routing, app error propagation, metadata removal, selected-home
and environment isolation, native requests/notifications/unrelated IDs,
pagination, malformed/oversized messages, credential-bearing errors, timeouts
without replay, discovery-only evidence and protected candidate writes.

---
name: t3-provider-pools
description: Plan or diagnose separate provider accounts and configuration homes in T3 Code, including local proxy routing and missing app or MCP connections. Inspect the installed versions and owning layer before changing account or provider configuration.
---

# T3 Provider Pools

Keep the user's chosen accounts separate and prove which route a T3 session
actually uses. This workflow requires an installed T3 version
that supports the intended provider configuration, the relevant native clients,
and authorized access to their local configuration. A proxy is optional; when
one is used, its installation, license and compatibility must be checked
separately. Portable stdio app-bridge, discovery-check and candidate-alignment
helpers ship here; they do not install a proxy, log in, copy credentials or edit
live T3 settings. Read [portable tools](references/portable-tools.md) before
using them, including their experimental native-protocol compatibility limits.

The helpers require Python 3.10+ on macOS or Linux. Their offline tests use fake
native executables and temporary account directories only. A passing test does
not establish that a real account or installed T3/Codex version works.

## Establish The Supported Configuration

Discover installed versions and supported commands from each executable's help,
current official documentation and local schemas. Do not invent flags or copy
another machine's paths. Inspect the current T3 provider catalog and configured
instances; a catalog entry alone does not prove an account can use that model.

In versions that expose `providerInstances` and `config.homePath`, inspect those
fields to locate each instance's native home. Confirm they are supported before
editing them. Common native home selectors include `CODEX_HOME` and
`CLAUDE_CONFIG_DIR`; verify their installed-client behavior. Do not change a
provider to an OpenAI-compatible driver unless T3 actually supports that driver.

Build a small private inventory for the selected pools:

| Layer | What to establish |
|---|---|
| T3 | Environment, stable instance ID, driver, selected model and native home |
| Native client | Effective configuration, inference route and authentication status |
| Proxy, if present | Process owner, version, listener, upstream mapping and credential store |
| Account | User-selected identity, permitted use and applicable quota |
| Apps and MCP | Intended app identity, transport, authorization and host exposure |

Record secret locations and redacted field names, never secret values. Prefer
supported status commands over dumping credential files, full configs or logs.
The inference account and app account may legitimately differ; do not silently
make them match.

## Diagnose Before Repairing

Trace a failure through the exact selected pool:

1. **Transport:** can the client reach its configured listener and can the proxy
   reach its actual upstream? Separate DNS, VPN, TLS and timeout failures from
   authentication or quota. Do not disable certificate checks or change system
   routing to make a probe pass.
2. **Inference authorization:** inspect a bounded, redacted error from the owning
   client or proxy. Distinguish expired credentials, account entitlement, model
   mapping and explicit usage limits. A generic demand message proves none of
   these by itself. Account quota may be shared across machines.
3. **Protocol:** confirm the upstream supports the client's wire format, tool
   calls and requested reasoning/options. A plain-text response does not prove
   that an agent session with tools will work. If several upstreams advertise
   one model name, inspect documented routing rather than assuming one account.
4. **Connector authorization:** a working model login does not authorize apps.
   Inspect the intended native account's app or standalone MCP status separately.
5. **Host exposure:** distinguish absent tools, failed MCP startup and a real
   tool-call error. A connector working in a native client does not prove T3
   exposes it in the selected provider session. A supported CLI may be the
   intended access surface; absent MCP access alone is not a fault.

Inspect one failing path before widening the audit. Never rotate accounts,
switch providers or repeatedly prompt for OAuth to conceal a transport or host
limitation. Stop model dispatch on explicit auth, quota or rate-limit failures
and report the owning layer; do not automatically spend another account's quota.

## Prepare A Change Within Its Authority

A diagnosis request stays read-only. For an authorized setup or repair, describe
the selected account, exact configuration fields, affected sessions and rollback
before editing. A new pool, provider, proxy service, account login, shared
credential route or global setting needs authority within the user's task;
installing this skill grants none.

- Prefer supported independent homes and login flows for separate identities.
  If a proxy pools credentials, use its documented isolation mechanism; verify
  that one pool cannot silently route to another pool's accounts.
- Keep inference API keys distinct from proxy management credentials. Use
  protected local stores and a loopback listener unless another exposure is
  explicitly required and secured. Do not paste tokens into prompts or commands
  that expose them in process listings or shell history.
- Authorize each machine through supported flows. Do not copy or synchronize
  OAuth/refresh credential files. For headless login, discover the supported
  device or callback flow; a temporary tunnel needs explicit scope and cleanup.
- Back up only affected configuration with private permissions. Preserve
  unrelated instances, native apps, plugins, MCPs and user edits. Do not replace
  an independently authorized home or attach every connector from another one.
- Keep instance IDs stable while threads depend on them. Test a candidate route
  before reconfiguring existing threads. A settings write does not prove a
  reload occurred; inspect the installed client's reload behavior.
- Inspect process ownership and in-flight work before a required restart.
  Follow the user's process manager and lifecycle rules. Do not kill shared
  clients or services merely to refresh a tool catalog.

If the proposed solution depends on a private bridge or an unbundled helper,
name that missing dependency. Do not invent its command or claim the setup is
portable merely because the instruction file exists.

## Verify The Selected Route

Start with non-inference evidence: configuration structure, process status,
supported auth status and the live T3 catalog. Paid model probes and external
service calls require the user's applicable authorization and budget.

When runtime checks are authorized, use a bounded request with a hard timeout,
limited output and no automatic fallback or repeated retries. Check the native
client, then the actual selected T3 provider session. If an agent test is
necessary, use authorized delegation; do not create a top-level thread just to
probe a pool. Preserve existing user conversations.

For missing connectors, verify a fresh selected session can make one harmless
authenticated read through the intended host. Tool discovery or a successful
JSON-RPC envelope alone is not that proof. Avoid creating or modifying service
data, and redact returned private content.

Report the tested pool and layer, evidence obtained, changes made and rollback,
and anything untested or blocked. Keep configuration validity, native-client
success, T3 inference and T3 connector access as separate claims.

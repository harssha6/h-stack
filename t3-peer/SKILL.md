---
name: t3-peer
description: Coordinate authorized work in T3 Code on another linked machine, or transfer selected working files and notes into a fresh isolated checkout using an explicit offline handoff artifact.
---

# T3 Peer

Run work where the required checkout, application or login already exists. This
uses T3's native linked-environment tools for coordination. It requires T3 on
both machines and access to the relevant tools in the calling harness. Tool
names and fields vary by version; inspect their current schemas.

This export does not include the legacy peer MCP client, token-login or renewal
helpers, or legacy Git/Syncthing transfer scripts. For an explicit file transfer,
use the independent [selected-file handoff](references/handoff.md), with a
versioned artifact and a fresh destination. It does not copy credentials or
conversation history automatically and does not bundle Git history.

## Find The Right Environment

1. Read the caller's environment identity and linked-environment list. Current
   tools may be named `t3_environment_read` and `t3_environment_links`. Match the
   machine the user named; do not infer it from the caller's operating system.
2. Keep unreachable, expired and unlinked states distinct. A stored link is not
   proof that the machine answers now. If a named machine needs linking, use
   T3's native link card when available. Supply only an address the user gave;
   do not guess private endpoints or collect pairing codes or tokens in chat.
   A pending card is not a completed link. Follow the tool's asynchronous
   instructions rather than polling or opening duplicate cards.
3. Inspect remote projects and capabilities using the selected environment ID.
   Match repository identity and the remote checkout, not just a project title.
   Local absolute paths do not establish where files live on the other machine.
4. Discover the available providers, models, options and permitted runtime modes
   on that environment. Preserve the user's selection and authority ceiling.
   A missing model does not authorize a new provider, account or fallback.

If native remote tools are absent, report that prerequisite. Do not silently
install a credential bridge or substitute a remembered private setup.

## Choose The Work's Owner

- **A bounded task whose result belongs here:** use the native delegation tool
  if delegation is authorized. In current T3 versions, `delegate_task` accepts
  the remote environment through `target.environmentId`. Record its task ID,
  child thread ID and returned link. For independent code changes, choose a
  supported isolated checkout and identify its starting commit. Uncommitted
  changes in the caller's checkout are not included automatically.
- **An existing conversation the user wants to continue:** read the selected
  remote thread first, then send the requested continuation to it. Preserve
  its workspace and outstanding work; do not launch a replacement casually.
- **A new top-level conversation:** create one only when the user requests that
  ownership. Select the remote project or supported scratch workspace explicitly.
  A top-level thread is not a substitute for a delegated audit.

The task's message must stand alone. Include the goal, repository and intended
checkout, relevant commit or branch, current evidence, authorized changes,
constraints, acceptance checks and where to return the result. State which
files or artifacts the remote agent actually has. Do not forward secrets or
unnecessary private conversation content.

Read-only work belongs in the task brief. A runtime approval mode alone is not
a read-only guarantee. Existing permission to work does not grant permission to
publish, merge, delete unrelated work or send external messages.

## Follow The Actual Work

- A successful launch or send means accepted, queued or running as reported;
  it does not prove completion. Record the returned IDs before any follow-up.
- For delegated work, follow its completion notification and task-status tools.
  When the tool says completion will wake the parent, continue independent work
  or end the turn; do not poll a running task or wait through its thread instead.
- For top-level threads, use the thread read/wait tools with the same remote
  environment and thread ID. Keep reads small and paginate when necessary.
  A timeout does not cancel work. An idle thread or a finished turn can still
  have unsettled children; inspect the returned work state before calling it done.
- An approval or question is a waiting state. Surface it through the supported
  request mechanism; do not answer a user-only approval on the user's behalf.
- Inspect the actual final result and evidence. Report failed, cancelled,
  interrupted, blocked and completed states accurately. Cancel delegated work
  through its task-cancellation tool; interrupt a top-level thread only when
  that is the intended scope.
- After a lost launch response, use the documented idempotency key when
  supported. Otherwise reconcile the remote thread/task list before retrying;
  do not create duplicate workers merely because the response was lost.

## Continue On Another Machine

For a continuation, prepare a compact handoff containing:

- The user's goal and decisions already made.
- The exact repository, branch and commit the receiving checkout must contain.
- Dirty or untracked changes and whether they are available remotely.
- Completed checks, unresolved failures, relevant artifacts and the next action.
- Which thread now owns edits and how the result should return.

Use an existing authorized code-sharing mechanism when files must move. Check
its destination and privacy separately. Never claim a branch, dirty files or
credentials arrived merely because the handoff message did. The receiving agent
must inspect its checkout and report missing state before editing. Avoid two
agents editing the same checkout during an ownership transfer.

For the bundled offline mechanism, read [the handoff contract and commands](references/handoff.md).
Select every file and a reviewed note explicitly. Preview before applying;
verify the artifact digest and base commit through a trusted channel. Receive
only into a new envelope using a local known base, never over the user's
existing checkout. A missing base needs a separately authorized clone/fetch;
do not silently fall back to exporting history or credentials.

Finish with the machine label, returned task/thread link, observed state and
remaining work. Reuse the tool's link rather than constructing one that may open
in the wrong T3 instance. A handoff sent is not a handoff completed.

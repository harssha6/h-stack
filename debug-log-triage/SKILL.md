---
name: debug-log-triage
description: Use when debugging local dev servers, background jobs, imports, batch work, AI calls, embeddings, queues, billing, sync, browser-to-backend requests, HAR captures, or any subsystem with searchable logs. Helps avoid reading full logs blindly.
---

# Debug Log Triage

Goal: inspect the smallest useful log slice with the right marker, then connect it back to the runtime owner.

## Workflow

1. Identify the failing subsystem and the action that should produce logs.
2. Find the repo's log surface: terminal session, `logs/`, dev wrapper, cloud log command, CI output, or provider dashboard.
3. Search by marker, request id, job id, route, timestamp, or error token before reading large log files.
4. Read surrounding context around matches.
5. Separate cause from symptom: app error, provider error, queue state, DB write, auth/session, network, or UI polling.
6. After a fix, trigger the same action and re-check the same marker.

## Browser Network Escalation

When the browser is the only observable path to a suspected request problem:

1. Reproduce one real, narrow flow and capture a HAR or network trace.
2. Correlate its request URL, status, timing, and response shape with the app's
   route, logs, session, and persistence owner.
3. Redact credentials, cookies, authorization headers, CSRF values, and private
   payloads before storing or sharing any artifact.
4. Use the trace to explain or reproduce the request. Do not mistake it for an
   invitation to bypass auth, rate limits, or access controls.

## Marker Pattern

When adding logs, prefer:

```ts
console.log("[SUBSYSTEM] concise event", { id, status });
console.error("[SUBSYSTEM] concise failure", error);
```

Use emojis only if the repo already uses them; bracket tags are the searchable contract.

## Rules

- Do not paste huge logs into the answer.
- Do not rely on the visible UI when the failure is owned by a job, queue, provider, or DB write.
- Do not add permanent noisy logging unless the repo has a debug flag or marker convention.
- Redact secrets and tokens in any report.

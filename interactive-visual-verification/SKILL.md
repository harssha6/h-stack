---
name: interactive-visual-verification
description: Test a real visual or interactive product flow across browser, desktop, and iOS simulator surfaces. Use when work needs clicks, typing, gestures, hover, responsive states, authenticated browser state, screenshots after interaction, HAR capture, or proof that a user flow works beyond source and static screenshots, especially when routing verification between Codex Desktop, Codex CLI, Claude Code, and Cursor.
---

# Interactive Visual Verification

Prove what a user can do and see. A screenshot, source read, or model opinion is not proof that an interaction works.

## Choose The Control Surface

1. When the active task is Codex, use its native Browser or Computer Use tools.
   Prefer Browser for web interaction; reserve Computer Use for Mac apps,
   Simulator, or a browser case Browser cannot handle.
2. When the active agent is not Codex, delegate interaction testing to the
   local Codex CLI. Tell it explicitly to use the `computer-use` MCP tool; it
   does not need a special Computer Use mode.
3. Run delegated tests in an ephemeral, read-only Codex process. The process may
   use Computer Use for the declared test actions, but must not edit the repo.
4. Fall back to the repo's normal deterministic browser or UI-test runner only
   when the Codex delegation cannot access the needed surface or the test is
   better expressed as repeatable automation.
5. Use the named browser and its existing session when the user names one. Do
   not silently substitute a signed-out profile or another browser.

## Run The Verification

1. State the user-visible claim and the action that proves it.
2. Capture the baseline when the regression, visual delta, or current state
   matters.
3. Perform the actual sequence: navigate, click, type, scroll, resize, hover,
   gesture, reload, or relaunch as the claim requires.
4. Re-inspect the live state after every consequential action. Re-resolve UI
   elements instead of reusing stale coordinates or accessibility references.
5. Capture evidence at meaningful states: before/after screenshots, visible
   copy, URL/route, console or app logs, API/DB result, and test output as
   applicable.
6. Report the control surface, actions performed, observed result, artifacts,
   and any limitation. Do not call an unexecuted path verified.

## Browser Fallbacks

- Use an existing Playwright, Cypress, Webdriver, or app-specific E2E setup
  when the active harness has no browser control. Prefer the repo's normal
  runner over installing a new framework for one check.
- A deterministic browser test can prove interaction, but it is not proof of a
  user-specific signed-in session unless it used that real session.
- When no interactive browser surface or existing runner is available, stop at
  the strongest available evidence and label browser interaction unverified.

## HAR To Read-Only Client

Escalate from browser control to a local client only when all of these hold:

- the same read-only browser workflow recurs enough to justify it;
- no supported API or owned backend path covers the need;
- the user owns the account or explicitly approves the external surface; and
- browser capture can prove the request contract without bypassing controls.

1. Run the real browser flow once and record a HAR or equivalent network trace.
2. Inspect it locally. Do not commit or share cookies, authorization headers,
   CSRF values, signed URLs, personal data, or full HAR files by default.
3. Derive the smallest read-only client that makes only the needed request.
   Preserve the site's authentication, rate-limit, and access constraints.
4. Compare its result with the browser output on the same input. Keep a browser
   check for contract drift rather than treating the derived client as canonical.
5. Store only durable request-shape knowledge and a local redacted fixture when
   needed. Do not make an undocumented client the owner of data we already own.

Use this for a legacy or third-party UI that has become a repeated bottleneck,
not for one-off browsing or for products with a supported API, direct DB owner,
or existing application route.

## Delegate From Another Harness

When your Codex configuration exposes a `computer-use` MCP server to
`codex exec`, provide a narrow test brief, target app or URL, allowed actions,
expected observable result, and required artifacts.

```bash
codex exec --ephemeral -C "$REPO" --sandbox read-only \
  'Use the computer-use MCP tool to verify this exact flow. Do not edit files.
   Target: <app or URL>. Actions allowed: <click/type/scroll sequence>.
   Expected result: <observable result>. Capture <screenshots/logs/route> and
   report executed actions, observed result, artifacts, and any limitation.'
```

Do not ask Codex whether it has Computer Use. Tell it to call the tool for the
actual test. A harmless `list_apps` call is the health check when the tool may
be unavailable.

## iOS Rules

- Prefer an available `iPhone 17`; discover its simulator ID at runtime and
  never hardcode it.
- Build, install, launch, and screenshot with `xcrun simctl` when those actions
  cover the claim.
- For taps, typing, scrolling, gestures, or system UI, use an existing XCTest
  UI test or the active harness's Computer Use capability. `simctl` alone does
  not make an ad hoc interactive test.
- Treat compile success and a single launch screenshot as insufficient for a
  navigation or interaction claim.

## Guardrails

- Never claim a visual flow passed from source inspection, a diff, or a static
  image alone.
- For a non-Codex agent, delegate visual interaction to Codex CLI before using
  Puppeteer, Playwright, or another normal browser automation fallback.
- Do not convert an authenticated third-party website into a mutation client.
  Read-only automation is the default; ask before any action that changes
  external state.
- Do not send, publish, purchase, change credentials, or accept terms while
  testing without the appropriate user authorization.
- Use `rendered-output-verification` to decide whether rendered proof is
  required. Use this skill to execute and document an interaction-level check.

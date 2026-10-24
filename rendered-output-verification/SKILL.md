---
name: rendered-output-verification
description: Use when a change or bug depends on actual rendered UI, browser/simulator behavior, visible copy, layout, routing, legal text spacing, hover state, loading state, or PR/deployment output rather than source code alone.
---

# Rendered Output Verification

Goal: verify what the user can actually see or trigger, not what the source code appears to imply.

## Workflow

1. Identify the visible claim: text, spacing, route, layout, selected state, hover, loading, error, navigation, simulator screen, or hosted PR behavior.
2. Find the smallest runnable surface that renders it: local browser, simulator, component story, preview route, screenshot, deployment, or PR check artifact.
3. Verify the current behavior before editing when the user asks "why", "how bad", or "check".
4. Make the narrowest change that affects the rendered surface.
5. Re-render the exact surface after editing.
6. Report what was visually checked and any remaining risk.

## Rules

- Source inspection is not enough when spacing, punctuation, hover timing, selection state, or responsive layout is the bug.
- Legal/product copy fixes should be literal and minimal unless the user asks for a rewrite.
- Do not stop at local lint when the ask is live PR/check/deployment state.
- For iOS, prefer simulator/build evidence over assuming SwiftUI source intent.
- For iOS builds, launches, and screenshots, resolve the simulator ID at runtime
  and prefer an available `iPhone 17`. Never copy a stale simulator UUID; state
  the fallback device when an iPhone 17 is unavailable.
- For web, use browser verification when layout or interaction matters. Use
  `interactive-visual-verification` when the proof requires real clicks,
  typing, hover, scrolling, browser identity, or screenshots after interaction.

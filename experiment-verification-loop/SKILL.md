---
name: experiment-verification-loop
description: Use when the user wants to test a falsifiable product claim, compare variants or approaches, run a pilot, validate model behavior, or decide whether an experiment worked. Ordinary browser or simulator QA alone does not trigger this skill.
---

# Experiment Verification Loop

Goal: force claims onto a small falsifiable slice, then verify the live or persisted surface that owns the truth.

## Workflow

1. Define the decision and claim being tested, including what result would change the decision.
2. Pick the smallest meaningful slice: a pilot subset, one route, one session, one simulator flow, one prompt variant set, or one artifact batch.
3. Keep control and variant boundaries explicit.
4. Use real inputs and the repo's actual runtime path when the result must appear in product UI.
5. Write or preserve artifacts when experiments need later comparison.
6. Verify the owner surface: browser, simulator, DB row, API response, generated file, sheet/Drive state, PR/check state, or system tool.
7. Report the delta, confidence, decision supported or weakened, and whether the experiment should ship, iterate, or be discarded.

## Rules

- Prefer 2-3 concrete variants over a blob of theoretical options.
- Do not introduce regex or substring matching as product logic or as the
  success criterion for an AI prompt, generation pipeline, API payload, or
  workflow. A regex may identify candidates to inspect, but proof comes from
  structured fields, domain invariants, persisted/provider payloads, and the
  resulting user-visible or generated artifact.
- Do not mutate live state for exploratory work unless the user asked for product-visible output.
- Do not pad underfilled outputs or hide failed configured paths with placeholder content.
- If the user says "I'll test", keep the dev server or artifact accessible and report the exact surface to test.
- If an experiment is wrong, stop and revert or redirect instead of polishing the wrong direction.

## Good Outputs

- "Control vs variant A vs variant B."
- "Tested on this exact slice."
- "Evidence lives here."
- "This proves X, but does not prove Y."
- "Next step: ship, iterate, or discard."

---
name: prompt-forensics
description: Use for AI generation systems when the user asks why a prompt, edit, image reference, model call, title, style, composition, palette, fallback, or generated output behaved a certain way.
---

# Prompt Forensics

Goal: explain generation behavior from the actual prompt/model/runtime path, not from plausible prompt-storytelling.

## Workflow

1. Identify the failed or confusing output.
2. Trace the full authority path: user input, selected axes, source packet, library/retrieval, intermediate model call, structured fields, prompt assembly, image attachments, provider request, job row, and persisted output.
3. Separate axes that often get blurred: title text, title style, composition, palette, identity, scene/body prompt, negative prompt, reference image role, and render attachment.
4. Check whether the model actually received the image/text/reference the user expected.
5. Detect duplicated or conflicting authority blocks before blaming the provider.
6. Distinguish fallback categories explicitly: legacy data source, offline/no-provider path, retry behavior, and hardcoded creative fallback after configured failure.
7. Report the exact layer that owned the behavior and the narrowest fix.

## Rules

- Persisted traces, provider payloads, job rows, and stored prompts beat UI labels.
- Render-facing text should stay compact; raw evidence belongs in debug/audit surfaces.
- Regex can locate a suspect prompt fragment or log candidate, but never proves
  semantic prompt correctness or pipeline behavior. For validation and tests,
  inspect or assert structured prompt fields, the final provider payload,
  persisted job/output provenance, and the rendered/generated result. Prefer
  parsers, schemas, typed objects, and domain assertions to string-pattern
  matching.
- Configured model failures should fail loudly unless the product explicitly defines a safe fallback.
- Do not answer "the model should know" without checking what the model was actually sent.

## Output Shape

- **What happened**
- **What was actually sent**
- **Which axis owned it**
- **Why it conflicted or failed**
- **Fix**
- **Verification**

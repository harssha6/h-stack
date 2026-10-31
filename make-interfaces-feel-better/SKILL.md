---
name: make-interfaces-feel-better
description: Improve an existing web or iOS interface when the user asks for clearer hierarchy, controls, states, or interaction quality. Use the current product and workflow as the starting point.
---

# Make Interfaces Feel Better

Goal: improve the actual working interface, not just decorate it.

Start by identifying the product mode:

- **Operator tool**: dense, scan-friendly, low-drama, fast repeated use.
- **Consumer product**: emotionally legible, content-forward, clear next action.
- **Marketing/editorial**: brand/product first, image-led, sparse copy.
- **Design-system work**: tokens and primitives before call-site churn.

## Default Workflow

1. Inspect the current UI surface and its real data/state owner.
2. Name the user's complaint in interface terms: hierarchy, affordance, density, pacing, copy, motion, state, or layout.
3. Remove dead chrome, inactive controls, duplicate labels, and decorative clutter before adding new elements.
4. Make visible controls real. If a control is shown before an action, wire it into that action path.
5. Preserve feature parity unless the user explicitly asks for a simplification.
6. Keep selected objects, progress, failure location, and provenance visible when those states matter.
7. Verify the rendered result on the target platform.

## Cross-Platform Taste Rules

- Keep layout stable under dynamic content; text and controls must not overlap.
- Prefer role-based spacing, typography, and surface hierarchy over one-off visual fixes.
- Use fewer, clearer states instead of more labels explaining what the UI does.
- Make the primary object obvious: current show, current story, current file, current task, current screen.
- Copy should orient, state, and command. Avoid marketing language inside operational tools.
- Empty/loading/error states should explain the next useful truth, not fill space.
- If the same treatment appears three times, consider a shared utility or component.
- Do not hide a data/query problem with client-only visual filtering when counts, pagination, persistence, or ownership matter.
- Do not argue with precise product wording or visible-copy corrections once the user clarifies the target.

## Platform References

Read only the reference that matches the task:

- Web/React/Next/Tailwind: [references/web.md](references/web.md)
- iOS/SwiftUI: [references/ios.md](references/ios.md)

## Output Standard

When reporting UI work, say:

- what visible problem changed;
- what state/path was verified;
- which shared component, token, or local surface owns the change;
- any remaining visual risk.

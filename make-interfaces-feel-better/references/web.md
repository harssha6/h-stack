# Web Interface Polish

Use existing component libraries and local helpers first: shadcn/ui, Tailwind utilities, app tokens, route-local components, and existing layout primitives.

## Web Defaults

- For operational apps, start with the working surface, not a hero.
- Keep cards for repeated items, modals, or genuinely framed tools. Do not nest cards.
- Prefer server-backed filtering/search/pagination when counts or result integrity matter.
- Use icons for common tool actions when a familiar symbol exists.
- Make responsive constraints explicit with grid tracks, aspect ratios, min/max widths, and fixed control dimensions.
- Verify text fit on mobile and desktop; do not scale fonts with viewport width.
- For visual changes, inspect in browser, not only with lint/build.

## Common Fix Patterns

- Dead first-run controls: hide until actionable, or wire them into the initial action path.
- Hover previews: preload, keep a stable base layer, and avoid blank frames.
- Dense workbench pages: reduce copy, keep provenance/debug affordances visible, avoid decorative panels.
- Gallery/filter work: apply filters at the data/query layer if pagination or counts exist.
- Landing pages: establish the audience, product story and first-viewport composition before styling individual controls. An installed art-direction skill can help, but is optional.

## Verification

- Run the repo's lint/typecheck/build as appropriate.
- Use Playwright, browser tools, or system Chrome for visual behavior.
- Check desktop and mobile when layout or text could shift.

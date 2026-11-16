---
name: screenshot-variant-mocks
description: Mock UI variants directly on real device or browser screenshots. Measure the screenshot, erase only the element under test, redraw it with the product's real fonts and tokens, put the variants side by side, score them with two configurable vision judges, and browse them in an interactive viewer (inline in T3 and as a standalone HTML file). Use when someone wants to see options for a small UI change in context ("show me ways to…", "mock a few variants", "what if the caption had an icon"), compare treatments of a label, badge, avatar, caption, chip or row, or brainstorm a design decision without building the app.
---

# Screenshot variant mocks

Mock a small UI decision on top of real product pixels, in minutes, without building, installing or editing the product.

The idea: a live screenshot already has the real covers, data, density and chrome. Change only the part under test, using the product's real fonts and tokens, and the variants are judged in their true context. Combine this with `design-reference-research` for references and `original-thinking` when the choice shapes product identity.

## Setup

Paths beginning with `<skill-dir>` refer to this installed skill folder. Python helpers need Python 3.10+ and Pillow (`python3 -m pip install Pillow`). The viewer itself has no external JavaScript, font or image dependencies beyond the images in your manifest. Standalone mode uses relative image files; inline mode embeds them and works offline. Neither requires T3 Code.

Optional browser QA needs Node.js and Playwright, installed in a location you control (`npm install playwright`, then `npx playwright install chromium`). Set `PLAYWRIGHT` to its absolute module directory if Node cannot resolve it, and optionally set `CHROME` to an installed Chrome/Chromium executable.

For scoring, configure your own provider and two vision models it supports:

```sh
export VISION_BASE_URL="https://api.openai.com/v1" # or another compatible API root
export VISION_API_KEY_ENV="OPENAI_API_KEY"       # the name, never the key itself
# Set that key variable securely through your shell or secret manager.
export VISION_MODELS='["your-first-vision-model", "your-second-vision-model"]'
python3 <skill-dir>/scripts/judge_vision.py rubric.json --dry-run
python3 <skill-dir>/scripts/judge_vision.py rubric.json
```

The base URL includes the API version; the script appends `/chat/completions`. Dry-run validates the rubric and images without credentials, network calls or writing scores. Real scoring sends each selected screenshot to the configured provider and may incur API charges. Use only images you may share with it. Scores must be JSON numbers from 1 to 10; failures stay visible in the output and return a nonzero exit status. API keys and provider error bodies are never logged. Keep your manifests and generated viewers trusted: the optional `decision` field accepts HTML.

A minimal `rubric.json` (image paths relative to the file):

```json
{
  "context": "Compare this label treatment in context: {desc}",
  "criteria": {"legibility": "Readable at actual screenshot width", "calm": "Fits the surrounding screen"},
  "items": {"a": {"image": "a.png", "desc": "Current label (control)"}, "b": {"image": "b.png", "desc": "Label with icon"}}
}
```

For a runnable synthetic example covering compositing, all three viewer modes and judge dry-run, see [examples/synthetic.py](examples/synthetic.py). It uses drawn shapes and an installed DejaVu Sans font (or pass `--font /path/to/font.ttf`), with no product screenshots or personal data.

## When it fits
- Small, local treatments such as captions, bylines, badges, avatars, chips, list-row metadata, icon + label pairs, or truncation and empty states.
- When a real screenshot exists or can be captured (device, simulator, browser).
- Not for layout reflows, new screens, motion, or interaction. Prototype those in code. A static composite cannot prove interaction or exact platform text layout.

## Workflow
1. **Collect ground truth.**
   - Get the latest screenshots of the target surface, with a capture date and time zone.
   - Read the component source (read-only) for the type style, colour token, spacing and line limit.
   - Load the font files and colour values from the repo's design-system folder. Never guess them.
   - Note real data quirks: handles, very long names, repeats, missing images, non-person accounts.
2. **Measure, don't eyeball.** Use the helpers in `scripts/svmock.py`:
   - `bands()` finds where cards end and captions begin. `segments()` finds tile columns. `text_box()` gets the exact glyph box.
   - `font_px_for_width()` and `density()` derive px-per-dp/pt from a measured string at a known token size. Check tile widths in dp against the design.
3. **Write a per-project generator** next to the outputs, e.g. `mocks_<topic>.py`. It imports `svmock` and does three things:
   - Erases only the region under test with the measured background colour. Covers and chrome stay untouched.
   - Draws one function per variant, each a single-variable change from the control. Always include the current build as the control.
   - Renders every data state the variant depends on: with data, without data (fallback), and **mixed** coverage. Keep mixed per entity, so the same person gets the same image everywhere (`stable_index`).
   - Also renders the repeated entity case and the longest-text truncation case.
   - Clips anything that would draw under floating chrome, such as a mini player or tab bar (`clip_below`).
4. **Use honest assets.**
   - Use only names and data visible in the screenshots.
   - Photos of people are `placeholder_photo()` silhouettes, labelled as placeholders on every board. Never invent real-looking people or data.
   - When the product has real default assets (e.g. backend default avatars), find them at the source (GitHub/backend repo, read-only), download the public CDN copies into `assets/`, and say where they came from.
   - Two-letter initials are unreadable below about 20dp, so use one letter or a glyph.
5. **Make the outputs:**
   - Boards: all variants on the full screen, close-ups at 1:1 device pixels (true tile width), the special rows (e.g. repeated entity), and photo/fallback/mixed states. Use `board()`.
   - Per-variant judge sheets with an identical layout (full screen + close-up + special row).
   - Stamp every board with: PROPOSAL, not a decision · surface · screenshot date and time zone · what is a placeholder.
6. **Judge with two vision models.** Run `python3 <skill-dir>/scripts/judge_vision.py rubric.json`. Configure an OpenAI-compatible Chat Completions endpoint, credentials and two vision-capable model IDs through the environment (see Setup above). Each item gets one call per judge, with no retries.
   - Write criteria that match the actual risk (e.g. reads-as-person, legibility at tile width, calm across a dense screen, no clash with art).
   - Report scores and errors as recorded. These are model judgments on static mocks, not user tests; treat gaps under 1 point as noise.
   - If a provider fails, report the error and continue other work. Do not silently substitute another provider or model.
   - Use judge feedback to propose new variants, then judge those too.
7. **Build the viewer.** Write `manifest.json` (schema in `scripts/build_viewer.py`), then run:
   - `build_viewer.py manifest.json` → `viewer.html`: standalone, light, relative image paths.
   - `build_viewer.py manifest.json --inline` → `viewer_inline.html`: one self-contained file with every image embedded, for sharing or offline.
   - `build_viewer.py manifest.json --t3` → `viewer_t3.html`: for T3. Images use absolute paths, the page uses theme variables and has no page background, and `embed_defaults` in the manifest sets the starting view, state and columns. In a T3 Code environment with HTML preview tools, run `html_preview` first. The template has no `vh` units, so keep it that way. Then call `html_render` with the content height (max 2000, so pick embed defaults that fit).
   - Viewer features:
     - Variants view: Rows (default) or a 2–4 column grid. Controls: a view segmented control (put the tight element crop first), a grouped coverage menu (`state_groups` with short labels and per-state counts), a picked-only filter, and a column switch.
     - Cards show compact score bars plus the mean, and a note field that expands. A card without the selected state falls back to another state and says which one it is showing.
     - Focus lightbox (an inline panel in T3): ←/→ changes variant, ↑/↓ changes coverage, 1–9 changes view, Z toggles actual pixels, P picks.
     - Compare A/B: side by side, swipe slider, or blink (press and hold to stay on B). Tall phone screenshots are capped at a sensible width.
     - Sortable score table with judge verdicts, and a refs gallery with reference links.
     - Picks and notes persist in localStorage (failing silently in sandboxed frames) and export as markdown or JSON.
   - Verify with `node scripts/qa_viewer.cjs /abs/viewer.html /tmp/out` (set `PLAYWRIGHT=` to any local `node_modules/playwright`; it uses Chromium, or an installed browser selected with `CHROME=`). It drives the grid, coverage menu, focus, swipe, scores and a 390px mobile pass, prints console errors and any clickable without a pointer cursor, and saves screenshots. Review the screenshots before showing the viewer. The QA fixture needs at least two variants, two coverage states and a score criterion.
8. **Report.**
   - Show the boards and link the standalone or self-contained HTML viewer. In T3 Code, optionally render the T3 viewer with its native HTML tools.
   - Give the score table and one recommended variant with its tradeoff.
   - Give the cheapest shippable version and the data or backend changes it needs.
   - Write a README in the output folder with inputs, method, scores, recommendation, decisions (dated with a time zone) and limits.

## Viewer quality bar
The viewer is a design tool and must feel like one. Before changing `viewer_template.html`, load `make-interfaces-feel-better` (the work surface: hierarchy, density, controls, states) and `web-animation-design` (motion).
- **Show the thing under review, not the tool.** The default view is a tight crop of the element being decided (e.g. cover bottom + caption line), and the default layout is Rows: one variant per line, so the reviewed element lines up and the eye scans straight down. Wider context (rail, full screen) is a view switch away. Scores, notes and fallback tags never sit on top of or around the image: scores are behind a toggle, notes live in the focus view, fallbacks are a one-line note in the row label.
- The screenshots are the hero. Controls stay in one quiet toolbar row with no uppercase field labels. Long option lists go in a grouped menu, never a wrapping pill cloud.
- Selected state comes from a sliding thumb or underline (transform, ~220ms ease-out). Popovers enter from scale .97 + opacity in ~150ms. Pressed controls scale to .97. Everything respects `prefers-reduced-motion`. Images swap instantly: they change hundreds of times per session.
- Every clickable gets a pointer cursor and a visible focus ring. Numbers use tabular figures. Text never overlaps: narrow cards switch to short labels (`criteria[].abbr`) through a container query.
- In T3 the page uses theme variables, has no page background and no `vh` units, and the focus view sits inline instead of fixed.

## Rules
- Read-only on product repos and backends. No builds or installs for mocks. No uploads, Slack or sharing unless the user says so.
- Covers, art and chrome stay as captured. If a variant must overlap them (e.g. an avatar on a cover corner), that overlap is what's being tested. Show it honestly, including clashes with progress bars or badges.
- Every variant needs its no-data fallback rendered. A variant that only looks good with perfect data isn't finished.
- Label proposals as proposals. Record the user's decision with a date and time zone when they make one.
- Keep each project's generator next to its outputs so any variant re-renders with one command.

## Files
- `scripts/svmock.py`: measuring, erasing, text fitting, avatars/discs/placeholders, boards, viewer asset helpers.
- `scripts/judge_vision.py`: rubric-driven two-judge scoring to `scores.json` through a configured OpenAI-compatible endpoint.
- `scripts/build_viewer.py` + `scripts/viewer_template.html`: the interactive viewer (standalone, inline, T3).
- `scripts/qa_viewer.cjs`: headless Chrome pass over the viewer with screenshots, console errors and a cursor audit.

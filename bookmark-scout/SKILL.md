---
name: bookmark-scout
description: Once a day, read what the owner saved (bookmarks, liked posts, read-later links) since the last scout, find the saves that could improve one of their projects, ideas or experiments, and try the best ones as cheap evidence (a mock, a preview screenshot, a short recording) so the owner only has to say yes or no. Use in a scheduled morning brief, when the owner asks "anything useful in my bookmarks", or when they share a link saying "try this somewhere".
---

# Bookmark scout

Most people save far more than they ever read. The scout reads the saves for them and turns the useful few into something they can judge in five seconds.

Nothing here ships. Prototypes are drafts, previews and mocks; the owner decides.

## Configure once

Write these in the orchestrator's `NOW.md` (or tell the scout in its brief):

- **Source:** where saves come from. Any of: the [`savethat-cli`](../savethat-cli/SKILL.md) skill or SaveThat MCP, a Raindrop export or API, X likes through an API client the owner already uses, a browser bookmarks file, a read-later service. Read-only access only.
- **State file:** where the last scout time lives, for example `~/.local/state/bookmark-scout/state.json` (`{"last_run": "<ISO time>"}`).
- **Work map:** the files that say what the owner is working on, for example the orchestrator's `BOARD.md`, open `LEDGER.md` rows, a project inventory and an ideas file.
- **Budget:** tries per day (default 3, at most 1 build thread) and a spend cap for any model calls inside prototypes.
- **Report folder:** where daily reports go.

## 1. Read the new saves

- List saves newer than the last scout time (default: 24 hours ago; on Mondays look back 7 days). Page until you reach the cutoff.
- Open the full content or the service's analysis for promising ones. Look for related older saves: a theme the owner keeps saving is a stronger signal than a one-off.
- If the source is unavailable, say so in the report and stop. Do not guess from titles alone.
- Write the new scout time to the state file only after the run finishes.

## 2. Map saves to work

Read the work map first. For each save, decide in one line:

- **apply:** a technique, component, prompt, library, design pattern or data source that would visibly improve a named project ("this shockwave halo effect -> the app's search input").
- **idea:** a new experiment or post, with where it came from, the proof and why someone else would care.
- **skip:** memes, news, hiring calls, things already done. Most saves are skips; report how many.

## 3. Try the best ones

Prefer the cheapest proof that lets the owner decide:

1. **A mock:** HTML/CSS rendered to PNG (light and dark if the product has both), or an annotated screenshot of the real product with the idea drawn in.
2. **A quick prototype on a preview:** a draft PR in the project's repository (worktree off the default branch, the repository's commit identity), the preview link, and stills or a 10 to 20 second recording.
3. **For a new experiment:** a one-page brief, with a first runnable slice only if it is cheap.

Rules:

- Code only in the owner's personal projects, unless they have said otherwise. Work projects get a mock or a note, never a PR, and no internal numbers.
- Every build thread gets a ledger row first (skill [`delegation-ledger`](../delegation-ledger/SKILL.md)): proof is a draft PR plus preview plus media, never merged.
- Stay inside the spend cap; check remaining credit before any paid call.
- When unsure whether the owner would want it, make the mock only and ask in one line.

## 4. Report

- Write `<report folder>/<YYYY-MM-DD>.md`: counts (new saves, apply, idea, skip), then one row per apply or idea: the save (title and link), the project, the idea in one sentence, the evidence (file path, preview URL, PR) and the bold reply words the owner can use (**try halo on search**, **drop it**, **make it a post**).
- Add the strong ones to the board's 💡 section (newest first, keep it to 5 to 8 lines).
- In the morning brief: a 🔖 section, at most 4 lines, plus the report path.
- Never post, message or contact anyone about a save. Never merge.

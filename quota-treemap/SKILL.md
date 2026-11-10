---
name: quota-treemap
description: Show how Claude Code and Codex subscription usage splits across projects (for example work, personal and agent setup) as a treemap where tile area is share, for the last 30 and 90 days, from real local session logs on one or more machines. Use when the owner asks "where is my quota going", "usage treemap", "how much of my personal subscription goes to work", or for a periodic check-in on that split.
---

# Quota treemap

One square is all included usage (= 1). Each tile's area is a project's share; its color is the project's group. Two squares: the last 30 days and the last 90 days. A dated snapshot per run makes the next run say what moved ("Side project 25% -> 18%").

It reads only local session logs, so it works for flat-rate subscriptions where the provider shows no per-project breakdown.

## Set up once

1. Pick a private data folder, for example `~/sub-usage`. If you use several machines, make it a folder they already share, or copy the TSV files over by hand.
2. Copy [rules.example.json](rules.example.json) to `<data>/rules.json` and edit the groups and projects. A session goes to the first project whose `match` substring appears in its Git remote or working directory, then (second pass) in its first prompt.
3. Know which config home belongs to which subscription. Default homes are `~/.claude` (Claude Code) and `~/.codex` (Codex). If you run several accounts through separate homes, list each one with its own account label.

## Run it

1. **Collect, on every machine** (read-only; slow on a busy machine, so run it under `nice`):

   ```sh
   nice python3 -I <skill-dir>/scripts/collect.py --machine laptop \
     --source personal=claude:~/.claude --source personal=codex:~/.codex --out ~/sub-usage
   ```

   It writes `<data>/sessions-<machine>.tsv`. A machine that is off is simply missing; the page lists which machines it used.
2. **Build, on any machine:**

   ```sh
   python3 -I <skill-dir>/scripts/build.py --data ~/sub-usage --rules ~/sub-usage/rules.json \
     --accounts personal --tz <your time zone>
   ```

   It writes `projects.txt`, `treemap.html` and `history/<date>.json`. `--accounts` limits the chart to one subscription; omit it to include all.
3. **Show it.** Open `treemap.html` and look at the smallest tiles: every label must sit inside its tile (the page shrinks or hides labels and lists hidden ones under the square). Compare with the previous file in `history/` and lead with what moved.

## Method (keep it stable so snapshots compare)

- Weight per session = input + 1.25 x cache write + 0.1 x cache read + 5 x output tokens (Codex: uncached input + 0.1 x cached + 5 x output). This roughly follows API price ratios. It is a proxy for quota burn, not the provider's meter.
- Claude usage is deduplicated by message id plus request id, because resumed sessions repeat lines.
- A session is dated by its start. Windows count back from now.
- When an "Other" tile grows past about 5%, read its top sessions' first prompts in the TSV and add a rule.

## Known limits (say them when showing)

- Claude Code deletes old transcripts after a retention period (30 days by default), so the 90-day square may show only about 30 days of Claude.
- Sessions whose log was deleted or that ran in a cloud sandbox are missing.
- The TSV files hold each session's first prompt (truncated) for classification. Keep the data folder private, and never paste it into a public issue.

## Rules

- Read-only over logs. Never read or print tokens, auth files or account ids.
- The page shows project labels and percentages only. Check that your labels are fine to share before you share the picture.

## Check the scripts

```sh
python3 -m unittest discover -s <skill-dir>/scripts -p 'test_*.py' -v
```

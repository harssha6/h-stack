# Lessons and references

Background for maintaining this skill. These are general lessons, not live
policy for any repository. Always re-query the live rules for the PR in front of you.

## Lessons that shaped the skill

- Green or neutral checks can coexist with unresolved bot review threads and a
  BLOCKED / REVIEW_REQUIRED merge state. One APPROVED review may not be enough.
- Security scanner findings and code review bot findings both arrive as review
  threads. Inspect every author, not only accounts ending in `[bot]`.
- The latest published bot review can be older than the current head. Freshness
  needs exact-head evidence, not an older review.
- A PR closed after its change was cherry-picked elsewhere is closed, not merged.
- Approvals can be dismissed when new commits land, or when a stacked parent
  merges and the head changes. Re-read approvals after every push or base change.
- Effective rules can come from organization-level rulesets that differ from
  classic branch protection. Some branches have no effective rules at all, and
  some policy endpoints are inaccessible. Treat inaccessible as unknown.
- Old PR titles and branch names are not a naming standard. Follow the
  repository's current conventions.

## Workflows compared

- [OpenAI Codex babysit-pr](https://github.com/openai/codex/blob/70ac0f123c4b1869c9069d5b34e367b96c28bfad/.codex/skills/babysit-pr/SKILL.md): persistent repair/push loop, review-first order, bounded retries and one owned watcher.
- [Claude Mem babysit](https://github.com/thedotmack/claude-mem/blob/main/plugin/skills/babysit/SKILL.md): live mergeability, paginated threads, fresh final sweep and readiness endpoint.
- [vaibhavmalik/babysit-pr](https://github.com/vaibhavmalik/babysit-pr): focused batches, attribution and scope deferral. Rejected arbitrary line-count cutoffs, blanket human replies and automatic follow-up PRs after merge.
- [Codex-derived standalone packaging](https://github.com/novotnyllc/babysit-pr): research lead on Copilot accounts without `[bot]`.

Adaptations: finite handoff default with explicit longer-watch mode; preserve dirty
trees; inspect every author; two diagnosed failed-job reruns per workflow/head;
account routing; inherited rules; head/base freshness; human/merge authority.

## Primary documentation

- [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Effective branch rules API](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch)
- [Required-check troubleshooting](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)
- [Cursor Bugbot](https://cursor.com/docs/bugbot)

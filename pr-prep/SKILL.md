---
name: pr-prep
description: Prepare a pull request with a categorized shipping inventory, deliberate scope, reviewer-ready title/body, verification evidence, and project-specific required approvers. Use for PR preparation or explaining what will ship and who must review; hand published PR checks and feedback to pr-babysitter.
---

# PR Preparation

Paths like `<skill-dir>/scripts/...` are relative to this skill's folder; replace `<skill-dir>` with wherever you installed it.

Give the user a concrete answer to: what ships, why these changes belong together, what has been proved, and who must approve. Keep the user's shipping inventory distinct from the reviewer-facing PR body.

## Scope and authority

A preparation request authorizes inspection and local preparation artifacts. Publish when the user asks to create/open/send the PR or has already authorized it. Do not manufacture another approval checkpoint when publication is already authorized. Preparation alone does not authorize committing all dirty files, sending reviewer messages, merging, deploying, or changing repository policy.

Preserve unrelated tracked, untracked, ignored, and staged work. A filename list or prior conversation is a starting point, not proof of change ownership. Inspect the actual diff. Never use `git add .` on a mixed worktree. Do not reset or stash user changes to make preparation easier.

## Establish the exact candidate

- Read repository instructions and discover the project stack, normal checks, deployment path, and PR template.
- Inspect origin, branch, upstream, dirty/staged/untracked state, existing PR and its state, and the intended base. If you use multiple GitHub accounts, make sure the right one is active, and follow the repo's own contribution conventions for branch and PR naming. Do not assume the default branch is the intended base of a stack.
- Fetch the selected base. Inspect both the commit range and tree difference. After a squash merge, old head commits may look unmerged while the trees are identical. Do not replay already-merged changes or reopen a completed topic by accident. Propose a fresh branch when appropriate; never silently migrate a published branch.
- Reconcile the eventual PR diff (base merge-base to candidate head) with intended staged/working/untracked changes. Untracked files do not appear in ordinary `git diff` and must be inspected separately. Do not claim a prospective diff is already remote.
- Record base/head SHA and the selected file list. If the diff changes, update the inventory and verification claims before publication.

## Categorize what ships

Group by behavior and ownership rather than extension or folder alone. Choose categories that explain this project, for example user flow/copy, runtime/API contract, loading/cache behavior, build/deployment, persistence/auth, tests, generated outputs and documentation. Avoid empty categories.

For each category, state:

| Category | Concrete before/after behavior | Representative files | Evidence and material risk | Review focus |
| --- | --- | --- | --- | --- |

Maintain an exact inclusion/exclusion list in the local preparation artifact when the worktree is mixed. Explain generated manifests versus generated build output, preexisting changes, and local-only skill/tooling work. Explicitly identify behavior changes that were reverted and therefore will not ship when they were material to the conversation.

Recommend splitting changes that have independent purposes, rollback needs, or reviewer ownership. Explain the smallest useful split; do not force one PR per directory. Keep tightly coupled producer/consumer or migration changes together. If the user requests one PR, organize its independent pieces visibly rather than silently omitting them.

## Determine approvers from current policy

Use the intended **base branch's** CODEOWNERS, not just the working copy. GitHub searches `.github/CODEOWNERS`, then root, then `docs/CODEOWNERS`; the first existing file wins. Last matching pattern wins, paths are case-sensitive, and multiple owners on a matching line are alternatives unless other policy adds requirements. Use GitHub's ownership information or a compatible parser for complex patterns; do not improvise a regex matcher. Inspect CODEOWNERS errors and access when material.

Inspect effective branch rules including inherited organization rules, classic protection, required checks/workflows, approval count, required code-owner review, stale-review dismissal, last-push approval and conversation resolution. An inaccessible endpoint is unknown, not no policy. Classic `Branch not protected` does not cancel inherited rulesets.

Useful read-only endpoints, with shell arguments quoted:

- `gh api 'repos/OWNER/REPO/rules/branches/BASE'`
- `gh api 'repos/OWNER/REPO/branches/BASE/protection'`
- `gh api 'repos/OWNER/REPO/contents/.github/CODEOWNERS?ref=BASE'`
- `gh api 'repos/OWNER/REPO/codeowners/errors'`

Encode branch names containing slashes in URL path parameters. Use the existing pr-babysitter snapshot helper when a real PR exists instead of rebuilding its policy collection.

Report three separate things:

1. **Required human approvals:** actual named code owners/teams and approval conditions, tied to changed paths and policy evidence. Do not imply all listed owners must approve or that one approval always satisfies every owner group. The author cannot approve their own PR; latest-push rules may also exclude the pusher.
2. **Recommended technical reviewers:** infer from the actual change and project ownership evidence. Label recommendations as recommendations. A Docker change alone does not prove Infra approval is mandatory. Do not invent people or claim expertise from a username.
3. **Automated and release gates:** CI, security scanners, ticket checks, thread resolution and deployment approval are distinct from human PR approval. Inspect emitted checks on existing PRs; missing future results are pending, not passed. Merge approval is not deployment approval.

## Evidence and PR copy

Discover commands from the repository. Reuse valid verification evidence; rerun when the selected change invalidates it. Match each claim to its layer: source, unit tests, browser, provider, container, remote checks or deployed behavior. Never turn package-size reduction into download savings, or local tests into deployed proof. Label stale or partial coverage and state the smallest remaining check.

Write a title matching project conventions and the dominant outcome. Write the body for someone who has not read the conversation: lead with the problem and resulting behavior, then only material design choices, review focus, validation and rollout risk. Follow a repository template when present. Avoid dumping the private categorized inventory, test logs or revision history into a small PR. For broad changes, compact categories may help the reviewer too.

Save exact multiline title/body drafts locally. Use structured tool arguments or `--body-file` if publication is authorized. Link verified tickets without implying closure unless requested. Do not attach private artifacts to public hosting just to get screenshot URLs.

## Handoff

Before publishing: confirm the branch/base, file scope, commit identity and GitHub identity; meet required naming rules; inspect the final candidate diff. Carry prior authorization forward. Register created/worked-on PRs with T3 `link_pull_request` when available, then use `pr-babysitter` for live checks, bot findings, review freshness and final handoff. Prefer the app-owned watcher when available; do not create another polling loop.

For preparation-only requests, deliver the categorized scope, recommended split, excluded work, proposed title/body artifact, required and suggested approvers, and concrete remaining actions. State that no PR has been published. Never declare merge-ready from local evidence.

Research provenance and upstream comparisons: [references/sources.md](references/sources.md). These are design references, not live repository policy or authorization.

---
name: clean-worktree
description: Create isolated git worktrees for focused changes when the current checkout is dirty, when a task needs a pushable branch, or when local ignored runtime files like .env and node_modules should be symlinked from an existing checkout.
metadata:
  short-description: Create clean git worktrees with runtime symlinks
---

# Clean Worktree

Use this skill when a task should be separated from a dirty checkout, needs a clean pushable branch, or should reuse local ignored runtime files such as `.env`, `.env.local`, `.vercel`, and `node_modules`.

## Workflow

1. Inspect the current repository state:
   - `git status --short`
   - `git branch --show-current`
   - `git worktree list`
2. Choose a sibling worktree path, usually next to the current repo:
   - `<repo-parent>/<repo-name>-<short-purpose>`
3. Create a branch with the `codex/` prefix unless the user requested another branch name:
   - `git worktree add -b codex/<short-purpose> <worktree-path> <base-branch>`
4. Symlink ignored runtime files from the source checkout into the new worktree when they exist and are useful:
   - `.env`
   - `.env.local`
   - `.vercel`
   - `node_modules`
5. Apply or recreate only the intended task changes in the clean worktree.
6. Validate from the clean worktree. If `node_modules` was symlinked, normal `npm`/`npx` commands should work.
7. Commit, push, and report the clean worktree path and branch.

## Helper Script

`<skill-dir>` is this skill's folder, wherever you installed it. Run the script from inside the repository you want to branch from. For the common case, run:

```bash
bash <skill-dir>/scripts/create_clean_worktree.sh <purpose-slug> [base-branch]
```

Example:

```bash
bash <skill-dir>/scripts/create_clean_worktree.sh dynamic-tool-labels main
```

The script creates a sibling worktree, creates `codex/<purpose-slug>`, and symlinks ignored runtime files that exist in the source checkout.

## Guardrails

- Never discard or reset changes in the source checkout.
- Do not copy secrets into git-tracked files. Symlink ignored env files instead.
- If the target worktree already exists, stop and inspect it rather than overwriting.
- Do not commit symlinks for ignored runtime files; confirm with `git status --short`.
- Keep the isolated branch scoped to the task. If unrelated files appear, remove them from the isolated worktree before staging.

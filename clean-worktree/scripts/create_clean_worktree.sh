#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <purpose-slug> [base-branch]" >&2
  exit 2
fi

purpose="$1"
base_branch="${2:-main}"

if [[ ! "$purpose" =~ ^[a-z0-9][a-z0-9._-]*$ ]]; then
  echo "Purpose slug must use lowercase letters, numbers, dots, underscores, or hyphens." >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
repo_name="$(basename "$repo_root")"
repo_parent="$(dirname "$repo_root")"
target_path="${repo_parent}/${repo_name}-${purpose}"
branch_name="codex/${purpose}"

if [[ -e "$target_path" ]]; then
  echo "Target path already exists: $target_path" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/heads/${branch_name}"; then
  echo "Branch already exists: ${branch_name}" >&2
  exit 1
fi

echo "Creating worktree:"
echo "  source: $repo_root"
echo "  target: $target_path"
echo "  branch: $branch_name"
echo "  base:   $base_branch"

git worktree add -b "$branch_name" "$target_path" "$base_branch"

for item in .env .env.local .vercel node_modules; do
  source_item="${repo_root}/${item}"
  target_item="${target_path}/${item}"

  if [[ -e "$source_item" && ! -e "$target_item" ]]; then
    ln -s "$source_item" "$target_item"
    echo "Linked ${item}"
  fi
done

echo
echo "Ready:"
echo "  cd $target_path"
echo "  git status --short"

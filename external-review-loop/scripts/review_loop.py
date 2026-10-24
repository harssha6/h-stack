#!/usr/bin/env python3
"""Plan a minimal, independent review council without invoking a model by default."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

LANES = {
    "change-correctness": "Trace the changed behavior to its current owner. Find concrete regressions, contract breaks, and scope mistakes.",
    "product-user": "Infer the current user role from current source and inspect the changed journey for trust, clarity, state, and task completion.",
    "interaction-quality": "Inspect interface states, accessibility, interaction feedback, motion, and design-system fit. Treat visible controls that cannot act as defects.",
    "security-privacy": "Inspect authorization, sensitive data, secrets, trust boundaries, webhooks, and public attack surface.",
    "data-ai-integrity": "Trace model/prompt/input/data/persistence/output/fallback ownership. Check provenance, schema/API contracts, and hidden failure paths.",
    "reliability-performance": "Inspect query/cache/job/concurrency/error/observability behavior and require evidence for performance claims.",
    "platform-flow": "Inspect iOS/native navigation, state restoration, gesture/playback behavior, and the simulator/device verification path.",
    "experiment-evidence": "Inspect controls, fixtures, repeatability, artifacts, comparison logic, and whether the experiment can support the claimed decision."
}

KEYWORDS = {
    "security-privacy": ("auth", "login", "session", "token", "secret", "permission", "middleware", "webhook", "billing", "payment", "stripe", "dodo", "oauth", "privacy"),
    "data-ai-integrity": ("ai", "agent", "prompt", "model", "llm", "embedding", "vector", "retrieval", "generation", "schema", "migration", "database", "db", "queue", "job", "worker", "prisma", "drizzle"),
    "reliability-performance": ("cache", "performance", "benchmark", "query", "worker", "queue", "retry", "rate", "telemetry", "observability", "log", "concurrency", "import", "sync"),
    "experiment-evidence": ("experiment", "eval", "evaluation", "fixture", "benchmark", "variant", "ab-test", "pilot", "report"),
}

UI_SUFFIXES = {".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss", ".html"}
MOBILE_SUFFIXES = {".swift", ".m", ".mm"}
NON_DECISION_PREFIXES = (".agents/", ".port-tmp/", "node_modules/", "tmp/")
NON_DECISION_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pid", ".log"}


def run(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.rstrip("\n")


def repository_paths(repo: Path) -> list[str]:
    paths: list[str] = []
    for name in ("AGENTS.md", "CLAUDE.md", "README.md", "package.json", "Package.swift", "Podfile", "Gemfile", "pyproject.toml", "Cargo.toml"):
        if (repo / name).exists():
            paths.append(name)
    return paths


def status_paths(repo: Path) -> list[str]:
    result = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=repo, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace").strip() or "git status failed")
    records = result.stdout.decode(errors="surrogateescape").split("\0")
    paths = []
    index = 0
    while index < len(records):
        record = records[index]
        if not record:
            index += 1
            continue
        if len(record) < 4:
            raise RuntimeError(f"unexpected git status record: {record!r}")
        paths.append(record[3:])
        # In porcelain -z rename/copy records place the original path in the next record.
        index += 2 if record[:1] in {"R", "C"} or record[1:2] in {"R", "C"} else 1
    return sorted(set(paths))


def changed_paths(repo: Path) -> list[str]:
    paths = status_paths(repo)
    nested = []
    for path in paths:
        child = repo / path
        if child.is_dir() and (child / ".git").exists():
            nested.extend(f"{path.rstrip('/')}/{nested_path}" for nested_path in status_paths(child))
    return sorted(set([*paths, *nested]))


def material_paths(paths: Iterable[str]) -> list[str]:
    return [
        path
        for path in paths
        if not path.startswith(NON_DECISION_PREFIXES)
        and Path(path).suffix.lower() not in NON_DECISION_SUFFIXES
    ]


def lane_plan(paths: Iterable[str]) -> list[str]:
    normalized = [path.lower() for path in paths]
    routable = [path for path in normalized if Path(path).name not in {"agents.md", "claude.md"} and not path.startswith((".agents/", ".port-tmp/"))]
    lanes = ["change-correctness"]
    joined = "\n".join(routable)
    path_tokens = set(re.findall(r"[a-z0-9]+", joined))
    mobile_markers = ("ios/", "xcodeproj", "xcworkspace")
    if any(Path(path).suffix in MOBILE_SUFFIXES or any(marker in path for marker in mobile_markers) for path in routable):
        lanes += ["product-user", "platform-flow", "interaction-quality"]
    elif any(Path(path).suffix in UI_SUFFIXES or any(token in path for token in ("screen", "view", "component", "page", "onboarding")) for path in routable):
        lanes += ["product-user", "interaction-quality"]
    for lane, keywords in KEYWORDS.items():
        if any(keyword in path_tokens for keyword in keywords):
            lanes.append(lane)
    # Preserve priority and keep routine councils small.
    priority = ["change-correctness", "security-privacy", "data-ai-integrity", "product-user", "platform-flow", "interaction-quality", "reliability-performance", "experiment-evidence"]
    return [lane for lane in priority if lane in lanes][:4]


def harness(value: str) -> tuple[str, str]:
    if value != "auto":
        return value, "explicit"
    if os.environ.get("CLAUDE_CODE"):
        return "claude", "environment"
    if os.environ.get("CURSOR_TRACE_ID") or os.environ.get("CURSOR_AGENT"):
        return "cursor", "environment"
    terminal = os.environ.get("TERM_PROGRAM", "").lower()
    if "cursor" in terminal:
        return "cursor", "terminal"
    return "unknown", "not reliably detectable"


def runner_recommendation(authoring: str) -> dict[str, str]:
    if authoring == "codex":
        return {"local": "Claude Code in print/plan mode with a strongest available model", "cloud": "Claude ultrareview only for an approved synced branch or PR"}
    if authoring in {"claude", "cursor"}:
        return {"local": "Fresh Codex exec in read-only sandbox with the findings schema", "cloud": "Claude ultrareview only for an approved synced branch or PR"}
    return {"local": "Choose a fresh alternate local CLI after confirming the authoring harness", "cloud": "Do not select cloud mode until the branch and policy are confirmed"}


def plan(repo: Path, authoring_harness: str) -> dict:
    paths = changed_paths(repo)
    material = material_paths(paths)
    authoring, detection = harness(authoring_harness)
    try:
        upstream = run(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    except RuntimeError:
        upstream = None
    ahead = None
    if upstream:
        try:
            ahead = int(run(repo, "rev-list", "--count", "@{u}..HEAD"))
        except RuntimeError:
            pass
    digest = hashlib.sha256("\n".join(paths).encode()).hexdigest()[:16]
    return {
        "version": 2,
        "repo": str(repo),
        "changed_paths": paths,
        "change_digest": digest,
        "source_pointers": repository_paths(repo),
        "material_paths": material,
        "lanes": lane_plan(material),
        "authoring_harness": authoring,
        "authoring_harness_evidence": detection,
        "recommendation": runner_recommendation(authoring),
        "cloud_review": {
            "allowed_by_default": False,
            "requires": ["explicit user approval", "synced intended branch or PR", "review of code-sharing policy"],
            "upstream": upstream,
            "local_commits_not_on_upstream": ahead,
            "working_tree_clean": not paths
        }
    }


def write_bootstrap(review_plan: dict) -> list[Path]:
    target = Path(review_plan["repo"]) / ".agents" / "external-review"
    target.mkdir(parents=True, exist_ok=True)
    profile = {
        "version": 1,
        "purpose": "Durable review policy and source pointers. Not a repository summary.",
        "source_pointers": review_plan["source_pointers"],
        "refresh": "Regenerate the plan when changed file families or source pointers change; do not carry inferred product roles forward.",
        "cloud_review": review_plan["cloud_review"]
    }
    personas = {
        "generated_from_change_digest": review_plan["change_digest"],
        "lanes": [{"id": lane, "instruction": LANES[lane]} for lane in review_plan["lanes"]],
        "product_role_rule": "Infer the current user role from current source and cite it in the review."
    }
    written = []
    for name, payload in (("profile.json", profile), ("personas.json", personas)):
        path = target / name
        path.write_text(json.dumps(payload, indent=2) + "\n")
        written.append(path)
    return written


def decision_brief_template(review_plan: dict) -> str:
    files = "\n".join(f"- {path}" for path in review_plan["material_paths"]) or "- No material local changes detected; name the intended branch or PR."
    return f"""# Change Decision Brief

## Outcome

- Desired user or system result:
- Non-goals:

## Changed Surfaces

{files}

## Material Decisions

For each choice that changes behavior, contract, cost, safety, or future ownership:

1. **Decision:**
   - Owner surface:
   - Alternative rejected:
   - Why this choice:
   - Confidence: high | medium | low
   - Evidence or source of truth:
   - Verification that could disprove it:

## Open Assumptions

- Assumption or user decision still needed:
- Consequence if wrong:
"""


def read_decision_brief(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"decision brief does not exist: {resolved}")
    text = resolved.read_text().strip()
    if not text:
        raise ValueError(f"decision brief is empty: {resolved}")
    return text


def prompt(review_plan: dict, lane: str, decision_brief: str | None = None) -> str:
    if lane not in LANES:
        raise ValueError(f"unknown lane: {lane}")
    sources = ", ".join(review_plan["source_pointers"]) or "current repo instructions and package manifests"
    files = "\n".join(f"- {path}" for path in review_plan["material_paths"]) or "- No material local changes detected; inspect the requested branch/PR instead."
    author_brief = decision_brief or "No author decision brief was provided. Mark decision_audit.coverage as missing, reconstruct only the material choices needed for review, and state this limitation."
    return f"""You are the independent {lane} reviewer. You did not implement this change. Work read-only.

Audit the material decisions before you inspect implementation detail. The diff is evidence for or against a decision, not the primary object of review.

Author decision brief:
---
{author_brief}
---

First inspect the current source of truth, including: {sources}. For each material decision, verify its owner, rejected alternative, evidence, confidence, and disproof path against current source and the relevant runtime owners/tests. Only then inspect the diff where it helps prove or weaken that decision.

Changed paths:
{files}

Generated artifacts, screenshots, and temporary QA files are omitted from this
overview. Inspect them only when they are the evidence needed to verify a stated
decision.

Review lens: {LANES[lane]}

Return JSON matching the provided findings schema. Fill decision_audit before findings. A zero-finding result is valid. Every finding must include a precise location, direct evidence from current source, concrete consequence, recommendation, and confidence. Do not invent a user persona; for a product-user review, infer and cite the role from current source. Mark taste tradeoffs or missing runtime access in verification_notes rather than calling them defects. Do not report syntax nits unless they change behavior, contract, safety, cost, or ownership."""


def command_for(repo: Path, runner: str, review_prompt: str, model: str | None) -> list[str]:
    skill_root = Path(__file__).resolve().parents[1]
    schema = skill_root / "references" / "findings-schema.json"
    if runner == "claude":
        command = ["claude", "-p"]
        if model:
            command.extend(["--model", model])
        return [*command, "--permission-mode", "plan", "--no-session-persistence", "--output-format", "json", "--json-schema", str(schema), review_prompt]
    if runner == "codex":
        command = ["codex", "exec"]
        if model:
            command.extend(["--model", model])
        return [*command, "--ephemeral", "-C", str(repo), "--sandbox", "read-only", "--output-schema", str(schema), review_prompt]
    raise ValueError(f"unsupported runner: {runner}")


def invoke(repo: Path, review_plan: dict, runner: str, lane: str, execute: bool, model: str | None, decision_brief: str) -> int:
    review_prompt = prompt(review_plan, lane, decision_brief)
    command = command_for(repo, runner, review_prompt, model)
    if not execute:
        print(json.dumps({"mode": "dry-run", "cwd": str(repo), "command": command}, indent=2))
        return 0
    result = subprocess.run(command, cwd=repo)
    return result.returncode


def cloud_review(repo: Path, review_plan: dict, execute: bool, allow_cloud: bool) -> int:
    cloud = review_plan["cloud_review"]
    blockers = []
    if not allow_cloud:
        blockers.append("pass --allow-cloud to confirm code-sharing approval")
    if not cloud["working_tree_clean"]:
        blockers.append("working tree is not clean")
    if not cloud["upstream"]:
        blockers.append("no upstream branch is configured")
    if cloud["local_commits_not_on_upstream"] not in (0, None):
        blockers.append("local commits are not on the configured upstream")
    command = ["claude", "ultrareview", "--json"]
    if blockers:
        print(json.dumps({"mode": "blocked", "command": command, "blockers": blockers}, indent=2))
        return 2
    if not execute:
        print(json.dumps({"mode": "dry-run", "cwd": str(repo), "command": command}, indent=2))
        return 0
    return subprocess.run(command, cwd=repo).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "bootstrap", "decision-brief", "prompt", "run", "cloud"))
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--authoring-harness", choices=("auto", "codex", "claude", "cursor"), default="auto")
    parser.add_argument("--lane", choices=tuple(LANES))
    parser.add_argument("--decision-brief", type=Path, help="Change-scoped author decision brief. Required to run an external reviewer.")
    parser.add_argument("--runner", choices=("claude", "codex"))
    parser.add_argument("--model", help="Optional runner model alias. Omit to use the runner's configured default.")
    parser.add_argument("--execute", action="store_true", help="Run the selected external CLI. Otherwise print a dry-run command.")
    parser.add_argument("--allow-cloud", action="store_true", help="Confirm that cloud review is permitted for this synced branch.")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    try:
        review_plan = plan(repo, args.authoring_harness)
    except RuntimeError as error:
        parser.error(f"{repo} is not a usable git repository: {error}")
    if args.command == "bootstrap":
        paths = write_bootstrap(review_plan)
        print(json.dumps({"plan": review_plan, "written": [str(path) for path in paths]}, indent=2))
    elif args.command == "decision-brief":
        print(decision_brief_template(review_plan))
    elif args.command == "prompt":
        if not args.lane:
            parser.error("prompt requires --lane")
        try:
            brief = read_decision_brief(args.decision_brief)
        except ValueError as error:
            parser.error(str(error))
        print(prompt(review_plan, args.lane, brief))
    elif args.command == "run":
        if not args.lane or not args.runner or not args.decision_brief:
            parser.error("run requires --lane, --runner, and --decision-brief")
        try:
            brief = read_decision_brief(args.decision_brief)
        except ValueError as error:
            parser.error(str(error))
        return invoke(repo, review_plan, args.runner, args.lane, args.execute, args.model, brief)
    elif args.command == "cloud":
        return cloud_review(repo, review_plan, args.execute, args.allow_cloud)
    else:
        print(json.dumps(review_plan, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

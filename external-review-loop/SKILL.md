---
name: external-review-loop
description: Run an independent, harness-aware review for a code or product change using dynamic risk lanes and fresh-model context. Use when the user asks for a separate reviewer, cross-model review, review council, product/user/security persona feedback, adversarial validation, or a review after implementation, especially across Codex, Claude Code, Cursor, web, iOS, AI/backend, and internal-tool work.
---

# External Review Loop

Paths like `<skill-dir>/scripts/...` are relative to this skill's folder; replace `<skill-dir>` with wherever you installed it. Run the commands from the target repository.

Use independent reviewers to create useful disagreement, not a theatre troupe that invents bugs. Audit the material choices behind a change before reading its implementation details. The diff is evidence for or against a decision, not the primary review object.

## Safety Boundary

- Inspect `git status`, the active branch, and the changed files before selecting a runner.
- Treat cloud review as an explicit branch-level action. Do not send an uncommitted diff or proprietary repo to a cloud runner without the user's approval and a synced target.
- Use fresh local external CLI context for dirty changes. Use read-only/plan permissions. Never use bypass-permissions modes for a reviewer.
- Bootstrap only source pointers and review policy. Do not write a repo snapshot or inferred product facts into `AGENTS.md`, `CLAUDE.md`, or a persona file.
- Keep author decision briefs change-scoped. Do not commit them as durable repo documentation unless the user explicitly wants a decision record.
- Require evidence for every finding: exact path/line, observed or reproducible consequence, violated contract, and confidence. A review may return zero findings.

## Workflow

### 1. Create a decision brief

Before review, the author names the material choices rather than narrating syntax:

- desired outcome and non-goals;
- each material decision and the owner surface it changes;
- alternatives rejected and why;
- evidence, confidence, and the verification that could disprove the choice;
- unresolved assumptions or user decisions.

Generate a change-aware template without writing it to the repo:

```bash
python3 <skill-dir>/scripts/review_loop.py decision-brief .
```

Fill the brief in a temporary file or the review handoff. Do not use a generic
architecture summary. A decision about naming, formatting, or local syntax is not
material unless it changes a contract, behavior, cost, safety property, or future
ownership boundary.

### 2. Plan the review

Run the deterministic planner from the target repository:

```bash
python3 <skill-dir>/scripts/review_loop.py plan .
```

Pass `--authoring-harness codex`, `claude`, or `cursor` only when it is known. Otherwise keep `auto`; do not pretend terminal detection proves authoring context.

The planner selects the smallest council, normally `change-correctness` plus one to three lanes. Read [protocol.md](references/protocol.md) before overriding it.

### 3. Bootstrap or refresh repo-local personas

When the repo has no review profile, or its source pointers/changed risk surface have changed, generate one:

```bash
python3 <skill-dir>/scripts/review_loop.py bootstrap .
```

This writes `.agents/external-review/profile.json` and `personas.json`. They contain current source pointers, selected lenses, refresh metadata, and review policy, not a description of the product. Review these files before committing them; keep them only when the repo wants durable local review policy.

### 4. Choose the independent runner

Use this precedence: explicit user choice, known authoring harness, then a fresh local alternate-harness process.

- Codex-authored change: prefer Claude Code locally with the strongest available review model. `claude -p --model opus --permission-mode plan` is a typical invocation, but model availability is runtime state, not a durable requirement.
- Claude Code or Cursor-authored change: prefer a fresh local Codex process with `codex exec --sandbox read-only --ephemeral` and the structured response schema.
- Cloud final gate: use `claude ultrareview --json` only after confirming the intended branch/PR is synced and the user permits cloud review. It is a multi-agent branch review, not an uncommitted-worktree reviewer.
- If no alternate runner is available, run a fresh process of the current harness and label the reduced independence.

Generate a lane-specific prompt with the author decision brief:

```bash
python3 <skill-dir>/scripts/review_loop.py prompt . --lane data-ai-integrity --decision-brief /tmp/change-decisions.md
```

Then invoke the chosen runner from the target repo. The reviewer must inspect current instructions and source itself. Do not paste a stale repo summary into its prompt.

For a controlled local invocation, use the adapter. It only prints a command until `--execute` is supplied:

```bash
python3 <skill-dir>/scripts/review_loop.py run . --runner claude --model opus --lane change-correctness --decision-brief /tmp/change-decisions.md
```

For the cloud council, use `cloud . --allow-cloud` first. It refuses a dirty or unpushed branch and still remains a dry run until `--execute` is supplied.

### 5. Validate before acting

Use a separate validation lane, fresh reviewer, or direct source/runtime check for material findings. Deduplicate by root cause. Mark every result `confirmed`, `dismissed`, `needs-user-decision`, or `unverified`.

Do not make implementation changes merely because a reviewer sounded certain. For product feedback, preserve the declared stage: V1/pilot feedback is not a production-blocking defect unless the user said it is.

### 6. Close the real loop

Fix only confirmed findings, re-run the affected lanes, then verify the real path: named browser/account for web, simulator/device for iOS, route/job/persistence for backend and AI, and comparable controls/artifacts for experiments.

## Lane Selection

- `change-correctness`: always. Trace the changed behavior to its real owner and check regressions, contracts, and scope.
- `product-user`: UI, routes, screens, or interaction flows. Discover the actual user role from current instructions and product vocabulary; do not invent a demographic.
- `interaction-quality`: visual, accessibility, motion, component, or design-system changes. Check operability and state feedback, not subjective visual taste alone.
- `security-privacy`: auth, secrets, user data, webhooks, billing, permissions, or public API changes.
- `data-ai-integrity`: AI prompts/models, retrieval, generation, queues, schemas, jobs, DB/API data paths, provenance, or fallbacks.
- `reliability-performance`: caching, queries, worker/background behavior, concurrency, imports, observability, or high-volume flows.
- `platform-flow`: Swift/iOS, simulator/device, playback, navigation, gesture, or native platform changes.
- `experiment-evidence`: benchmark, evaluation, fixture, variant, or product experiment changes. Require controls, repeatability, and decision-ready artifacts.

Use specialist skills as evidence sources when you have them for a selected lane (for example security review, `rendered-output-verification`, design or accessibility review, prompt debugging, and experiment verification). A lane does not replace the relevant verification surface.

## Finding Contract

Use [findings-schema.json](references/findings-schema.json) for JSON-capable runners. First return `decision_audit`: which choices were covered, what evidence supports or weakens them, and where confidence remains low. For plain text, preserve those fields. A finding without a location, consequence, or current-source evidence is a question, not a defect.

## Do Not Do This

- Do not force every persona to find an issue.
- Do not turn a review into a syntax walkthrough, style-nit list, or diff summary.
- Do not count multiple agents repeating the same claim as proof.
- Do not add a permanent generic council to every task.
- Do not use cloud review as a substitute for dirty-worktree review or runtime verification.
- Do not let persona files become stale repo summaries.

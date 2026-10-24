# Review Protocol

## Council Shape

Use `change-correctness` plus only the lanes activated by the current change. Cap ordinary local reviews at four lanes. Prefer one strong specialist over three generic critics.

Each lane is a job, not a fictional identity:

- Inspect live source, existing instructions, changed files, and relevant tests/runtime owner.
- State no finding when the evidence does not support one.
- Distinguish a defect from an open product choice, a V1 tradeoff, or an unverified suspicion.
- Cite the path/line and expected consequence. Suggest a verification method.

## Decision Audit First

Start from the author's change-scoped decision brief. For each material decision,
check whether the stated owner, rejected alternative, evidence, confidence, and
disproving verification are credible. Use source, runtime behavior, tests, and the
diff to validate that choice.

Do not begin with a code walkthrough. Do not turn formatting, naming, or local
syntax into a finding unless it changes behavior, contract, safety, cost, or a
future ownership boundary. If the author did not provide a brief, mark decision
coverage `missing`, reconstruct only the material choices needed to review the
change, and state that limitation.

## Dynamic Product Persona

For `product-user`, determine the relevant role from the current route, screen, vocabulary, and task. Examples include a listener consuming media, a consumer saving/retrieving information, a creative operator preparing media, or a designer operating a console. The review must cite the source used to make that determination. It must not carry an old role forward merely because it exists in a prior persona file.

## Validation

Material findings require one of:

1. a fresh independent validation lane;
2. a direct code/source-of-truth check; or
3. a real runtime reproduction.

Classify the result after validation:

- `confirmed`: evidence supports a concrete fix;
- `dismissed`: false positive or intentional, with reason;
- `needs-user-decision`: real tradeoff or taste threshold;
- `unverified`: needs an unavailable runtime, credential, or artifact.

## Stage-Aware Bar

Ask whether the changed surface is production, release candidate, V1, or an experiment. Do not block an intended pilot for lack of production polish. Do block correctness, safety, provenance, or user-trust failures at every stage.

## Evidence Rules

For performance claims, require a comparable before/after slice. For UI claims, use the requested browser/account/device. For AI/data claims, trace prompt/model/input/persistence/output/fallback ownership separately. For internal tools, test the operator workflow rather than judging it by consumer-app conventions.

---
name: package-provenance-audit
description: Use before recommending or installing unfamiliar packages, especially auth, credentials, billing, payments, agents, browser automation, CLI tools, or packages that read files, network, env vars, tokens, or local accounts.
---

# Package Provenance Audit

Goal: answer "should we use this package?" from practical behavior and provenance, not README vibes.

## Workflow

1. Identify why the package is being considered and what trusted surface it would touch.
2. Inspect package metadata, repository, maintainers, version history, license, and install footprint.
3. Inspect tarball contents or source for postinstall scripts, binaries, network calls, env/token access, filesystem reads, and account/config storage.
4. Compare the package's actual API to the user's practical use case.
5. State risk plainly: acceptable, acceptable with constraints, avoid, or needs more verification.
6. If download counts or popularity matter, fetch current data and label it as time-sensitive.

## High-Risk Areas

- Auth, OAuth, sessions, tokens, SSH keys, browser profiles, local account files, payments, billing, email, agents with tool access, and CLIs that run code.
- Packages that require broad filesystem permissions or hidden background services.
- README-only claims without inspectable source or published tarball consistency.

## Output

- Practical usage path first.
- Provenance and risk second.
- Exact commands or integration notes only after the package clears basic trust checks.

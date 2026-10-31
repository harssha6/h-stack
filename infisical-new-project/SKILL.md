---
name: infisical-new-project
description: Set up development secrets for a user-chosen new app or project using the user's selected Infisical service. Use for requests to connect a new project to Infisical or share its dev secrets across machines; creating a reusable skill alone does not create a project. Existing-app migration, production secrets, and whole development environment setup are outside this workflow.
---

# Infisical for a new project

Give a new app a normal development command backed by Infisical secrets, with no secret values in its repository. Keep the work within the project and machines the user requested.

## Resolve the target

- Infer the project name, path, stack, startup command, and requested machines from the current task and repository. Ask only for missing project context that prevents progress. A scaffold with files can still be a new project; an empty directory is not a prerequisite.
- Creating this skill, discussing the approach, or starting unrelated new-project work does not authorize creating an app or Infisical resource. Once the user requests this project's secrets setup, perform its ordinary setup without adding a separate approval ceremony.
- Inspect project instructions, package scripts or equivalent, current environment loading, Git ignores, and existing Infisical project configuration (such as `.infisical.json`, or a repository-specific equivalent). Work with the actual startup path; avoid a parallel launcher that nobody uses.
- Use one Secrets Management project per new app and its `dev` environment by default. Honor explicit alternatives. Do not import another app's secrets, reuse another app's identities, migrate existing apps, deploy production secrets, or redeploy the vault.

## Connect and integrate

Read [references/connection.md](references/connection.md) for connection prerequisites and authentication boundaries. Use the official installed CLI and inspect its current help before applying commands; this export has no private endpoint or machine-specific wrapper.

1. Verify connectivity to the selected service and the account/organization on this machine. Interactive developers authenticate locally as themselves. Unattended machines receive independent read-only identities scoped to this new project. Never copy personal sessions/keychains between machines.
2. Inspect project listings and IDs before creation. Reuse only a resource demonstrably linked to this selected app. On ambiguous names, mismatched config, or an unexpected existing resource, stop the conflicting operation and resolve the identity; do not overwrite, remove, or recreate it.
3. Create/link the selected new project with the official CLI. Existing local config must be checked through the CLI and left intact when it matches. Populate development secrets through the private dashboard or another authorized secure input path. Never request passwords, tokens, or real secret values in chat.
4. Configure the selected project's development startup to use `infisical run -- <existing app command>`, using the project and environment flags required by the installed CLI. Preserve arguments and the package manager; avoid wrapping a script around itself. Keep infrastructure/client credentials outside the repo.
5. Commit-safe project references such as the official CLI's project configuration may contain the project ID and environment, never credentials. Keep `.env.example` to names and nonsecret placeholders. Confirm real environment files and local credential artifacts are ignored before staging changes.
6. Inject secrets into the server process only. Never place secrets in frontend public-variable prefixes, browser bundles, generated assets, or client-side configuration. Public configuration is a separate category and must contain no secret values.

## Verify and hand off

- Start with a clearly named dummy secret. Verify its presence through the actual app startup or a small subprocess using the same launcher. Do not dump the process environment or all fetched secrets. Run the project's appropriate checks for the launcher change.
- On an unattended reader, verify a dummy-only write attempt is rejected. Built-in viewer access covers the project's environments; do not claim dev-only isolation without inspecting and testing an available policy.
- Test a second actual machine only when cross-machine setup is in scope. A cross-machine sync claim requires both machines to fetch the same initial dummy and the same changed dummy after rotation. Hashes may compare dummy values; never fingerprint real credentials. One machine or two sessions on it do not prove cross-machine sync.
- Report the project, exact working startup command on each configured machine, what was tested, and any remaining login or connectivity step. Separate completed local setup from unverified cross-machine work.
- Inspect any existing backup/runbook as operational context. Do not stop a shared service, run a backup or alter the vault deployment as a side effect of new-project setup.

If an authentication credential is exposed, revoke that specific session/credential and verify rejection with its previous token before declaring cleanup complete. Handle tokens in memory; never print them or save them to a handoff document.

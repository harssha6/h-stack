# Infisical Connection Prerequisites

This skill assumes the user already has an Infisical Cloud account or a
self-hosted deployment. It does not deploy the service or configure a VPN.

## Discover The Connection

- Inspect the installed official `infisical` CLI's version and help, existing project configuration, and the user's documented service selection.
- Confirm the intended Cloud region or self-hosted API URL. Do not guess a hostname, reuse another person's deployment or silently fall back from a private instance to Cloud.
- For a private service, verify its intended network path and TLS trust. Do not disable certificate verification or change global DNS/network configuration to make the CLI connect.
- If the endpoint, organization, authorization or connectivity is missing, report the specific prerequisite. Ask only for nonsecret context; credentials belong in an approved secure input surface.

## Authenticate Locally

Interactive developers should use the official CLI's supported local login or
browser flow. Unattended machines should use separate machine identities with
only the project's required read access. Inspect the installed authentication
commands and provider policy rather than assuming a particular auth method or
license feature.

Keep tokens, passwords, client secrets and credential files outside the repo.
Never ask for secret values in chat, print them, place them in command-line
arguments or capture them in screenshots/logs. Use the CLI's supported secure
input/storage mechanism. Do not copy personal sessions or operating-system
keychains to another machine.

## Resolve The Project

Inspect structured project/account responses and compare stable IDs with the
selected app's existing config before creating or linking resources. A shared
name does not establish that an existing project belongs to this app. Preserve
matching config and stop on an unresolved collision.

Use the CLI's current help to select the project and development environment
for `infisical run -- <existing app command>`. Preserve the app's real package
manager and command arguments; avoid recursively wrapping a script around
itself. An authenticated CLI session on this machine does not prove another
machine can fetch the same secrets.

## Verify Without Exposing Secrets

Use one dedicated dummy key for fetch, rotation and permission checks. Never
dump all secrets or fingerprint real credentials. Verify permissions through
the actual configured machine identity and current service policy. A role
called viewer does not by itself prove development-only isolation.

Report the exact configured startup command and the machines actually tested.
Leave service deployment, existing-app migration and production secret changes
outside this workflow unless separately requested.

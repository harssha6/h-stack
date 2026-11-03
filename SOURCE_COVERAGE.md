# Coding-setup source coverage

Audit date: 2 November 2026 IST. Scope: every skill and custom integration named in [How I code with agents](https://www.harssha.design/blog/coding-setup.md). A public skill does not make the application it connects to open source. This document describes this branch; unmerged additions are not available on `main` yet.

## Our portable skill exports

The following article-named skills already shipped before this audit. Their instructions and any bundled resources are covered by this repository's [MIT license](LICENSE):

| Skill | Public export |
| --- | --- |
| original-thinking | [Instructions](original-thinking/SKILL.md) |
| source-of-truth-audit | [Instructions](source-of-truth-audit/SKILL.md) |
| rendered-output-verification | [Instructions](rendered-output-verification/SKILL.md) |
| interactive-visual-verification | [Instructions and UI metadata](interactive-visual-verification/SKILL.md) |
| external-review-loop | [Instructions, planner and references](external-review-loop/SKILL.md) |
| pr-prep | [Instructions and source credits](pr-prep/SKILL.md) |
| pr-babysitter | [Instructions, evidence collector and tests](pr-babysitter/SKILL.md) |
| clean-worktree | [Instructions and shell helper](clean-worktree/SKILL.md) |
| honcho-memory | [Instructions for a user-configured Honcho service](honcho-memory/SKILL.md) |
| infisical-new-project | [Instructions and connection reference](infisical-new-project/SKILL.md) |
| product-demo-video | [Instructions, capture/render scripts and example spec](product-demo-video/SKILL.md) |
| crisp-voice | [Instructions](crisp-voice/SKILL.md) |

This branch adds four portable instruction-only exports under the same MIT license:

| Skill | What is included | What is not included |
| --- | --- | --- |
| [t3-peer](t3-peer/SKILL.md) | Discover linked environments, read and control authorized threads, verify remote outcomes, and prepare context handoffs. | Legacy custom MCP client, credential renewal, global MCP registration, automatic Git/Syncthing transfer. |
| [t3-provider-pools](t3-provider-pools/SKILL.md) | Diagnose separate account homes, provider/model routing, native app authentication and MCP exposure using installed schemas. | Proxy installation, private gateways, configuration writers, app bridges and model shims. |
| [sticky-notes](sticky-notes/SKILL.md) | Read and narrowly edit a user-selected Markdown notes directory, with verified task completion. | Personal notes, fixed directories, the Stick This application. |
| [savethat-cli](savethat-cli/SKILL.md) | Retrieve bookmarks through an existing official CLI/account, discover its bundled skill, and protect private content. | Personal Keychain launcher, application environment-file fallback, CLI implementation, hosted service/backend. |

The repository also includes useful skills not named individually in the article. See the complete [README inventory](README.md#skills).

## Third-party originals

These belong to their authors. We link to their original releases rather than relabeling them as our exports. A local adaptation or reference does not imply the entire upstream repository is included here.

| Article name | Original source | Verified license evidence |
| --- | --- | --- |
| anatomy | [Ryan / wheresryan22](https://github.com/wheresryan22/anatomy) | [MIT](https://github.com/wheresryan22/anatomy/blob/main/LICENSE) |
| emil-design-eng | [Emil Kowalski's skill](https://github.com/emilkowalski/skills/tree/main/skills/emil-design-eng) | [MIT](https://github.com/emilkowalski/skills/blob/main/LICENSE); his writing is a separate reference. |
| stop-slop | [Hardik Pandya](https://github.com/hardikpandya/stop-slop) | [MIT](https://github.com/hardikpandya/stop-slop/blob/main/LICENSE) |
| vercel-react-best-practices | [Vercel React skill](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices) | The [skill frontmatter](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md) declares MIT; this audit did not find a root LICENSE file. |
| web-design-guidelines | [Public skill wrapper](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines) and [Vercel Web Interface Guidelines source](https://github.com/vercel-labs/web-interface-guidelines) | The guidelines source has an [MIT license](https://github.com/vercel-labs/web-interface-guidelines/blob/main/LICENSE). The wrapper has no separate license declaration, and this audit found no root LICENSE in agent-skills. |
| portless | [Vercel Portless skill and tool](https://github.com/vercel-labs/portless/tree/main/skills/portless) | [Apache-2.0](https://github.com/vercel-labs/portless/blob/main/LICENSE) |

## Custom tooling and applications

| Item | Public coverage | Remaining work or boundary |
| --- | --- | --- |
| Shared-folder symlink script | This branch adds the independent, portable [manual linker](tools/link-agent-skills.py), with [offline tests](tools/test_link_agent_skills.py), under MIT. | The local watcher/service installer is not exported. The original shell script depends on GNU path behavior unavailable on stock macOS. This helper links skills only when explicitly run. |
| hum | No h-stack implementation export. [Herdr](https://github.com/herdrdev/herdr) is a separate third-party base under [Apache-2.0](https://github.com/herdrdev/herdr/blob/master/LICENSE). | Package the terminal integration, ownership/lease store, cleanup scheduler and host notifications together; test installation, recovery and lifecycle behavior on supported hosts. Herdr's license does not release the hum wrapper. |
| Peer login and Git handoff | Not bundled with the instruction-only t3-peer export. | Replace private host/path assumptions; constrain authentication scope and global registration changes. Harden transfer paths and symlinks, decide what Git history may travel, and protect existing branches/dirty files on receive. Test malformed manifests, credential redaction, recovery and cancellation offline before release. |
| Provider account helpers | Not bundled with the instruction-only provider-pools export. [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) is independently public under [MIT](https://github.com/router-for-me/CLIProxyAPI/blob/main/LICENSE). | Separate user configuration from private gateway/identity handling, add an explicit account schema, and test settings writers, credential isolation and native-app bridges without touching real accounts. |
| Save That | The public [@savethat/cli package](https://www.npmjs.com/package/@savethat/cli) version 0.1.5 declares MIT and distributes compiled CLI code plus its own skill. [MCP documentation](https://savethat.app/docs/mcp) is public. | The npm tarball has no LICENSE file, and its repository points into an application repository unavailable publicly at audit time. This is public CLI distribution with a declared license, not a verified public backend/source release. The h-stack skill grants no rights to the hosted app. |
| Stick This | Public [Glaze app listing](https://www.glaze.app/app/stick-this-LwpGny); Markdown integration instructions exported here. | No public source repository or open-source license verified for the application. A free download is not evidence of an open-source release. |

## Why t3-peer was missing

The earlier h-stack release history documents a general portability exclusion for machine-specific integrations and explicitly postpones hum. It contains no t3-peer-specific exclusion explanation. The omission should not be described as a documented decision beyond that evidence.

The source audit found concrete blockers in its legacy helpers: hardcoded peer configuration, credential/login side effects, incomplete transport/protocol validation, unconstrained manifest paths, and receiving operations that can reset/clean a checkout. Filtering current snapshot files also does not establish that Git history contains no secrets.

The portable instructions avoid those helpers and use native linked-environment tools when available. They do not claim to reproduce the full automatic branch-and-files transfer shown in the article. A future executable client needs explicit configuration, secure transport, protocol/session validation, redacted failures and mocked negative-path tests; automatic Git transfer needs a separate safety review.

## Verification limits

Public paths and license files were checked over unauthenticated HTTP during this audit. The new instruction exports have no bundled executable integrations. The linker tests use temporary directories on Linux; macOS execution is not verified. Its source collection and parent directories must remain trusted and stable. No peer was contacted, no bookmark library was read, no provider/global skill configuration was changed, and no paid model API was called. This audit is not a release of any application's backend, private helpers or credentials.

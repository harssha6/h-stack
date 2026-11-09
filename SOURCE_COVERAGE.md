# Coding-setup source coverage

Audit date: 3 November 2026 IST. Scope: every skill and custom integration named in [How I code with agents](https://www.harssha.design/blog/coding-setup.md). A public skill does not make the application it connects to open source. This document describes this branch; unmerged additions are not available on `main` yet.

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

This branch includes the four portable exports proposed in the earlier coverage PR, now with bounded peer/provider helpers, and adds hum under the same MIT license:

| Skill | What is included | What is not included |
| --- | --- | --- |
| [t3-peer](t3-peer/SKILL.md) | Native environment/thread coordination plus a [selected-file snapshot helper](t3-peer/references/handoff.md), restoring into a fresh checkout from a known local commit. | Legacy custom MCP client, credential renewal, global MCP registration, Git-history transfer, destructive receive or automatic sync setup. |
| [t3-provider-pools](t3-provider-pools/SKILL.md) | Account diagnosis, an allowlisted native-app stdio bridge, discovery-only checker and new-file provider-home alignment candidates. | Private gateway/model shims, proxy installation, login copying, automatic changes to live provider settings. |
| [hum](hum/SKILL.md) | Herdr command, lifecycle and terminal guards, explicit installation preview, generic optional service templates and offline tests. | Personal hosts/settings, automatic service enablement, unsupported-host process cleanup or a guarantee of notifications for crashes/manual stops. |
| [sticky-notes](sticky-notes/SKILL.md) | Read and narrowly edit a user-selected Markdown notes directory, with verified task completion. | Personal notes, fixed directories, the Stick This application. |
| [savethat-cli](savethat-cli/SKILL.md) | Retrieve bookmarks through an existing official CLI/account, discover its bundled skill, and protect private content. | Personal Keychain launcher, application environment-file fallback, CLI implementation, hosted service/backend. |

### Orchestration release (9 November 2026 IST)

The coding-setup article's orchestrator section describes these. They are generic rewrites of the local skills, under the same MIT license:

| Skill or folder | What is included | What is not included |
| --- | --- | --- |
| [chief-of-staff](chief-of-staff/SKILL.md) | The orchestrator playbook: file-based memory, board contract, authority rules, waiting on others with signals, launch rules, rhythm, self-learning, plus [rollover](chief-of-staff/references/rollover.md) and [model routing](chief-of-staff/references/model-routing.md) references. Locally the orchestrator is named Friday; the public name says what it does. | The owner's own standing rules, thread and project ids, machines, accounts, work context and the live state files. |
| [orchestrator-template](orchestrator-template/README.md) | Blank `AGENTS.md`, `ORCHESTRATOR.md`, `BOARD.md`, `NOW.md`, `LEDGER.md`, `LOG.md`, `PULSE.md`, and the hourly pulse and morning brief prompts with placeholders. Not a skill: it has no `SKILL.md`. | Any real board, ledger or log content. No schedule is created. |
| [delegation-ledger](delegation-ledger/SKILL.md) | Row format, review rules and examples. | Real ledger rows. |
| [bookmark-scout](bookmark-scout/SKILL.md) | Source-agnostic daily scout with a try budget and a report format. | A specific bookmark account, credentials or the owner's project map. |
| [quota-treemap](quota-treemap/SKILL.md) | Configurable collector for local Claude Code and Codex logs, rules-driven build, treemap template and offline tests. | The local per-machine collectors, hardcoded account homes and project rules. |
| [site-analytics](site-analytics/SKILL.md) | Launch basics and an environment-configured Umami script for self-hosted or Cloud instances. | The private instance address, admin routes, team and website ids. |

Verification for this release: the quota-treemap tests ran on Linux against fake logs; `umami-site.py list` and `stats` ran read-only against one real self-hosted Umami instance. Umami Cloud's API-key path follows Umami's documentation and was not run. The chief-of-staff prompts are rewritten from prompts that run daily; the template copies themselves were not scheduled.

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
| hum | This branch exports the [complete portable command and sibling helpers](hum/SKILL.md) under MIT. [Herdr](https://github.com/herdrdev/herdr) remains a separate third-party base under [Apache-2.0](https://github.com/herdrdev/herdr/blob/master/LICENSE). | Service templates are generic and not enabled automatically. Real Herdr/Tailscale/desktop integration is not established by mocked tests. Unsupported process identity/terminal capabilities fail closed; host compatibility limits are stated in the skill. |
| Peer login and Git handoff | This branch exports a [bounded snapshot transfer](t3-peer/references/handoff.md) with versioned manifest/hash/size validation, path confinement and fresh-destination receive. | No login automation or global MCP registration. Only explicitly selected working files and notes travel; the receiver must already possess the exact base. No secret-content guarantee, transfer of Git history, existing-checkout reset or automatic Syncthing/thread setup. |
| Provider account helpers | This branch exports an explicit-config native-app stdio bridge, checker and candidate-only alignment tool. [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) is independently public under [MIT](https://github.com/router-for-me/CLIProxyAPI/blob/main/LICENSE). | Fake native clients prove the adapter contract, not real account/T3 interoperability. The private gateway shim is excluded because its identity handling and upstream protocol are not a portable public contract. No live configuration or credential copying. |
| Save That | The public [@savethat/cli package](https://www.npmjs.com/package/@savethat/cli) version 0.1.5 declares MIT and distributes compiled CLI code plus its own skill. [MCP documentation](https://savethat.app/docs/mcp) is public. | The npm tarball has no LICENSE file, and its repository points into an application repository unavailable publicly at audit time. This is public CLI distribution with a declared license, not a verified public backend/source release. The h-stack skill grants no rights to the hosted app. |
| Stick This | Public [Glaze app listing](https://www.glaze.app/app/stick-this-LwpGny); Markdown integration instructions exported here. | No public source repository or open-source license verified for the application. A free download is not evidence of an open-source release. |

## Why t3-peer was missing

The earlier h-stack release history documents a general portability exclusion for machine-specific integrations and explicitly postpones hum. It contains no t3-peer-specific exclusion explanation. The omission should not be described as a documented decision beyond that evidence.

The source audit found concrete blockers in its legacy helpers: hardcoded peer configuration, credential/login side effects, incomplete transport/protocol validation, unconstrained manifest paths, and receiving operations that can reset/clean a checkout. Filtering current snapshot files also does not establish that Git history contains no secrets.

The portable instructions use native linked-environment tools. The new executable snapshot helper transfers selected files and reviewed notes through a caller-selected shared directory, then materializes a new checkout from an independently expected local base. It validates the whole resulting tree, rejects symlinks/submodules and administrative paths, and never resets an existing checkout. It does not claim to reproduce the legacy automatic login/history-transfer workflow. The old helpers remain excluded.

## Verification limits

Public paths and license files were checked over unauthenticated HTTP during this audit. Package tests use temporary directories, local Git repositories, fake Herdr/native clients and mocked process/service operations. Local verification ran on Linux. The [CI template](tools/host-tools-workflow.yml) is not enabled: the publishing credential lacks GitHub workflow permission, so macOS CI remains unverified. Host tools, account access, desktop notifications and live peer synchronization are separate runtime checks; tests do not establish those. The linker's source collection and parent directories, and handoff's caller-selected local base repository, must remain trusted. No real peer or bookmark library was accessed, no provider/global skill configuration was changed, and no paid model API was called. This audit is not a release of any application's backend, private gateway integration or credentials.

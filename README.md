# h-stack

A curated set of 21 skills I use with Claude Code, Codex and Cursor. Each is a folder with a `SKILL.md` and, where needed, scripts and references.

These are portable exports from my shared skills folder. Personal identities, private hosts and project-specific setup are left out. Install the skills you need; the instructions adapt to the tools and repository you actually have.

## Skills

### Product and interface

- [original-thinking](original-thinking/SKILL.md): form a product-specific point of view, prove constraints and bring the user concrete choices when their judgment matters.
- [creative-direction-negotiation](creative-direction-negotiation/SKILL.md): turn taste and visual references into precise product choices.
- [make-interfaces-feel-better](make-interfaces-feel-better/SKILL.md): improve hierarchy, controls and states in an existing web or iOS interface.
- [motion-design](motion-design/SKILL.md): give animation a purpose, with pacing, continuity and reduced-motion behavior.

### Evidence and debugging

- [source-of-truth-audit](source-of-truth-audit/SKILL.md): trace a disputed claim to its runtime, data, code or Git owner before editing.
- [prompt-forensics](prompt-forensics/SKILL.md): inspect what a generation pipeline actually sent and persisted before blaming the prompt or model.
- [debug-log-triage](debug-log-triage/SKILL.md): find the smallest useful log slice and connect it to the failing subsystem.
- [experiment-verification-loop](experiment-verification-loop/SKILL.md): test a product claim on a small real slice and report what the evidence supports.
- [package-provenance-audit](package-provenance-audit/SKILL.md): inspect an unfamiliar package's source, install behavior and license before trusting it.

### Verification and shipping

- [rendered-output-verification](rendered-output-verification/SKILL.md): check the UI, copy, layout or PR output a user would actually see, instead of trusting the source.
- [interactive-visual-verification](interactive-visual-verification/SKILL.md): prove a browser, desktop or iOS simulator flow works with real clicks, typing and screenshots.
- [external-review-loop](external-review-loop/SKILL.md): get an independent review of a change from a fresh model, with risk lanes picked from what changed.
- [pr-prep](pr-prep/SKILL.md): work out what a pull request ships, who has to approve it, and write the title and body.
- [pr-babysitter](pr-babysitter/SKILL.md): take an open PR through CI, bot and reviewer findings and a verified handoff.
- [clean-worktree](clean-worktree/SKILL.md): create an isolated git worktree and branch when the current checkout is dirty.
- [product-demo-video](product-demo-video/SKILL.md): record a real product flow and edit it into a short captioned demo video.

### Context, setup and writing

- [agent-doc-bootstrap](agent-doc-bootstrap/SKILL.md): write thin, durable repository instructions without copying a snapshot of the repo.
- [context-rollover](context-rollover/SKILL.md): preserve decisions and verification in a handoff; start a new task only when explicitly requested and supported.
- [honcho-memory](honcho-memory/SKILL.md): recall and save a few durable facts in a user-configured Honcho workspace shared by agents.
- [infisical-new-project](infisical-new-project/SKILL.md): connect a selected new app's development command to Infisical without copying secrets into its repo.
- [crisp-voice](crisp-voice/SKILL.md): write or edit messages in a direct, concise engineer and founder voice.

## Install

A skill is a folder with a `SKILL.md`. Copy or symlink the folders you want into the skills folder of your tool:

- Claude Code: `~/.claude/skills`
- Codex: `~/.codex/skills`
- Cursor: `~/.cursor/skills`

To install this set, clone it once and link each skill into each tool. This Bash example leaves existing skills and symlinks alone:

```sh
git clone https://github.com/harssha6/h-stack.git ~/.agents/h-stack
mkdir -p ~/.claude/skills ~/.codex/skills ~/.cursor/skills
for s in ~/.agents/h-stack/*/; do
  [ -f "$s/SKILL.md" ] || continue
  name=$(basename "$s")
  for root in ~/.claude/skills ~/.codex/skills ~/.cursor/skills; do
    target="$root/$name"
    if [ -e "$target" ] || [ -L "$target" ]; then
      printf 'Keeping existing skill: %s\n' "$target"
    else
      ln -s "$s" "$target"
    fi
  done
done
```

Commands inside a `SKILL.md` that use `<skill-dir>` mean the folder where you installed that skill.

## Requirements

The instructions work with the tools your agent can access. Installing a skill does not install its CLI dependencies or grant permission to publish, merge, send messages or share private code.

Most of the new skills are instructions only. Supporting references ship in their own skill folder; no other skill in this repository is required just to read them. Where a skill suggests another specialist workflow, use it only if installed and appropriate.

- **Worktrees:** Git and Bash.
- **Review planner and PR evidence collector:** Python 3.10+. The collector also needs the GitHub CLI (`gh`) signed in to the intended account. The review planner only prints a plan or command unless you explicitly choose to execute it; local model review needs the corresponding Claude Code or Codex CLI and account.
- **Visual verification:** browser/computer-use tools in your harness, or an existing Playwright, Cypress or UI-test setup. For iOS, use macOS with Xcode and an available simulator.
- **Honcho memory:** an authenticated Honcho service or MCP connection, a selected workspace and a configured peer/identity. This repository does not deploy Honcho, create a peer, ingest conversations or grant permission to store private content. Without that setup the skill skips automatic memory access and reports missing setup for an explicit request.
- **Infisical:** the official CLI plus an existing Cloud account or self-hosted service and permission for the selected organization/project. Authentication stays local. The skill discovers the installed CLI's commands; no private endpoint, VPN or machine-specific wrapper is bundled.
- **Context rollover:** supported thread/task tooling is optional. Without it the skill returns a complete handoff to copy into a new conversation.
- **Demo video:** Python 3.10+, Node.js 20+, `ffmpeg` and `ffprobe`. The capture helper also needs Chrome or Chromium and `playwright-core` installed beside the helper so Node can resolve it:

  ```sh
  npm install --prefix ~/.agents/h-stack/product-demo-video --no-save --package-lock=false playwright-core
  ```

  Set `CHROME_PATH` if Chrome is not at the default macOS path. For example, on Linux use `CHROME_PATH=/usr/bin/google-chrome`. Edit the capture choreography for your page and choose a fresh `OUT` directory; capture refuses to reuse an existing directory. Set the real source and font paths in the example video spec before rendering.

The shipped Python tools use the standard library. To check the helpers without invoking a model or writing to GitHub:

```sh
python3 -m unittest discover -s pr-babysitter/scripts -v
python3 external-review-loop/scripts/review_loop.py --help
python3 product-demo-video/scripts/demo_video.py plan product-demo-video/scripts/example-spec.json
```

## Not bundled

This is not a copy of my whole local folder. Machine-specific integrations stay out until they can work independently. In particular, `hum` is a Herdr-backed process manager with lifecycle helpers and host setup; it needs a separately tested package, not just its instruction file copied here.

## Not in here, but worth getting

I also use these skills. They belong to their authors, so I have not copied them here.

- Emil Kowalski's design engineering skill, for UI craft and animation detail: [x.com/emilkowalski](https://x.com/emilkowalski)
- Anatomy by Ryan, for detailed interactive isometric SVG figures: [github.com/wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) and [x.com/wheresryan22](https://x.com/wheresryan22)
- Codebase Design and Domain Modeling by Matt Pocock, for deep modules and shared domain language: [github.com/mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/engineering)
- stop-slop by Hardik Pandya, for tightening prose that reads as AI-written: [github.com/hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) and [x.com/hvpandya](https://x.com/hvpandya)

## License

MIT. See `LICENSE`.

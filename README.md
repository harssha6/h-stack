# h-stack

These are the skills I use most with Claude Code, Codex and Cursor. Each one is a folder with a `SKILL.md` and, where needed, scripts and references.

## Skills

- [rendered-output-verification](rendered-output-verification/SKILL.md): check the UI, copy, layout or PR output a user would actually see, instead of trusting the source.
- [interactive-visual-verification](interactive-visual-verification/SKILL.md): prove a browser, desktop or iOS simulator flow works with real clicks, typing and screenshots.
- [external-review-loop](external-review-loop/SKILL.md): get an independent review of a change from a fresh model, with risk lanes picked from what changed.
- [pr-prep](pr-prep/SKILL.md): work out what a pull request ships, who has to approve it, and write the title and body.
- [pr-babysitter](pr-babysitter/SKILL.md): take an open PR through CI, bot and reviewer findings and a verified handoff.
- [clean-worktree](clean-worktree/SKILL.md): create an isolated git worktree and branch when the current checkout is dirty.
- [product-demo-video](product-demo-video/SKILL.md): record a real product flow and edit it into a short captioned demo video.
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

- **Worktrees:** Git and Bash.
- **Review planner and PR evidence collector:** Python 3.10+. The collector also needs the GitHub CLI (`gh`) signed in to the intended account. The review planner only prints a plan or command unless you explicitly choose to execute it; local model review needs the corresponding Claude Code or Codex CLI and account.
- **Visual verification:** browser/computer-use tools in your harness, or an existing Playwright, Cypress or UI-test setup. For iOS, use macOS with Xcode and an available simulator.
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

## Not in here, but worth getting

I also use these skills. They belong to their authors, so I have not copied them here.

- Emil Kowalski's design engineering skill, for UI craft and animation detail: [x.com/emilkowalski](https://x.com/emilkowalski)
- Anatomy by Ryan, for detailed interactive isometric SVG figures: [github.com/wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) and [x.com/wheresryan22](https://x.com/wheresryan22)
- stop-slop by Hardik Pandya, for tightening prose that reads as AI-written: [github.com/hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) and [x.com/hvpandya](https://x.com/hvpandya)

## License

MIT. See `LICENSE`.

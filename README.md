# Agent skills

These are the skills I use most with Claude Code, Codex and Cursor. Each one is a folder with a `SKILL.md` and, where needed, scripts and references.

## Skills

- `rendered-output-verification`: check the UI, copy, layout or PR output a user would actually see, instead of trusting the source.
- `interactive-visual-verification`: prove a browser, desktop or iOS simulator flow works with real clicks, typing and screenshots.
- `external-review-loop`: get an independent review of a change from a fresh model, with risk lanes picked from what changed.
- `pr-prep`: work out what a pull request ships, who has to approve it, and write the title and body.
- `pr-babysitter`: take an open PR through CI, bot and reviewer findings and a verified handoff.
- `clean-worktree`: create an isolated git worktree and branch when the current checkout is dirty.
- `product-demo-video`: record a real product flow and edit it into a short captioned demo video.
- `crisp-voice`: write or edit messages in a direct, concise engineer and founder voice.

## Install

A skill is a folder with a `SKILL.md`. Copy or symlink the folders you want into the skills folder of your tool:

- Claude Code: `~/.claude/skills`
- Codex: `~/.codex/skills`
- Cursor: `~/.cursor/skills`

Or keep everything in one folder, such as `~/.agents/skills`, and symlink each skill into each tool:

```sh
git clone https://github.com/harssha6/agent-skills ~/.agents/skills-src
mkdir -p ~/.claude/skills ~/.codex/skills ~/.cursor/skills
for s in ~/.agents/skills-src/*/; do
  name=$(basename "$s")
  ln -s "$s" ~/.claude/skills/"$name"
  ln -s "$s" ~/.codex/skills/"$name"
  ln -s "$s" ~/.cursor/skills/"$name"
done
```

Commands inside a `SKILL.md` that use `<skill-dir>` mean the folder where you installed that skill.

## Not in here, but worth getting

I also use these skills. They belong to their authors, so I have not copied them here.

- Emil Kowalski's design engineering skill, for UI craft and animation detail: [x.com/emilkowalski](https://x.com/emilkowalski)
- Anatomy by Ryan, for detailed interactive isometric SVG figures: [github.com/wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) and [x.com/wheresryan22](https://x.com/wheresryan22)
- stop-slop by Hardik Pandya, for tightening prose that reads as AI-written: [github.com/hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) and [x.com/hvpandya](https://x.com/hvpandya)

## License

MIT. See `LICENSE`.

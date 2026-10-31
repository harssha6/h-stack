---
name: product-demo-video
description: "Record a real product flow on real data and edit it into a short demo video (1080p MP4): the clean experience first, then a captioned step-by-step breakdown. Use when the user asks for a demo, a recording, a walkthrough video, a \"proper demo video\", a screen recording of a feature, or something to share with a team or stakeholders."
---

# Product Demo Video

Paths like `<skill-dir>/scripts/...` are relative to this skill's folder; replace `<skill-dir>` with wherever you installed it.

The helpers need Python 3.10+, Node.js 20+, ffmpeg/ffprobe, and Chrome or Chromium. Install `playwright-core` beside the capture helper (see the repository README), set `CHROME_PATH` when the default macOS Chrome path does not apply, and choose a new `OUT` directory for each take. Capture refuses to overwrite an existing directory.

You are the camera operator and the editor. Nobody hands you footage. Decide what the finished video needs, then shoot exactly that, at the pace the edit needs. Never record first and hope the edit can rescue it.

A demo has two jobs, in this order:
1. **Show the experience** as a user meets it: full frame, smooth, no overlays. A viewer who stops here should still get it.
2. **Break it down**: zoomed steps with captions that explain what they just saw.

Never open on the breakdown. Someone who hasn't seen the thing can't follow an explanation of it.

## 1. Write the edit before you record

Settle these in a few lines, from context when you can. Ask only for what you can't infer.

- **Audience.** Team update or stakeholder pitch. The clean pass usually runs 15–30s and the breakdown 30–45s.
- **Steps and captions.** Name 4–6 steps. Write each caption now as a verb-first title and one concrete subtitle. Caption length sets the shot length (section 4), so write tight: about 90 characters for title and subtitle together keeps a step near 8s.
- **Real target.** Use the feature, project, or record the user named. Don't invent fixtures.
- **Side effects.** List what the flow writes: drafts, jobs, model calls, quota, sends. Get an explicit OK before anything costly, irreversible, or shared. Plan to undo the rest.

## 2. Direct the take

The take is the clean pass and also the raw footage for every step, so choreograph it for both.

- **One action per beat.** Each step needs a clip that starts from a clean state and ends on a finished state, so it can loop or hold without looking broken.
- **Let the viewer see the target.** Move the cursor onto a control and rest about 0.5s before clicking. Ease every move. Don't jump.
- **Leave stillness.** Hold about 1.5s after each beat so the action can land and the edit has clean frames to cut on.
- **Show it at human pace.** Rapid repeats such as six pokes in a row are fine when they are the feature. Otherwise, one deliberate action beats three hurried ones.
- **Prepare the surface.** Use a fixed viewport, usually 1280×720 or 1440×900 at 2× for crisp crops. Hide dev chrome (framework badges, debug panels, replay buttons) with injected CSS, not code edits. Keep the take out of product analytics. Back up any state the flow touches.
- **Rehearse once.** A rehearsal that surfaces a product gap is a finding. Tell the user before the final take.

## 3. Record smoothly

The frame rate is part of the product. A laggy take makes good motion look broken.

- **Animated web UI (the default):** use `<skill-dir>/scripts/capture.mjs`. It runs the page on a virtual clock and screenshots every 1/60s, so every frame lands however slow the machine is. Edit its CHOREOGRAPHY block (cursor moves and clicks by time, with targets resolved from live selectors), then turn the frames into a take with ffmpeg at 60fps. The page's analytics hosts are blocked.
- **Fallback:** a live recorder (`preview_recording_start` / `preview_recording_stop` in T3). Use it only for flows that need real network timing or a signed-in state that headless can't reach. Live recorders drop frames on heavy animation. Count the distinct frames (`mpdecimate`) and re-shoot with `capture.mjs` if it stutters.
- Find beat times from frames, not from when you sent an action.
- Afterwards, restore any backed-up state, reload, and confirm the restore.

## 4. Edit

Use `<skill-dir>/scripts/demo_video.py` (Python 3 + ffmpeg). Write a spec (see `<skill-dir>/scripts/example-spec.json`), run `plan SPEC` to read the timing table, then run `build SPEC`.

Segment types, in their usual order:
- `clean`: the experience, full frame, played once, no text.
- `card`: a short title card such as "The breakdown".
- step (the default): captions on the left, the zoomed clip on the right. Use `clips` to cut between several moments under one caption without re-fading the text.

**Pacing rules that the script enforces**
- **A step stays up until its caption can be read:** max(3s, 1.2s + characters ÷ 14). The 14 characters per second is slower than subtitle speed because the viewer is also watching the clip.
- **Clips under 3s play once, then hold the finished frame.** A short click-and-result reads best once. Looping it twitches.
- **Clips of 3s or more loop in whole plays, then hold the finished frame** for the remaining time. A cut never lands mid-action. Override with `"after": "hold"` or `"after": "loop"` when the content calls for it, such as a one-way transition that looks wrong replayed.
- **A clip longer than its read time plays once**, and the step lasts as long as the clip.
- Every step after the first freezes its first frame through the crossfade, so the action starts once the viewer can see it.
- To shorten the video, cut caption words or steps. Never shorten a hold below its read time.

Composition:
- Use the product's own font and background colour. Find fonts in the repo's `public/fonts` and the colour in its tokens.
- Each step's crop must contain its whole subject at the end of the action, not only at the start.
- Use 0.4–0.5s crossfades and hold the last frame about 1.5s. Encode H.264 at CRF 18 with faststart, at the take's frame rate (60fps from `capture.mjs`).

## 5. QA before delivering

- `build` refuses to finish if any segment renders at a length other than its plan. Also check that the final duration and frame rate match the plan.
- Make a contact sheet with one frame from the middle of each segment. Check that each crop contains its subject and that no caption overflows.
- Read every caption aloud at normal speed while its step plays. If you can't finish before the cut, the timing is wrong.
- Watch it once end to end.

## 6. Deliver

- Embed the MP4 by absolute path, then list what it shows, one short line per step.
- State what was real (data, model calls, timings) and what you restored. If true, say that nothing was regenerated, published, or committed.
- Offer to reveal it in Finder (`open -R path`).
- Never post it anywhere under the user's name without approval. Chat connectors often can't attach video, so draft the message and let the user attach the file.

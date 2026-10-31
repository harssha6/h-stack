---
name: motion-design
description: Use when defining motion personality, choreography, transition intent, interaction pacing, brand motion, tactile feel, or why an animation should exist across web or iOS. Trigger on "motion design", "animation direction", "make it feel alive", "interaction feel", "microinteraction", "hover feel", "transition", "choreography", "easing direction", "snappy", "smooth", "janky", "too fast", "too slow", or "motion system".
---

# Motion Design

This skill decides what motion should mean. Implement that intent with the project's existing animation tools and the platform notes below. A separate animation implementation skill is optional, not a prerequisite.

## Motion Thesis

Before adding or changing motion, name:

- the object moving;
- the state change being clarified;
- the emotional quality: crisp, calm, playful, tactile, cinematic, utilitarian;
- the frequency of use.

If the animation does not clarify state, continuity, hierarchy, or affordance, remove it.

## Defaults

- Product tools: fast, restrained, interruptible, mostly feedback and continuity.
- Consumer/content UI: content-forward, subtle transitions, avoid covering the media.
- Marketing/editorial: choreographed entrance and scroll moments are acceptable when they support hierarchy.
- Tactile UI: motion should imply material, pressure, weight, and release.

## Hard Rules

- Repeated actions should not make users wait for a flourish.
- Avoid blank frames between content states.
- Do not animate layout properties when transform/opacity can do the job.
- Respect reduced-motion behavior on web and iOS.
- Pair related elements so they feel like one system.
- Slower is not automatically smoother. If feedback feels late, it is broken.
- Reuse a shared motion asset or utility when the same treatment appears across related chrome/loading/hover states.
- Verify motion in the rendered target surface when timing, continuity, or blank frames are the actual concern.

## Pushback

- Push back on decorative motion that does not clarify state, hierarchy, continuity, or affordance.
- Push back on hover/loading treatments that flash blank frames or hide the user's current object.
- Do not push back on the user's chosen motion personality after they clarify it; translate it into timing, easing, and continuity constraints.

## References

Read as needed:

- [references/choreography.md](references/choreography.md) for motion patterns.
- [references/platform-notes.md](references/platform-notes.md) for web/iOS implementation boundaries.

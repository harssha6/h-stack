# Motion Platform Notes

## Web

- Prefer transform and opacity.
- Use CSS for simple state transitions; use Framer Motion or a motion library when interruptibility, shared layout, or gesture continuity matters.
- Guard hover motion with pointer/hover media queries when touch behavior matters.
- Add `prefers-reduced-motion` handling for every meaningful animation.

## iOS

- Prefer SwiftUI animation APIs that match the state transition.
- Use spring-like motion for interruptible, gesture-driven surfaces.
- Keep production motion aligned with the app's existing design system and interaction behavior.
- Verify in Simulator for actual pacing; compile success is not motion verification.

# Motion Choreography

## Useful Patterns

- **Immediate feedback**: press/down state in 80-140ms.
- **Entrance**: start close to final state; small translate/opacity changes usually beat dramatic travel.
- **Exit**: shorter than entrance unless the disappearing object needs comprehension.
- **Shared movement**: if a drawer, scrim, and content shift together, they share duration/easing.
- **Hover preview**: do not blank; keep previous image/video visible while the next layer is ready.
- **Loading**: use motion to prove liveness, not to hide missing progress.
- **Marquee/ticker**: linear is acceptable only for constant-speed loops.

## Frequency Rule

- 100+ times per day: nearly instant or no motion.
- Frequent product actions: 100-200ms.
- Occasional panels/modals: 180-300ms.
- Editorial/first-time reveal: 300-600ms if it does not block action.

## Review Checklist

- What state change does this clarify?
- Can the user interrupt it?
- Does it run every time or only at useful moments?
- Does content remain visible during transitions?
- Is the slowest device still okay?

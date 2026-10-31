# iOS Interface Polish

Use the existing app architecture and design system. Inspect their current APIs and tokens before choosing a component or inventing a new surface.

## iOS Defaults

- Prefer the app's shared components when they already cover the behavior.
- Add shared token/component capability before copying hardcoded values across screens.
- Keep product orchestration in the app; shared visual primitives belong in the design-system package.
- Preserve data ordering, navigation, analytics, media controls and configuration unless the requested change affects them.
- Use names that communicate a token's visual or behavioral role.

## Common Fix Patterns

- Prototype to production: fit the idea into the app's existing navigation and state model.
- Design/spec mapping: inspect available tokens and components, explain material gaps, and propose the smallest coherent addition.
- UI tests: reuse the repo's existing test conventions and screen helpers when present.
- Designer previews: use representative states and real components; do not replace the production flow with a disconnected mock.

## Verification

- Start with `git status --short --branch` in each iOS repo touched.
- Discover the supported workspace or project, scheme and test command from the repo and Xcode tooling.
- Use isolated derived data when needed to avoid colliding with another build.
- Verify layout and interaction in an available simulator; a successful compile does not prove the visible result.
- Watch for Swift Package and CocoaPods resolver churn before committing.

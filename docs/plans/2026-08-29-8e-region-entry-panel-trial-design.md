# 8E Region Entry Panel Trial Design (2026-08-29)

## Purpose

This is a bounded 8E productization slice, not a final Portal visual sign-off and
not a media-adoption decision. It makes the official-wallpaper fallback usable as
a two-region trial so the complete interaction can be judged:

```text
select region → switch local scene → preserve region in URL → open Account
```

The default `/` cinematic Portal remains unchanged. The trial is isolated at
`/?surface=wallpaper-lab`; it performs no Auth, Riot, OP.GG, Provider, or SSE I/O
until the user deliberately enters the Account journey.

## Product decision

The first pass exposes the two candidates that have an auditable local media
bundle today: Demacia and Bandle City. The selector still renders the 13 Riot
Universe region crests, but regions without a locally reviewed dynamic candidate
remain disabled and labelled pending. A crest, an Account still, and a Portal
motion file are three separate readiness states.

The selected region is carried by a typed allowlist (`demacia`, `bandle-city`) in
the product-journey URL. Account receives it as a presentation hint only and uses
a quiet static background; it does not change identity, routing region, owner
scope, or player-link semantics. Back and Continue preserve the region parameter.

## Visual and interaction direction

The wider MotionSites audit is used as a source of interaction patterns, not as a
template or dependency. Its public browse/catalog exposes patterns such as
`Cinematic Landing Hero`, `Container Scroll Animation`, `Interactive Hover Button`,
`Background Paper Shaders`, and `Neon Nebula`, plus hero/landing/technology and
interactive-media groupings. We translate only what fits RiftCoach:

1. a full-bleed media hero with clear information hierarchy;
2. a compact, stateful atlas rather than a wall of equal cards;
3. immediate preview feedback on selection;
4. one deliberate action with a short, reversible activation transition;
5. hover, focus, reduced-motion, and failure states that are designed too.

React Bits and Motion documentation are secondary implementation references for
micro-interaction vocabulary. No new animation package is introduced; the
existing CSS and Motion stack are sufficient for this trial.

## Data and control flow

1. `RegionWallpaperLab` reads the typed local catalog and 13-crest catalog.
2. A ready candidate supplies WebM, MP4, and poster. The browser tries WebM,
   falls back to MP4, then keeps the poster on playback failure or reduced motion.
3. Selecting a ready region updates `data-region`, remounts media, and resets the
   playback-failure state. Pending regions cannot submit a false preview.
4. Enter runs the existing 760 ms semantic transition and calls the route owner
   with the selected region.
5. `productJourneyUrl` encodes the allowlist. `AuthenticatedProduct` passes it
   only to Account's presentation background and preserves it on Back/Continue.

## Verification contract

- unit: URL allowlist, bilingual copy, 13 controls with 11 pending, selection,
  poster fallback, reduced-motion, keyboard activation, and callback payload;
- build: TypeScript and Vite production build;
- E2E: no early product API I/O and keyboard activation carries
  `region=demacia` into `stage=account`;
- governance: default `/`, `production_media=0`, and rights gates unchanged;
- review: local research candidates are not mistaken for adopted or redistributable
  media.

## Explicit non-goals

- no automatic expansion from two candidates to all 13 regions;
- no file renaming or public asset promotion;
- no direct hotlinking, Workshop extraction, or licence inference;
- no MotionSites prompt/package import and no new UI dependency;
- no final Portal/Account visual QA, 8E exit, or 8F README packaging.

## References

- MotionSites public browse: https://motionsites.org/browse
- MotionSite public catalog: https://www.motionsite.ai/
- React Bits component index: https://www.reactbits.dev/get-started/index
- Motion React transitions: https://motion.dev/docs/react-transitions

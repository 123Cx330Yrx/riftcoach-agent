# 8E Region Focus Rail Implementation Plan

Status: `implemented locally / awaiting checkpoint-level evidence and user visual review`  
Design: `docs/plans/2026-08-29-8e-region-focus-rail-design.md`

## Task 1: freeze identity/media separation in tests

1. Add unit tests proving the presentation-region parser/builder accepts exactly
   the 13 known identities and still fails closed for unknown values.
2. Change RegionWallpaperLab tests from the old two-enabled/eleven-disabled
   card contract to 13 selectable rail controls, selected hero, generic CTA,
   optional motion and poster-only fallback.
3. Add activation tests for one-generation commit, duplicate click protection,
   full-motion and reduced-motion timing/focus.
4. Run the focused tests and retain the expected RED output before production
   code changes.

## Task 2: normalize local research assets

1. Copy the user-selected Bandle City Account still to an ignored local research
   path without modifying the source; record dimensions and SHA-256.
2. Copy/rename the supplied detailed emblem bytes to truthful `.webp` paths;
   keep the source files untouched and preserve Universe fallback.
3. Normalize the already prepared Portal research renditions into the typed
   catalog. Ixtal remains poster-only unless its conditionally accepted video
   receives the same WebM/MP4/poster treatment.
4. Keep every asset `rights=unverified` and outside the adopted-media manifest.

## Task 3: implement typed presentation state

1. Reuse `RegionIconId` as the presentation-region allowlist; keep Riot routing
   region types unchanged.
2. Let `RegionWallpaperCandidate` expose optional motion renditions and a required
   poster so presentation can continue without motion.
3. Update URL parsing/building and Account presentation props for all 13 regions.
4. Build maps once at module scope instead of repeatedly scanning catalogs in
   render loops.

## Task 4: implement the rail and hero

1. Replace scene-preview and grid DOM with selected hero, labelled horizontal
   rail, previous/next controls and the CTA action block.
2. Keep native buttons, visible labels, `aria-pressed`, Arrow/Home/End behaviour,
   scroll-to-selected and reduced-motion handling.
3. Render Universe crests in the rail and detailed local research art only in
   the selected hero.
4. Consolidate the old duplicate grid/breakpoint CSS rather than appending
   another cascade override.

## Task 5: implement authored handoff

1. Pass selected presentation identity into the shared activation overlay.
2. Replace the generic burst with selected-emblem aperture layers and
   Portal-departing/Account-arriving states.
3. Preserve generation guards, no double activation, immediate reduced-motion
   commit and delayed Account focus until the overlay stops owning the surface.
4. Use the new Bandle City Account still and verify that auth loading/error states
   inherit the same background without changing authentication logic.

## Task 6: visual and regression gates

1. Run focused unit tests, full frontend unit tests, typecheck and Vite build.
2. Run Playwright Portal/Account route tests, media failure, keyboard, reload,
   Back and reduced-motion scenarios.
3. Inspect live DOM/screenshots at 1440, 1024, 768, 390 and 320 px; run Axe and
   page-overflow checks.
4. Run `git diff --check` and `python scripts/check_project_governance.py`.
5. Update canonical execution, active plan and learning evidence with actual
   results and remaining media/rights limitations. Do not mark 8E complete.

## Execution result (2026-08-29)

- Tasks 1–5 are implemented with TDD coverage for 13 selectable identities,
  optional motion/poster fallback, URL copy/reload/Back, single-generation
  activation, delayed focus and reduced-motion behavior.
- RQ-159 added the 13-region bilingual presentation-copy registry and removed
  user-facing media bookkeeping without deleting machine/audit evidence.
- RQ-160 added semantic full heading names plus explicit, non-random visual
  lines for Portal and Account in both locales. Desktop and 390px live-DOM
  checks confirmed that the fixed lines do not overflow.
- Task 6 local gates passed: unit `297/297`, full frontend E2E `49/49`,
  typecheck and build. Desktop/mobile screenshots were reviewed for the focus
  rail, selected detail badge, generic sign-in CTA, transition aperture,
  Account arrival and both localized heading contracts.
- No commit, push or public deployment was performed. Media rights remain
  unverified, `production_media=0`, Workbench is untouched, and 8E is not closed.

## RQ-161 follow-up hygiene (2026-08-30)

- Account panel desktop position now uses an independent, bounded `top` offset;
  mobile explicitly resets it to zero so the handoff transform remains the only
  transition channel.
- Riot ID and both Account selects now share the same Manrope body typography;
  field captions share one readable scale. Full frontend unit is `297/297` and
  full E2E is `50/50` after adding computed-style desktop/mobile assertions.
- This is a local Portal/Account polish increment only. Workbench, Auth,
  routing, media adoption and `production_media=0` remain unchanged; 8E stays
  in progress.

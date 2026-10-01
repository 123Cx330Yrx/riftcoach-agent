# 8E Region Entry and Account Handoff Polish (2026-08-29)

## Scope

This is a bounded follow-up to the two-region wallpaper trial. It fixes the
arrival and recovery path without changing the production authentication
contract or promoting local wallpaper/badge candidates. The path is:

```text
region trial -> selected scene -> authored handoff -> account/auth state
             -> back to the same region trial
```

The default `/` cinematic Portal, `production_media=0`, and the existing
`research-candidate`/`rights=unverified` gates remain unchanged.

## Design read and protection rules

- Product surface: competitive-game coaching, Hextech Tactical Editorial.
- Register: product-first with a branded entry moment.
- Motion thesis: one shared activation state explains the handoff; a short
  crossfade/active-marker acknowledges region selection; no decorative engine.
- Keep Auth fail-closed. A missing session must remain visibly unavailable and
  must never become a fake demo login.
- Keep the typed region allowlist. Never construct an asset path from a query
  string.
- Detailed LoR-style badges are optional local research overlays. Universe
  crests remain the semantic fallback and source-of-truth selector family.

## Changes

1. Bring `surface=wallpaper-lab` under the existing `ProductJourney` owner so
   the portal activation state machine is reused. Navigation removes the
   preview-only surface flag, preserves the typed region, and does not reload
   the document. Back from Account/Auth returns to the same region selector.
2. Pass the presentation-only region through `AuthGate` and `AuthBoundary`.
   Unavailable/checking/signed-out states keep their existing copy and security
   semantics while showing the selected Account still and region identity.
3. Add a compact region identity strip to Account/Auth surfaces. It uses the
   selected region's Universe crest and, when present locally, a detailed badge
   overlay. Missing local badge files fall back without a broken image; a
   combined Piltover/Zaun research mark is never presented as a region-specific
   selector badge.
4. Add an optional detailed badge catalog for the user-supplied LoR-style icon
   files. The files remain ignored research material; a clean clone renders the
   Universe crest fallback.
5. Improve the trial's selection feedback: media layers crossfade, the active
   card has a bounded spotlight/focus marker, and the activation overlay has a
   localized aperture/burst layer while remaining interruptible and
   reduced-motion safe.
6. Make the handoff recoverable from a copied or reloaded Account URL. When the
   region trial owns the transition, the canonical Account URL carries the
   explicit `from=wallpaper-lab` marker; parsing that marker restores the
   region-picker back action without storing navigation truth only in React
   memory. Unknown markers still fail closed.

## Resource adoption boundary

The earlier broad research pass was re-read before this slice. It is useful
only when a source has a concrete consumer and a reversible implementation:

| Source pool | What is carried into this slice | What stays out |
|---|---|---|
| Riot Hextech Visual Language, Hextech UI, Client Animation, Universe | Square/diamond/circle grammar, directional energy, restrained cyan/gold hierarchy, and the Universe crest as the stable semantic fallback | Riot client chrome, copied art, official fonts, or a claim that a user-supplied badge is an official asset |
| Awwwards Technology, SiteInspire, Recent Design, Godly, Mobbin, Refero, Land-book, Lapa Ninja, Nicelydone, Dribbble, Behance | Editorial composition, type scale, hero pacing, and density checks used to keep the atlas from becoming a plain card wall | Screenshot collage, unverified interaction claims, or a second visual language pasted into the product |
| MotionSites (public browse and the user's offline index), Motion, 21st.dev Motion/Primitives, Magic UI, Animata, React Bits, Aceternity, Uiverse | A bounded active-card spotlight, diamond focus marker, poster-first media crossfade, and a localized aperture/burst handoff; all are written in existing CSS/React | Paid prompt/source copying, whole-library installation, floating HUD lines, or a new animation engine |
| OP.GG, Mobalytics, Blitz, Porofessor, LeagueOfGraphs | Nothing visual in this portal slice; their compact-stat and profile→insight lessons remain the Workbench information-architecture input | Invented match/history data or a data-dashboard pasted onto the entry surface |
| Langfuse, LangSmith, Phoenix, Braintrust, Honeycomb, MLflow | Nothing in this slice; their typed lifecycle/filter ideas remain the Evidence/Trace consumer | Prompt/context bodies, chain-of-thought, or an observability console in the portal |
| TrainingPeaks, WHOOP, Strava | Nothing in this slice; plan→train→progress remains the Training consumer | Readiness scores, progress claims, or a training panel before its data contract exists |
| Aura, v0, Lovable, Figma Make, Framer | Isolated visual/prototype comparison only | Generated code, platform lock-in, or treating a vendor prompt as a product specification |
| Image2, Photoshop, After Effects, video models, HyperFrames, Remotion, GSAP, Anime, OGL/Three, Steam Workshop | Research-only asset exploration and provenance/codec experiments; local poster/video candidates remain unadopted | Static images pretending to be interaction, unverified downloads, full-screen WebGL/video dependency, or Workshop redistribution |

The actual implementation therefore uses no new dependency: CSS pseudo-elements
provide the local spotlight and marker, two bounded media layers provide the
scene handoff, and the existing `PortalActivationOverlay` owns one shared
activation state. This is deliberately more than a minimal card list, while
remaining easy to remove or replace when a licensed production asset passes
the media gate. The five-module matrix remains the backlog source for later
Timeline, Trace, and Training work; those consumers are not silently pulled
into this Portal change.

## TDD and acceptance

- URL tests accept the preview surface only at the route owner and preserve a
  valid region; the explicit return marker survives reload; unknown regions or
  markers fall back safely.
- Region lab tests cover detailed-badge fallback, selection feedback,
  single activation, and reduced motion.
- Auth tests cover region propagation through checking/unavailable states and
  unchanged failure codes/copy.
- Browser tests cover no early product I/O, no full-page reload, keyboard
  activation, account arrival, and back-to-region return.
- Run frontend unit/E2E, typecheck/build, `git diff --check`, the Impeccable
  detector, and project governance. No external API or media generation call
  is made by this slice.

## Explicit non-goals

- No production Auth/RSO implementation or local-auth bypass.
- No promotion of ignored wallpaper/badge files into the adopted manifest.
- No wholesale MotionSites/React Bits/Aceternity/Uiverse source import.
- No final 13-region media expansion or 8E exit claim.

## 2026-08-29 front-only implementation pass

This pass keeps the scope on the front door and does not alter Workbench,
Coach, Timeline, Evidence or Training. The previously reviewed source pool is
used by consumer rather than by name:

- Riot/Universe crests remain the semantic fallback; the supplied detailed
  emblems are a progressive local overlay and can disappear without breaking
  selection.
- Gallery references (Awwwards, SiteInspire, Mobbin, Refero and their peers)
  informed the editorial split between the large scene proof and the compact
  atlas, including the 3-column desktop / 2-column narrow rhythm.
- MotionSites, Motion/21st, Magic UI, Animata, React Bits and Aceternity
  informed only the bounded spotlight, focus diamond and poster crossfade.
  No prompt, paid page or library source is copied into the product.
- Photoshop/After Effects, League Displays and Steam/Wallpaper Engine remain
  provenance and media-quality references. They do not grant redistribution
  rights and do not become runtime dependencies.
- OP.GG/Mobalytics, Langfuse/LangSmith/Phoenix, TrainingPeaks/WHOOP/Strava,
  chart libraries and design-to-code services remain reserved for their
  Workbench, Trace, Training and prototype consumers.

The implementation adds a poster thumbnail only to the two ready research
cards, keeps the actual page background video behind a stable poster, and
uses the existing cinematic policy to avoid loading the large local videos on
mobile. MP4 is listed before the Bandle WebM because the local MP4 sibling is
the audio-free fallback. The CTA now names its real destination (account
setup), and the copy says plainly that the other regions are still being
prepared. The old `awakening` images remain temporary foundation-preview
fallbacks until the later media gate can replace their CSS references and
files atomically; this pass does not promote or delete them.

## Current wording/status note (2026-08-30)

The paragraph above is retained as a historical trial snapshot. Its earlier
“account setup” CTA and “other regions being prepared” wording were superseded
by RQ-157/RQ-159: the current product CTA is the locale-neutral “进入登录界面” /
“Continue to sign in”, and all 13 presentation identities remain selectable
independently of motion readiness. RQ-161 adds only Account panel/control
typography hygiene; it does not reopen this trial or close 8E.

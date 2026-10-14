# 8E Region Focus Rail and Portal-to-Account Handoff Design

Status: `implemented locally / awaiting checkpoint-level evidence and user visual review`  
Checkpoint: `8e-productization / portal-motion-polish / official-wallpaper-fallback / region-catalog-expansion`  
Scope: Portal region presentation and Account handoff only; Workbench is out of scope.

## Problem and principle

The current research preview conflates two different facts:

1. which Runeterra region the user selected as presentation identity; and
2. whether that region currently has a locally audited motion candidate.

That coupling disables eleven region controls, hides the supplied high-detail
emblems inside very small marks, repeats the selected wallpaper as a thumbnail,
and leaves the real action in a small footer button. The fix follows a common
product/Agent principle: keep user intent as durable state and treat capability
availability as independent evidence. A selected region remains meaningful even
when its motion rendition falls back to a poster.

## Approved visual direction

Use a `Region Focus Rail`, not the old grid, a 3D coverflow, or an autoplaying
marquee:

- the selected wallpaper remains the full-viewport presentation layer;
- a selected-region hero shows the detailed local emblem when available and a
  stable Universe crest fallback otherwise;
- a horizontal rail contains all 13 simple Universe crests as real buttons;
- the selected crest receives a bounded gold/cyan focus treatment and is
  scrolled to the centre;
- the single primary action sits directly below the rail and reads exactly
  `进入登录界面` / `Continue to sign in`;
- the redundant scene-preview thumbnail, 13-card wall, duplicated current-region
  footer and corner CTA are removed.

External component sources remain mechanism references only. CSS Scroll Snap,
the WAI carousel/selection guidance, Motion/Aceternity control affordances,
React Bits track behaviour, and Uiverse control skins inform the contract. The
implementation stays in existing React, CSS and `motion`; it adds no Tailwind,
GSAP, Anime.js, Embla, icon package, paid prompt, or copied component source.

## State and media contract

`RegionIconId` is the 13-region presentation identity. It is not a Riot API
routing region and must never leak into Riot request routing. A separate optional
`RegionWallpaperCandidate` supplies motion/poster evidence for that identity.

```text
URL/rail selection -> selectedRegion (13-region identity)
                   -> candidateByRegion[selectedRegion]
                      -> motion when allowed and present
                      -> otherwise selected poster/static fallback
                   -> Account presentation region

Riot ID form routing -> americas/europe/asia/sea (unchanged)
```

All 13 rail items remain selectable. `data-media-ready` and supporting copy may
describe whether motion is available, but missing motion must not disable the
identity button or prevent the Account handoff. Selection updates the current
wallpaper-lab URL with `history.replaceState`; the Account handoff still uses a
new history entry and the restricted `from=wallpaper-lab` marker.

## Interaction contract

- The rail is a labelled horizontal list/navigation region, not an autoplaying
  slideshow. Every item is a native button with visible text and `aria-pressed`.
- Pointer/touch uses native horizontal scrolling and CSS scroll snap. Desktop
  previous/next buttons scroll one logical item. ArrowLeft/ArrowRight move
  selection, Home/End select bounds, and focus remains visible.
- Selecting a region updates the hero, global background, URL and Account
  presentation state. It does not make any product API call.
- The rail exposes the next item at narrow widths instead of trapping the user
  in an invisible scroll area.
- `prefers-reduced-motion` changes smooth scrolling to immediate movement and
  removes decorative scale/translation while retaining state feedback.

## Portal-to-Account handoff

The handoff must communicate cause rather than play an unrelated effect:

1. `0-240 ms`: the selected hero emblem, rail and CTA settle toward the selected
   visual centre while the current scene slightly quiets;
2. `240-760 ms`: a bounded region-coloured aperture/veil takes ownership of the
   viewport; there is no white flash, full-screen bloom or geometry explosion;
3. after route commit, the Account background is already present and its content
   enters in a short stagger while the aperture clears over about `240-360 ms`.

The total full-motion handoff remains within roughly `760-1000 ms`. Duplicate
activation is generation-guarded. Back navigation uses a shorter reverse-feel
Account exit without replaying the full spectacle. Reduced-motion and Save-Data
commit immediately, use only a short opacity crossfade, and never delay focus.

## Asset treatment

- Rail: tracked Universe crest assets, rendered in a common visual box. These
  remain the semantic fallback in clean checkouts.
- Hero: the desktop `*_emblem` files may be used only as local research overlays
  after their real WebP format is corrected. Their filename extension currently
  says PNG even though the bytes are WebP. Source/author/licence metadata is
  still missing, so they are not production or redistribution evidence.
- Void: use the approved balanced generated candidate only as a research hero
  fallback; it is not represented as Riot art.
- Bandle City Account: replace the frame-grab poster with the user-selected
  `4e498e9f..._fw1200webp.webp` local research still. Keep its source hash and
  `rights=unverified`; search/verify a higher-resolution original before any
  production promotion.
- `production_media` remains `0`. This slice changes local presentation, not
  the adoption or redistribution decision.

## Responsive visual hierarchy

- Desktop: selected hero about 144-176 px; rail shows 5-7 items; CTA is
  320-380 px wide and at least 56 px high.
- Tablet: hero about 120-144 px; rail shows about 4-5 items.
- Mobile: hero about 96-120 px; rail shows 3 items plus a partial next item;
  CTA becomes full width and remains at least 52 px high.
- Region labels stay at or above roughly 13-15 px, body/supporting copy at or
  above 14 px where space permits, and CTA text at 16-18 px. Late short-screen
  rules must not shrink the control back into the old 7-11 px range.

## Verification contract

Tests must prove:

- 13 identity buttons are selectable even when media is poster-only;
- rail selection, hero, URL and Account region agree after click, reload, copy,
  Back and popstate;
- the CTA copy is the generic sign-in destination and never interpolates a
  region name;
- no product API I/O occurs on Portal selection;
- WebM/MP4/poster, mobile, playback failure, Save-Data and reduced-motion
  fallbacks remain truthful;
- activation is single-generation, commits once, moves focus to Account only
  after the Account surface can receive it, and cannot be double-triggered;
- keyboard, 200% zoom, 1440/1024/768/390/320 widths and serious/critical Axe
  checks pass without page-level horizontal overflow.

## Explicit non-goals

- no Workbench, Coach, Training or Agent-runtime redesign;
- no claim that 13 motion files are production-ready;
- no new runtime dependency or copied external component;
- no change to Riot API routing semantics;
- no commit/push or public deployment in this local implementation batch unless
  separately authorized.

## Local implementation result (2026-08-29)

- All 13 identities now share one focus rail and use an independent bilingual
  presentation-copy registry. The lines are authored by RiftCoach and are not
  represented as verbatim Riot or champion quotations.
- User-facing media bookkeeping was removed. Readiness, codec, dimensions and
  duration remain machine-observable catalog/test evidence only.
- The handoff now uses a shared journey shell with `closing`,
  `background-handoff` and `idle` phases. The aperture originates near the
  selected rail focus, Account layers enter after route commit, and heading
  focus waits until the overlay releases the surface.
- RQ-160 replaces automatic display-title wrapping with an explicit bilingual
  line contract. Portal is `从一方之地，` / `启程。` and Account is
  `选择一位` / `召唤师。`; English receives equally intentional two-line
  variants. The full sentence remains the accessible heading name.
- Local verification passed: frontend unit `297/297`, full frontend E2E
  `49/49`, TypeScript typecheck and Vite production build. Responsive visual
  review covered Chinese and English at desktop and 390px mobile, including
  live-DOM overflow checks; governance and whitespace gates are rerun after
  persistent evidence is updated.
- Workbench was not changed. Research media remains rights-unverified,
  `production_media=0`, and the larger 8E checkpoint remains in progress.

## RQ-161 follow-up hygiene (2026-08-30)

- The Account panel's desktop vertical correction is a bounded `top` offset,
  separate from the handoff transform; mobile resets it to zero.
- The Riot ID input and both native selects share Manrope body typography, and
  all field captions share one readable scale. Computed-style assertions cover
  desktop/mobile position and control parity.
- The latest local verification is frontend unit `297/297`, E2E `50/50`,
  typecheck/build, live DOM and governance. This does not close 8E or change
  Workbench, routing, media rights or `production_media=0`.

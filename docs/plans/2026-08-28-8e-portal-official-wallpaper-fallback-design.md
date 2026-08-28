# Official wallpaper fallback for Portal

Decision record: [ADR-0069](../adr/0069-adopt-local-region-wallpaper-fallback.md)

## Decision trigger

Wan 3.0 official first-frame generation is stopped after the user-directed
route change. The new primary path is to use finished wallpaper scenes rather
than asking a video model to invent motion inside the complex Portal mother
image.

The first sample is the user-supplied `animated-demacia.webm`. It is a real
1920×1080 scene with continuous motion, but its source/redistribution rights
are not yet verified and its first/last frames are not a seamless loop. It is a
research candidate, not a production asset.

## Product shape

The Portal becomes a region-aware cinematic surface:

```text
region choice (no network)
  → selected local wallpaper + poster
  → semantic Portal activation control
  → one bounded transition
  → Account with a separate static wallpaper
```

The user chooses a Runeterra region before entering the Portal. The selected
wallpaper is a local, content-hashed candidate; the UI does not edit or repaint
its pixels. The central action is a DOM button placed in a quiet, measured area
of the composition, not a fake crystal image pasted over the artwork. Clicking
it keeps the existing single navigation latch and enters Account. Account gets
its own static poster/wallpaper so the two scenes have different visual jobs.

## Motion and media policy

- Keep the original wallpaper motion intact; do not add a generated veil,
  source duplicate, or global color filter.
- A video is progressive enhancement. The poster appears first; unsupported
  decode, Save-Data, reduced-motion, mobile constraints or playback failure use
  the poster without changing the journey state.
- Each candidate needs a WebM/MP4 pair, a poster, intrinsic dimensions, a
  focal point, a loop/seam assessment and a local removal path.
- If a wallpaper is not naturally seamless, do not hide the jump with an
  unbounded crossfade. Either choose a verified loop segment or keep it as a
  short controlled scene with a visible transition policy.

## Source and rights gate

Riot's League Displays site advertises HD wallpapers, screensavers and
Animated Art, but a desktop app listing is not by itself a grant to redistribute
the files inside an open-source web app. A Steam Workshop/Wallpaper Engine
scene is even more constrained: official Wallpaper Engine help says downloaded
wallpapers may need the original author's permission before republishing, and
scene wallpapers are not directly exportable as video. Therefore:

1. keep user-supplied and Workshop files in research/local-only storage until
   provenance and permission are recorded;
2. prefer Riot-hosted assets whose usage terms explicitly allow the intended
   presentation, or assets created by us/with a redistribution license;
3. never hotlink a Workshop file or commit a third-party scene package as a
   silent dependency;
4. record the source URL, creator/permission, hash, consumer, fallback and
   removal path for every adopted wallpaper.

## Implementation order

1. Add a strict region-wallpaper catalog separate from the existing four-entry
   Portal/Account cinematic manifest.
2. Build a local research preview using Demacia only; verify poster-first,
   browser decode, keyboard/focus, reduced-motion and mobile fallback.
3. Add a no-cost loop-segment/export audit. Transcode an H.264 sibling only in
   research output; do not call it production until the seam and rights gates
   pass.
4. Add further regions one at a time, each with the same audit envelope.
5. Only after a candidate set passes the source/format/rights gate, wire the
   region picker into the default Portal route and update the adopted media
   manifest. Existing Account and Workbench business control flow remains
   unchanged.

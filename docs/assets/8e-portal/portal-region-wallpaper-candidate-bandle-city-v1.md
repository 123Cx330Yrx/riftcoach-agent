# Bandle City wallpaper candidate audit

Status: `research-candidate` · `rights: unverified` · not adopted

## Source

- Local source: `C:/Users/33502/Desktop/RIFTCOACH/animated-bandlecity.webm`
- Copied research candidate: `web/public/assets/wallpapers/candidates/bandle-city.webm`
- Source SHA-256: `17da832a35c669df551663a2a363e43b825895ba1a1b7648a4d07694a0eddb6c`
- The scene visually matches Bandle City: a dark forest, luminous blue mushrooms, a tree bridge and small bioluminescent details.
- The original file includes an Opus audio stream. The preview uses muted playback and also has a separately encoded audio-free H.264 sibling.

## Technical audit

| Property | Observation |
| --- | --- |
| Video | VP8 WebM, 1920×1080, 25fps, 15.04s, `yuv420p`, 376 frames |
| Audio | Opus in source; omitted from the H.264 preview |
| Sampled adjacent motion | mean absolute difference `0.0043761693`; p95 `0.006180584` at 5fps/256px wide |
| Sampled first/last difference | mean absolute difference `0.0062992894` |
| Visual judgment | continuous environment motion is visible in sampled contact sheet; no production visual sign-off yet |

The measurements show that this is a genuinely animated candidate and that its sampled seam is relatively calm. They do not prove a seamless native loop, source ownership, or redistribution permission.

## Browser variants

- WebM: `/assets/wallpapers/candidates/bandle-city.webm` (source hash above; local candidate only)
- H.264 fallback: `/assets/wallpapers/candidates/bandle-city.mp4`, 1920×1080, 25fps, `yuv420p`, no audio, SHA-256 `786eac540d764f5b91265b6513f4651f2e1ba23012a7d3545ddba518cf13454d`
- Poster: `/assets/wallpapers/candidates/bandle-city-poster.webp`, SHA-256 `9c751c64eb3ae4cdb40a31ee9a9bae31ff081a57ad556c47a2fcfeeee71bbec9`

## Gates still open

1. Identify the official source and terms permitting local web presentation or redistribution.
2. Verify WebM and H.264 playback in supported desktop browsers and the mobile fallback behavior.
3. Verify `prefers-reduced-motion`, Save-Data and playback-error behavior use the poster without changing the journey state.
4. Decide whether the native seam is acceptable or whether a verified loop segment is needed.
5. Keep all files local-only until every gate passes; do not add them to the adopted media manifest or public runtime.

Machine-readable details are in `portal-region-wallpaper-candidate-bandle-city-v1.json`.

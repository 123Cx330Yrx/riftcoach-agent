# Ixtal dynamic wallpaper candidate audit

Status: `research-candidate · conditionally usable` · `rights: unverified` · not in adopted runtime media

## Decision

The candidate is visually acceptable as a restrained Ixtal Portal background:
it keeps the official splash composition clear and adds continuous, low-amplitude
motion without the global veil or camera drift seen in rejected Portal trials.
The current human review is “usable for now, slightly too light”. This is not a
final visual sign-off; keep the candidate replaceable and remind the owner to
choose later between keeping this soft motion, tuning it, or replacing it.

## Source and request identity

- Original local source: `C:/Users/33502/Desktop/RIFTCOACH/1a75d072fa01ec3d0cda3f87fc1bf18dce736424-5000x2811.jpg`
- Original source SHA-256: `b2d6c927c46454f2c638b1639eed55074f4c7971f026cf4a518552caf752230f`
- Provider input: `web/public/assets/wallpapers/candidates/portal-ixtal-first-frame-1920x1080.png`
- Provider input SHA-256: `c7837289972cb8e14ecb8ea0699d1dfd8c023342202c0033d7c860e027a24177`
- Provider source URL: `https://game.gtimg.cn/images/lol/universe/v1/assets/1a75d072fa01ec3d0cda3f87fc1bf18dce736424-5000x2811.jpg`
- Model/transport: DragonAPI `seedance-2-5`, first-frame-only, one POST
- Request: 10 seconds, adaptive aspect ratio, 720p, audio off, prompt extension off, watermark off
- Prompt SHA-256: `ac5ce04dfb15a12906e8c4e494dd88ef6bc5541d6094797c04e11d771d4552b8`
- Task: `task_kUGmfjSuAXEl5VJza7tlctIUAeQAxs2z`
- Downloaded candidate: `D:/riftcoach-agent/tmp/riftcoach-ixtal-seedance25-first-only-v1/ixtal-seedance25-first-only-v1.mp4`
- Candidate SHA-256: `c56f39dd768675f09f3559339ff05350b7e5c077d52a513380e014c69ac384aa`

## Technical audit

| Property | Observation |
| --- | --- |
| Container / codec | MP4 / H.264 High / `yuv420p` |
| Dimensions / rate | 1280×720, 24fps |
| Duration | 10.041667s |
| Audio | no audio stream |
| POST count | exactly 1; no automatic retry |
| Source-to-first visual check | mean absolute difference `0.014363` against the 960×540 source preview; architecture and crop remain recognizable |
| Sampled adjacent motion | mean absolute difference `0.0027503`, p95 `0.0040256` at 5fps/256px wide |
| Sampled first/last difference | mean absolute difference `0.0046950` |
| Region motion (adjacent mean) | left/foliage `0.0035211`; center/palace `0.0016868`; right/crystals `0.0029671`; sky `0.0035993`; midground `0.0025349`; foreground `0.0021096` |

## Human visual review

What works:

- Palace, mountain line, framing and painterly identity stay stable and sharp.
- Motion is present from the opening and persists through the clip: clouds/haze,
  foliage layers, light shafts and floating crystals all change over time.
- The scene reads as a premium, calm living environment rather than a copied
  still with a full-screen tint or an obvious camera move.
- No visible text, logo, watermark, black fade or audio dependency.

What is intentionally not claimed:

- Motion is subtle rather than “cool/strong”: leaves and midground vegetation
  have limited visible displacement, and the central palace is mostly a stable
  anchor. It is lighter than the Portal mother-image target by design.
- The clip is not proven to be a native seamless loop; the low sampled seam is
  only evidence for a calm transition, not a loop guarantee.
- Source ownership/redistribution terms for the downloaded file are not yet
  independently verified.

## Adoption gates still open

1. Verify source/redistribution terms for local web presentation.
2. Test WebM/H.264 playback, mobile fallback, Save-Data and
   `prefers-reduced-motion` poster behavior in the region journey.
3. Review the crop and readability behind Portal controls at real viewport sizes.
4. Revisit the visual choice later: keep this soft version, commission a
   controlled tuning pass, or replace it with a better official dynamic source.
5. Only after those gates may this candidate receive an adopted-media manifest
   entry; `production_media` remains `0` for now.


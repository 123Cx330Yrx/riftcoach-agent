# Portal Motion — Kling v3 Omni B2 result review

Date: 2026-08-28  
Checkpoint: 8E `portal-motion-polish`  
Decision: `research-candidate-rejected`; pause paid generation pending method review

## Executive result

The B2 task was created once and recovered safely. The first polling attempt
failed with a transient `HttpRequestException`; two bounded GET retries reached
`completed` and downloaded the result. `post_attempts=1` and
`recovery_post_attempts=0`, so the charge belongs to one task only.

The MP4 is technically valid: 8.041667 seconds, 1280×720, 24 fps,
H.264 Main/yuv420p, no audio, no duplicate decoded frames, and no visible
watermark. That is transport evidence, not visual adoption.

## Evidence

| check | result |
| --- | --- |
| output | `tmp/riftcoach-task5-video-bakeoff/dragon-kling-v3-omni-video-image-b2.mp4` |
| output SHA-256 | `5a9509ee3efdd2dbc0e8264bba88bba1315f3880e2c0932c8ac56da56f02cbba` |
| mother-image → first-frame SSIM | `0.9893096372` |
| first → last SSIM | `0.9953213687` |
| 0.5-second MAD left / center / right | `0.008926 / 0.007587 / 0.004271` |
| 0→4 s MAD left / center / right | `0.023736 / 0.018973 / 0.011454` |
| 0.5-second MAD near / mid / far | `0.005677 / 0.010753 / 0.004350` |
| mean-luma range | `0.010299` |
| external POSTs | `1` |
| production media | `0` |

The high first/last similarity and zero duplicate frames do not rescue the
visual failure: the motion is present but concentrated in the wrong carriers.

## Visual diagnosis

### What held

- The output opened and decoded cleanly after GET-only recovery.
- The opening composition and major architecture remain close to the mother
  image; this is materially better than Kling image-only B1.
- There is no obvious camera push, reframe, fade, or audio track.

### What failed

- The left Rift is rendered as a thick, smooth, synthetic ring. Its edge glow
  reads like plastic/tube shading rather than broad, irregular, layered energy
  moving inside the original aperture.
- The center event becomes a hard bright column. That is the exact failure the
  contract called out: the crystal should breathe through existing facets and
  reflections, not turn into a solid laser or white beam.
- Right constellation/terrain is materially quieter than left/center. Small
  star twinkles are not equivalent to independent arc, terrain, depth and
  reflection motion.
- Roads, seams, ground reflections, clouds, air and far depth remain largely
  static. The result therefore still looks like a focal-object animation with
  decorative changes, not a whole-scene ambient loop.

## Root-cause split

1. **Mode/input limitation (primary):** B2 supplied a base video as a temporal
   anchor and the mother image as an identity anchor, but the endpoint exposes
   no dependable region/time mask semantics. The model can preserve the camera
   while choosing where to invent motion; it chose the most salient subjects.
2. **Reference weakness:** the base video was the earlier Seedance pass whose
   motion was already uneven. Asking B2 to preserve its rhythm did not provide
   a strong blueprint for near/mid/far material motion.
3. **Prompt semantics (contributing):** despite explicit negatives, phrases such
   as “vertical swell”, “existing column texture” and “move arcs” still permit
   common generative shortcuts: beam, smooth ring and sparse stars. More words
   cannot create missing controllable layers.
4. **Mother image (not primary):** the first-frame SSIM shows the confirmed v2
   source is still a good identity anchor. The cheapness appears after motion
   interpretation, so another source redraw is not the immediate fix.
5. **Evaluation gap:** numeric MAD detects change but cannot tell whether the
   change is material motion, geometry drift, a cheap glow pulse or a static
   region with a few bright pixels. Human region-by-region review remains a
   hard gate.

## Process correction

The bounded model experiment was justified after the image-only failure, but it
still asked one generative pass to solve four different problems at once:
preserve geometry, invent organic motion, balance left/center/right, and close
the loop. That is the recurring failure pattern in Seedance v3/v4, Kling B1 and
now Kling B2. We should stop interpreting each new model as a clean slate when
the input/control shape is unchanged.

The next attempt must therefore begin with a no-cost method decision, not a
longer prompt or another model brand. The decision has to answer whether each
visible layer has a controllable carrier and a reversible fallback:

- immutable mother-image base and masks/inpainted backplates;
- separate Rift, crystal/refraction, right-field, road/reflection and
  near/mid/far atmosphere layers;
- deterministic frame clock and fixed camera for the loop;
- a small, local crystal activation transition kept separate from idle loop;
- perceptual review of every 0.5–1 second window, not just SSIM/MAD.

## Hold decision and bounded next plan

No new video generation, model switch, runtime integration or Account work is
authorized by this review. `production_media` remains `0`.

When work resumes, the proposed order is:

1. Freeze the visual contract and mark the exact carriers that can move without
   redrawing geometry.
2. Build a no-cost layered/compositor proof with visibly stronger low-frequency
   material motion (not the rejected line/HUD proof and not another opacity-only
   tweak). Use Image2/Photoshop only for concrete masks/backplates or texture
   tiles, never to repaint the master scene.
3. Compare that proof against one true video-edit/reference mode only if the
   provider can expose the same region/time controls. If it cannot, record the
   transport as unsuitable instead of buying another pass.
4. Re-run the visual gates; only an accepted candidate may become production
   media, then the Portal click transition and Account scene can be composed.

This review deliberately leaves the model ceiling open while rejecting the
current method result. It prevents another paid call from merely moving the
same cheap ring/beam failure around.

# Ixtal first-frame motion preflight

Status: `prepared` · no external generation call yet · production media `0`

## Goal

Create one controlled Ixtal dynamic-wallpaper candidate from the user's
5000×2811 official Universe splash. The original file remains immutable and
continues to serve as the source of truth. This is a simpler scene than the
Portal mother image: it has natural, already-visible motion carriers instead
of a synthetic crystal/Rift composition.

## Recommended method

Use first-frame-only image-to-video, not first+last interpolation and not a
camera-led pan. Downsample the source to a 1920×1080 PNG/JPEG only for the
provider input, record both source hashes, request 8–10 seconds at the highest
verified available resolution, audio off, prompt extension off and watermark
off. Start with one already-mapped Seedance 2.5 transport only after its exact
schema, price and quota are read back. Do not change model after a quality
failure without a new fault hypothesis.

Current source records:

- Original `1a75d072...-5000x2811.jpg` SHA-256: `b2d6c927c46454f2c638b1639eed55074f4c7971f026cf4a518552caf752230f`
- Provider input `portal-ixtal-first-frame-1920x1080.png` SHA-256: `c7837289972cb8e14ecb8ea0699d1dfd8c023342202c0033d7c860e027a24177`

## Motion brief

```text
Use the supplied Ixtal still as the immutable first frame of one continuous
landscape shot. Preserve the exact camera, lens, framing, architecture,
mountain silhouettes, palace geometry, floating crystal positions, palette and
painterly material identity. Animate only the existing scene in place:

• foreground leaves and hanging vines sway in a coordinated, low-amplitude
  breeze with natural overlapping phases;
• midground foliage shifts softly and the existing mist rises and drifts between
  vegetation layers, creating real near/mid/far depth;
• distant clouds and haze slide very slowly across the existing sky;
• existing sunlight shafts breathe gently along their current direction;
• each existing floating crystal makes a small, smooth local hover/rotation,
  never changing scale, shape or position enough to detach from its architecture;
• the palace and terrain remain the stable visual anchor while the living jungle
  environment continues moving from frame one to the final frame.

The motion is continuous, clearly perceptible and elegant, like a premium
painted fantasy environment coming alive. Keep the original emerald, jade,
turquoise and restrained warm-gold balance. Return naturally toward the opening
phase near the end for a calm loop.
```

## Hard negatives

```text
No camera pan, zoom, dolly, orbit, shake, Ken Burns move or reframing. No
architecture morphing, melting, repainting, duplicated structures, new objects,
new symbols, characters, text, logos, watermarks, neon outlines, HUD lines,
large energy beams, global colour wash, full-frame fog veil, exposure flash,
overbloom, texture boiling, artificial sharpened noise, floating detached
crystals, or static background with only one moving particle. Do not make the
palace or central crystal pulse like a UI button. Prefer stable geometry over
stronger motion if the two conflict.
```

## Acceptance gates

1. Request gate: source/first-frame SHA, model/schema, duration, resolution,
   audio, price and one-POST/no-retry runner are frozen before spending.
2. Identity gate: first frame preserves the source crop, palace and terrain;
   no global blur, drift or AI repainting.
3. Motion gate: leaves/vines, mist/clouds/light shafts, floating crystals and
   near/mid/far layers all remain visibly active; one particle is insufficient.
4. Technical gate: playable WebM/H.264 fallback, no audio, stable dimensions,
   no accidental watermark, and a documented loop/seam result.
5. Human gate: compare against the saved region stills; reject if it looks like
   a translucent overlay, camera drift or generic fantasy repainting.

The failed Portal motion experiments remain negative evidence only. A failed
Ixtal sample would keep model quality unknown and trigger diagnosis, not an
automatic route switch.

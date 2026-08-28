# Portal masked-inpaint plate proof result

Date: 2026-08-28  
Checkpoint: 8E `masked-inpaint-plate-proof`  
Decision: `research-proof-rejected`

## What this proof tested

This was the smallest honest test of the proposed Photoshop/ImageGen-style
workflow: keep the confirmed mother image as the base, use an ImageGen edit as
a clean backplate only inside one bounded Rift aperture, and place one
independent transparent fluid layer behind that boundary. The output was a
silent 960×540, 24 fps, 8 second local proof. No video model, API, network or
runtime media was used.

## Mechanical result

- The base is not shifted or globally tinted.
- The backplate is confined to the Rift interior mask; pixels outside it remain
  source-owned before encoding.
- The encoded output has 192 frames, H.264/yuv420p and no audio.
- The exact measurements are recorded in
  `tmp/portal-mask-proof-v2/masked-inpaint-plate-proof-v1-audit.json`.

These checks prove that the compositing plumbing is bounded. They do not prove
that the generated layer belongs in the scene.

## Human visual result

The clean backplate removes the original Rift vortex successfully, but the
transparent wisps read as a broad pasted blue ribbon when made visible. At the
low opacity needed to hide the sticker edge, the movement becomes too weak to
read. Raising opacity makes the Rift look like a translucent overlay rather
than a material inside the arch. The ImageGen backplate also differs subtly
outside the requested region, so it is not safe as a whole-image replacement;
the bounded mask avoids that global drift but cannot fix the plate's material
 mismatch.

## Decision and next action

This proof is `research-proof-rejected`. It is not a Portal loop and does not
enter `web/public/assets` or the runtime manifest. The result closes the
bounded Rift experiment without authorizing another batch of generic plates.
The next decision gate is a source-aware manual/segmented material authoring
route: either a human-authored Rift plate whose silhouette follows the real
aperture and whose original pixels are removed cleanly, or a video-editing
mode that accepts explicit masks and preserves the backplate. Until one of
those routes is available, keep the high-quality static mother/poster and do
not spend another paid generation call.

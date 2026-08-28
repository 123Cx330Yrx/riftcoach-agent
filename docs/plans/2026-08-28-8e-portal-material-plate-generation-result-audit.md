# Portal Material Plate Generation Result Audit

Date: 2026-08-28  
Checkpoint: 8E `material-plate-generation-gate`  
Decision: `research-plate-preflight-rejected`; no runtime adoption

## What was tested

Five built-in image-generation calls produced independent candidates for the
Rift, right field, road reflection and crystal. This was not a video call and
did not upload the Portal mother image. Every output stayed under the Codex
generated-image directory and outside the repository/runtime.

The objective was narrow: determine whether a standalone RGBA plate could be
placed over the sharp mother image without carrying a new scene, new geometry
or a broad color veil. An alpha channel alone was not considered sufficient.

## Results

| plate | observation | decision |
| --- | --- | --- |
| Rift blob | contiguous blue fluid mass; direct composite reads as a pasted water blob | rejected |
| Rift separated wisps | separated broad wisps; useful only as a possible control texture until a clean backplate exists | research-only |
| Right stardust | sparse stars are promising, but a broad dark-blue field needs alpha keying and terrain-aware occlusion | rejected unmasked |
| Road caustic | water-like field with broad blue opacity; would veil the road | rejected unmasked |
| Crystal refraction | shattered crystal geometry and fragments; violates the original crystal identity | rejected |

## Root cause

Generic transparent imagery does not know the mother image's exact occlusion,
perspective, material boundaries or existing crystal geometry. Direct placement
becomes a sticker; increasing strength becomes a veil; preserving the scene
too strictly makes the effect disappear. This is the same representation
conflict seen in the source-shift and procedural-noise proofs.

## Decision and next step

Do not generate more unmasked plates and do not attach these outputs to a
video. The next proof is `masked-inpaint-plate-proof`: start with one bounded
Rift mask, remove only the original movable energy into a matching backplate,
place one transparent plate behind that boundary, and review it at 100% over
the active source. Only after that passes should road/right/crystal plates be
attempted.

Photoshop is suitable for this manual workflow, but it is not installed on the
current machine. Image2 credentials exist, but the configured proxy
`127.0.0.1:7890` is unreachable; no direct bypass was used. Built-in imagegen
remains a preview source, not an adoption path until masked backplate evidence
passes. `production_media` remains `0`.

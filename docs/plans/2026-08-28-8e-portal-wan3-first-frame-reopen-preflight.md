# Wan 3.0 official first-frame reopen preflight

## Why reopen Wan

The earlier Wan sample was not a fair test of continuous motion: it used the
same image as both `first_frame` and `last_frame`, a long scene-description
prompt, and the official console's 30 fps/watermark behavior. Its rejection is
valid for that request, but it does not establish Wan's first-frame-only
behavior. The user has now explicitly asked to re-open the official Wan 3.0
route rather than continue the visibly cheap local plate proof.

## Narrow hypothesis

Use only the confirmed Portal mother image as `first_frame`, omit `last_frame`,
use `ratio=adaptive`, and describe motion rather than repainting the scene.
This gives the model freedom to create continuous material motion while still
locking the opening frame. A 12-second, 1080P, audio-off diagnostic is long
enough to judge sustained movement; it is not a production-loop claim.

The prompt deliberately removes the earlier central burst. That event will be
considered only after a model can first sustain left/center/right and
near/mid/far motion. The right field is a hard visual gate, not a decorative
afterthought.

## Official contract readback

Alibaba's current Wan 3.0 API documentation states that the model supports
first-frame image-to-video, first/last-frame image-to-video and a separate
reference-based mode. The first/last-frame types cannot be mixed with
reference types; `ratio=adaptive` is recommended for matching input media;
duration is 2–30 seconds; and `prompt_extend`, `audio`, `seed` and
`watermark` are explicit parameters. The API is asynchronous and requires the
model, endpoint and API key to belong to the same region. See the [official
API reference](https://help.aliyun.com/en/model-studio/wan3-video-generation-api-reference)
and [official model pricing](https://help.aliyun.com/en/model-studio/model-pricing).

The official prompt guide makes the same distinction we are applying here:
for image-to-video, the image already supplies the entity, scene and style,
so the text should concentrate on motion and camera movement. This prompt is
therefore intentionally shorter and motion-first; it names the visible
carriers (Rift currents, crystal refraction, right-field depth and surface
reflections) instead of rewriting the artwork as a second scene description.
See the [official image-to-video prompt guide](https://help.aliyun.com/en/model-studio/text-to-video-prompt).

## One-call guard

Before the POST, the runner must read back the active account region, matching
endpoint and current quota/price. It then verifies the source SHA, prompt SHA,
`wan3.0-video`, `1080P`, `adaptive`, 12 seconds, audio off, prompt extension
off and watermark off. The runner accepts the key only through a local secure
prompt, makes one POST, and polls by task ID. A network error may retry a GET;
it may never create another task. A successful output remains research-only
until codec, source identity, motion distribution, seam and human visual
review all pass.

## Visual scorecard

The output must show continuous, simultaneous, readable motion in the left
Rift, central crystal/platform, right constellation/terrain and near/mid/far
environment. The camera, geometry, linework and composition must stay locked.
Reject a hard torus, broad pasted ribbon, central laser/white flash, frozen
right side, global fog veil, exposure pulsing, camera drift, watermark or
unrecoverable source drift. Pixel MAD is supporting evidence only; it cannot
override the human material-motion gate.

No output from this preflight enters `web/public/assets`, the runtime manifest,
or `production_media` automatically.

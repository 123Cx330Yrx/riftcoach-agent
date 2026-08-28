# Portal Layer Assets and Occlusion Proof Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract crisp, source-derived energy/material layers from the confirmed Portal mother image so deterministic motion can move only existing light and texture, never the structural scene.

**Architecture:** Keep the resized mother image as an immutable base. Build feathered region masks and a source-derived high-energy alpha for each carrier. Render each carrier as a transparent RGBA layer with periodic local shifts, then composite it over the untouched base. This is a research renderer, not a browser runtime or an external-model call.

**Tech Stack:** Python 3.11, Pillow, NumPy, FFmpeg/ffprobe. No OpenCV, no network, no Image2 call, no WebGL runtime dependency.

---

### Task 1: Freeze layer/occlusion contract

Create `experiments/portal_layer_assets_proof_v1/layer-contract.json` with the v2 source SHA, output timeline, seven carriers, source-derived alpha policy, maximum pixel shift, occlusion rules, and research-only boundary.

### Task 2: TDD the extraction and render invariants

Create `tests/test_portal_layer_assets_proof_v1.py`. Tests must require source locking, deterministic frame count, all carriers, no remote input, base-preserving composition, alpha-only movable layers, and explicit no-camera/no-full-frame-overlay rules.

### Task 3: Implement deterministic layer extraction and renderer

Create `experiments/portal_layer_assets_proof_v1/render_material_layers.py`. It will create feathered masks, derive alpha from source luminance/chroma, save inspectable mask/layer previews, and render a fixed 8s/24fps sequence with periodic local shifts and a bounded central swell. The base is never shifted, tinted globally, or blurred.

### Task 4: Produce and inspect a research proof

Run the renderer on the v2 mother image, encode a silent H.264/yuv420p/BT.709 MP4, extract keyframes and contact sheets, calculate source/seam/region/depth metrics, and inspect at full resolution for veil, ghosting, geometry drift, and actual material motion.

### Task 5: Close or reject the proof

If the source remains crisp and the motion reads as material rather than a mask overlay, record the layer assets as a reusable production-candidate foundation. If it still reads cheap or too subtle, reject it and stop local shader tuning. In either case update canonical evidence, run focused/full/governance gates, commit and public-CI the result; do not add media to runtime.

## Result of the bounded proof

The source-derived high-pass renderer produced a sharp, silent 1920×1080/24fps
8-second MP4 with no duplicate frames. The base geometry remains crisp and the
moving pixels are limited to source highlights inside named masks. Human review
accepted this as a reusable foundation, not as an adopted Portal loop: the
motion is still too restrained and lacks genuine occlusion/backplate depth for a
MotionSites-level result. The next gate is `material-plate-generation-gate`.

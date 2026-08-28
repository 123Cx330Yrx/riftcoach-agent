# Portal Material Plate Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce independent, transparent material plates that can move over the immutable Portal mother image without source-edge ghosting or a full-frame veil.

**Architecture:** Generate blue/cyan RGBA plates from deterministic low-frequency noise and bounded masks. The base source image is rendered once and never shifted, blurred, or globally tinted. Each plate receives its own periodic local motion and is composited with a hard alpha ceiling; the central swell is scoped to the crystal plate only.

**Tech Stack:** Python 3.11, Pillow, NumPy, FFmpeg/ffprobe. The plate generator is local-only and does not call Image2, a video model, or a remote service.

---

### Task 1: Freeze the plate contract

Create `experiments/portal_material_plate_proof_v1/plate-contract.json` with source SHA, seven independent plate roles, output timeline, alpha/occlusion policy, and no-runtime/no-network boundary.

### Task 2: Write failing tests

Create `tests/test_portal_material_plate_proof_v1.py`. Require independent RGBA plates, immutable base policy, named central-event scope, no source-image duplication in the renderer, no remote URLs, deterministic seed, and exact 24fps/8-second output contract.

### Task 3: Implement the plate generator and compositor

Create `experiments/portal_material_plate_proof_v1/generate_material_plates.py`. Generate inspectable transparent plates from seeded smooth noise, create a locked-base composite, animate each plate on a periodic local clock, and pipe a silent H.264/yuv420p/BT.709 MP4 to FFmpeg. The base is never blurred or shifted.

### Task 4: Low-resolution visual gate

Render 960×540 with stronger but bounded plate motion. Inspect plate alpha contact sheets and 0/3/4/7-second composite frames for ghosting, veil, hard rings, beams, and right-field/far inactivity. Reject before spending time on 1920×1080 if the visual carrier is wrong.

### Task 5: High-resolution evidence and closure

If the low-resolution gate is clean, render 1920×1080, audit source identity/seam/coverage/codec, record the result, and decide whether this is a reusable production foundation. It must remain research-only until a separate runtime media adoption gate passes.

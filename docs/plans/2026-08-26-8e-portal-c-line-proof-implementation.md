# 8E Portal C-Line Proof Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Build a reproducible, research-only 8-second Portal motion-direction proof that animates every major scene region while preserving the confirmed mother image and keeping the corrected generative A line as a measured fallback.

**Architecture:** A tracked HTML/SVG composition and strict JSON contract define eight deterministic motion systems. A Python wrapper verifies source/tool identities, renders a PNG sequence with an already-vetted local HyperFrames 0.8.14 installation, encodes a compatibility preview with fixed FFmpeg settings, and emits body-free metrics; generated media remains outside the repository.

**Tech Stack:** HTML/CSS/SVG, Python 3.11 standard library, HyperFrames 0.8.14 isolated renderer, FFmpeg/ffprobe, pytest.

---

### Task 1: Freeze the proof contract in red tests

**Files:**
- Create: `tests/test_portal_cinematic_proof.py`
- Create: `experiments/portal_cinematic_proof/motion-contract.json`

1. Write tests that require schema `1.0`, source path/SHA, 1920×1080, 24fps, 192 frames, eight named motion systems, no remote URL/audio/randomness, exact renderer `hyperframes@0.8.14`, research-only output, and a corrected-A fallback clause.
2. Run `\.venv\Scripts\python.exe -m pytest tests\test_portal_cinematic_proof.py -q` and confirm collection/contract failure.
3. Add the minimal contract JSON and decoder assertions needed for the test to proceed to composition checks.
4. Run again and keep the expected missing composition/renderer failures red.

### Task 2: Implement the deterministic scene graph

**Files:**
- Create: `experiments/portal_cinematic_proof/index.html`
- Create: `experiments/portal_cinematic_proof/README.md`
- Modify: `tests/test_portal_cinematic_proof.py`

1. Add a locked base source plus `left-atmosphere`, `rift-interior`, `route-energy`, `crystal-tower`, `star-map`, `foreground`, and `global-light` layers; the eighth contract system is the locked base.
2. Use fixed SVG paths/masks and CSS keyframes only. All animations use `7.958333s`, have equal start/end state, fixed coordinates and no network/font/script/random source.
3. Tests parse the HTML and require all IDs, the exact source filename, timeline metadata, no remote schemes, no `audio`/`video`/`canvas`, and no camera transform on the base.
4. Run the focused test and confirm green.

### Task 3: Implement the isolated renderer wrapper

**Files:**
- Create: `scripts/render_portal_cinematic_proof.py`
- Modify: `tests/test_portal_cinematic_proof.py`

1. Add a dry-run path that verifies source SHA, composition/contract paths, local HyperFrames package version, FFmpeg/ffprobe presence, and that output is outside the repository.
2. Add execute mode that copies only the composition/source into a temporary project, creates an isolated HOME, sets `HYPERFRAMES_NO_TELEMETRY=1` and `DO_NOT_TRACK=1`, runs local `check`, renders PNG sequence at 24fps/one worker/no browser GPU, then encodes H.264 yuv420p/BT.709/no-audio/faststart.
3. Never install packages, call `npx`, auth, cloud, publish, provider, registry, feedback or telemetry commands. Do not save raw process output containing external data.
4. Test argv/env/path construction with fakes, then run focused tests green.

### Task 4: Render and audit the motion-direction proof

**Files:**
- Research only: `C:\Users\33502\Documents\Agent\tmp\riftcoach-task5-c-line-proof\...`
- Modify after evidence: `docs/plans/2026-08-26-8e-portal-c-line-proof-design.md`
- Modify after evidence: `docs/learning/8e-portal-motion-polish-walkthrough.md`
- Modify after evidence: active planning and canonical state files

1. Run wrapper dry-run and record body-free identities.
2. Execute HyperFrames `check`, raw snapshot/PNG sequence and fixed FFmpeg encoding without network/model calls.
3. Compute source→first, frame0→191, adjacent p95/seam, left/center/right and 3×3 motion coverage; create a 0/2/4/6/end contact sheet.
4. Inspect full-size frames/video for mask edges, synthetic HUD feel, source drift, frozen large regions and focus-by-focus motion.
5. Record one of three exact verdicts: `proof_pass_continue_hybrid`, `proof_fail_reopen_corrected_a`, or `proof_inconclusive_requires_layer_asset_gate`.

### Task 5: Close the proof batch

1. Run focused tests, governance, compileall, pip check and `git diff --check`; no generated media may be staged.
2. Update the eight-dimensional walkthrough, adoption ledger, active plan, state, roadmap/amendment, capability matrix and requirement history only where the observed verdict changes execution.
3. Commit the reproducible code/evidence separately, push, and wait for exact-SHA `pytest`, `postgres-migrations`, and `packaging-smoke` success.
4. Only a passed hybrid proof may proceed to organic plate calls; a failed proof switches to the one corrected-A comparator defined in RQ-125.


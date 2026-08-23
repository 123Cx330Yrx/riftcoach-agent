# 8E Batch D Rift Command Center Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build and verify a visually distinctive, fixture-backed RiftCoach recent-review workbench without connecting real API, SSE, or Auth.

**Architecture:** Add an isolated `web/` React/Vite/TypeScript package. Keep immutable safe fixtures behind a client-state boundary, render product state separately, and use a small autonomous CSS token system plus Motion/Radix primitives. Verification is layered across Vitest, Playwright, visual inspection, existing Python gates, and exact-SHA public CI.

**Tech Stack:** React 19, TypeScript 7, Vite 8, vanilla CSS, Motion, Radix Dialog, Vitest/Testing Library, Playwright, axe-core.

---

### Task 1: Freeze the web package and dependency boundary

**Files:**

- Create: `web/package.json`
- Create: `web/package-lock.json`
- Create: `web/tsconfig.json`
- Create: `web/tsconfig.app.json`
- Create: `web/tsconfig.node.json`
- Create: `web/vite.config.ts`
- Create: `web/playwright.config.ts`
- Create: `web/index.html`
- Create: `web/src/test/setup.ts`
- Modify: `.gitignore`

**Step 1: Write the failing package-boundary test**

Create `web/src/app/packageBoundary.test.ts` to read an exported dependency manifest and assert that runtime dependencies are limited to React, Motion, Radix Dialog and the two local font packages. Explicitly reject Tailwind, GSAP, Anime.js, OGL/Three, ECharts and copied component-library packages.

**Step 2: Run the test to verify the red state**

Run: `npm test -- --run src/app/packageBoundary.test.ts`

Expected: FAIL because the web package and dependency manifest do not exist.

**Step 3: Create the minimal package**

Pin current compatible package versions, generate the exact npm lockfile with scripts disabled, configure Node 24-compatible Vite/Vitest, and keep Playwright browsers outside the repository. Add ignored paths for `web/dist`, coverage, Playwright report and test results.

**Step 4: Verify install, typecheck shell and dependency boundary**

Run: `npm ci --ignore-scripts && npm test -- --run src/app/packageBoundary.test.ts`

Expected: PASS with no post-install code execution.

### Task 2: Build strict fixture contracts before UI

**Files:**

- Create: `web/src/contracts/workbench.ts`
- Create: `web/src/fixtures/workbenchFixtures.ts`
- Create: `web/src/fixtures/workbenchFixtures.test.ts`

**Step 1: Write failing contract tests**

Cover the allowlisted `ClientResourceState`, `ProductState`, selected player profile, recent summary, task/run, Evidence and Training shapes. Recursively scan every fixture and fail on forbidden keys/values such as `owner_id`, `puuid`, `prompt`, `context_body`, `raw_response`, `worker_id`, `lease_token`, `refresh_id`, local paths and DSNs.

```ts
expect(assertPublicWorkbenchFixture(publishedFixture)).toBeUndefined()
expect(() => assertPublicWorkbenchFixture({ ...publishedFixture, owner_id: "x" }))
  .toThrow(/forbidden fixture field/)
```

**Step 2: Run the focused test and confirm failure**

Run: `npm test -- --run src/fixtures/workbenchFixtures.test.ts`

Expected: FAIL because contracts/fixtures are missing.

**Step 3: Implement immutable scenario fixtures**

Add `published`, `degraded`, `rejected`, `not_ready`, `loading`, `empty` and `error`. Use invented accounts, explicit `fixture_mode: true`, no ShowMaker default, and separate self/observed views. Unknown scenario input returns a safe client error rather than published.

**Step 4: Run focused tests**

Run: `npm test -- --run src/fixtures/workbenchFixtures.test.ts`

Expected: PASS.

### Task 3: Implement the semantic shell and visual tokens

**Files:**

- Create: `web/src/main.tsx`
- Create: `web/src/app/App.tsx`
- Create: `web/src/app/App.test.tsx`
- Create: `web/src/components/RiftAtmosphere.tsx`
- Create: `web/src/components/CommandRail.tsx`
- Create: `web/src/styles/tokens.css`
- Create: `web/src/styles/global.css`
- Create: `web/src/styles/workbench.css`

**Step 1: Write the failing shell tests**

Assert a skip link, header/main/nav/aside landmarks, one page `h1`, fixture disclosure, selected player/region/relationship, and real section anchors. Assert decorative Rift SVG is hidden from accessibility APIs.

**Step 2: Run focused tests**

Run: `npm test -- --run src/app/App.test.tsx`

Expected: FAIL because the shell is missing.

**Step 3: Implement the shell and autonomous visual system**

Add local Oxanium/Manrope imports, obsidian/navy/cyan/gold/violet/risk tokens, a custom Rift contour/three-lane atmosphere, Coach Core focus field, cut-corner panels, visible focus and a one-time reveal sequence. Do not copy external component source or Riot art.

**Step 4: Verify unit tests and production build**

Run: `npm test -- --run src/app/App.test.tsx && npm run build`

Expected: PASS and a successful `dist` bundle.

### Task 4: Render client and product state honestly

**Files:**

- Create: `web/src/components/ProductStateBanner.tsx`
- Create: `web/src/components/RecentFormPanel.tsx`
- Create: `web/src/components/CoachBrief.tsx`
- Create: `web/src/components/TrainingPanel.tsx`
- Create: `web/src/components/WorkbenchState.test.tsx`
- Modify: `web/src/app/App.tsx`

**Step 1: Write the state-matrix red tests**

Prove loading never flashes published, empty differs from error, not-ready has no fake percentage, degraded retains report plus limitation, rejected hides the report, and observed profiles never say “my training completion”.

**Step 2: Run the focused test**

Run: `npm test -- --run src/components/WorkbenchState.test.tsx`

Expected: FAIL before components exist.

**Step 3: Implement minimal state-aware panels**

Render direct fixture values with text/icon/reason labels. Add an unordered win/loss share, aggregate Wins-vs-Losses comparison, primary role/champion text tags and a tactical brief. Do not add per-match cards, dates, W/L sequences, invented Timeline or run-history list. Use Motion only for bounded reveal; numeric values render directly at their final values.

**Step 4: Run state and app tests**

Run: `npm test -- --run src/components/WorkbenchState.test.tsx src/app/App.test.tsx`

Expected: PASS.

### Task 5: Add the accessible Evidence Drawer

**Files:**

- Create: `web/src/components/EvidenceDrawer.tsx`
- Create: `web/src/components/EvidenceDrawer.test.tsx`
- Modify: `web/src/app/App.tsx`
- Modify: `web/src/styles/workbench.css`

**Step 1: Write failing interaction tests**

Use `userEvent` to open by keyboard, inspect source/join/gap/digest labels, close with Escape, and verify focus returns to the trigger. Scan rendered text for private/runtime fields and hidden reasoning labels.

**Step 2: Run the focused test**

Run: `npm test -- --run src/components/EvidenceDrawer.test.tsx`

Expected: FAIL before the drawer exists.

**Step 3: Implement Radix-backed behavior and RiftCoach visuals**

Let Radix manage semantics/focus only. Implement the overlay, sheet, energy edge and state transitions locally. Under reduced motion, remove horizontal transforms and use an immediate/short fade.

**Step 4: Run focused interaction tests**

Run: `npm test -- --run src/components/EvidenceDrawer.test.tsx`

Expected: PASS.

### Task 6: Verify responsive, keyboard and reduced-motion behavior

**Files:**

- Create: `web/tests/e2e/workbench.spec.ts`
- Create: `web/tests/e2e/visualEvidence.spec.ts`
- Modify: `web/playwright.config.ts`
- Modify: `web/src/styles/global.css`
- Modify: `web/src/styles/workbench.css`

**Step 1: Write failing Playwright flows**

Test 1440×1000 and 390×844 viewports, no horizontal overflow, anchor navigation, full keyboard Drawer flow, rejected/degraded scenarios, observed boundary, and `reducedMotion: "reduce"`. Run axe and reject critical/serious violations.

**Step 2: Install the isolated browser and confirm red**

Run: `npx playwright install chromium && npm run test:e2e`

Expected: FAIL until responsive/a11y contracts are complete.

**Step 3: Implement only the required fixes**

Add responsive grid collapse, touch-sized controls, mobile Drawer geometry, reduced-motion CSS and focus rings. Keep decorative atmosphere static on mobile/reduced-motion instead of deleting the visual identity.

**Step 4: Run all frontend gates**

Run: `npm run typecheck && npm run test:unit && npm run build && npm run test:e2e`

Expected: all commands PASS.

**Step 5: Capture and inspect visual evidence**

Generate desktop published/degraded, mobile published and reduced-motion screenshots under a temporary directory. Inspect every image; fix clipping, hierarchy, contrast, awkward empty space or generic styling before copying the accepted evidence to `docs/assets/8e-batch-d/`.

### Task 7: Add blocking public CI without changing backend packaging

**Files:**

- Modify: `.github/workflows/tests.yml`
- Create: `tests/test_frontend_package_contract.py`

**Step 1: Write the failing repository contract test**

Assert the workflow cache includes `web/package-lock.json` and the existing `pytest` job runs `npm ci --ignore-scripts`, typecheck, unit, build and Playwright. Assert Docker runtime does not copy frontend source in Batch D.

**Step 2: Run the focused Python test and confirm failure**

Run: `python -m pytest tests/test_frontend_package_contract.py -q`

Expected: FAIL before workflow integration.

**Step 3: Update CI minimally**

Reuse the existing Node 24 setup, add the web lockfile to npm cache paths, install Chromium explicitly, and run frontend gates in the existing blocking `pytest` job. Do not add frontend files to the Python image or claim deployment.

**Step 4: Verify workflow/package contract**

Run: `python -m pytest tests/test_frontend_package_contract.py -q`

Expected: PASS.

### Task 8: Durable evidence and checkpoint closure

**Files:**

- Create: `docs/learning/8e-batch-d-rift-command-center-walkthrough.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Modify: `docs/project_execution_state.md`
- Modify: `docs/requirements_change_log.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`

**Step 1: Write the eight-dimension walkthrough**

Cover problem/principle, design/implementation, code map, data/control flow, verification, runbook, failure/security/
boundary and interview-safe wording. Keep whole 8E coverage `planned` until later Auth/API/deployment batches finish.

**Step 2: Run proportional and full local gates**

Run focused frontend/Python tests, frontend full gates, full `python -m pytest -q`, both RAG evaluations, Harness dry-run,
`python -m compileall -q app scripts tests`, dependency/license checks, forbidden secret/run-data scans,
`python scripts/check_project_governance.py`, and `git diff --check`.

Expected: all applicable gates PASS; any remaining skip is reported with independent public evidence responsibility.

**Step 3: Create one independent implementation/evidence commit**

Review staged files and cached diff, commit only Batch D files, push the exact SHA, and wait for blocking `pytest`,
`postgres-migrations` and `packaging-smoke`. The `pytest` job must include all frontend gates on that same SHA.

**Step 4: Close only Batch D**

Record exact SHA/run/job evidence. Do not mark 8E complete or enter real API/SSE/Auth, HTTPS, backup, deployment or 8F.

# Rift Awakening → Broadcast Workbench Visual Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the approved cinematic-portal-to-broadcast-workbench direction into a testable, layered React visual slice without changing product truth or adding an unbounded visual dependency.

**Architecture:** Add an isolated `AwakeningScene` presentation surface that consumes a typed presentation state and existing profile/product-state adapters. CSS/SVG own the environment, routes, shape semantics, and responsive fallback; React Motion owns only state transitions. Generated/Photoshop assets are replaceable atmosphere layers, never the source of UI text or data.

**Tech Stack:** React 19, TypeScript, Vite, vanilla CSS tokens, inline SVG, existing Motion dependency, Playwright/Vitest, Image2/Photoshop for preview-only layered art.

---

## 1. Teaching contract

The concrete problem is that an attractive concept image does not automatically
become an honest product interface. The implementation must preserve real
identity, relationship, product-state, and evidence contracts while adding a
visual narrative around them.

The Agent/software principle is progressive enhancement: semantic DOM and typed
state are complete first; atmosphere and motion add depth but cannot create a
state, invent data, or hide an error. The portal only owns presentation and
handoff choreography. It does not perform authentication, Riot lookup, RSO
binding, or external API calls.

## 2. Surface contract

### Entry states

```text
idle → editing → calibrating → ready|degraded|rejected
                         ↘ client-error
```

`reduced-motion` is a presentation mode over every state, not a product state.
The DOM must expose the same labels and action order in every mode.

### Shared visual grammar

| Concern | Contract |
|---|---|
| Geometry | square = structure, diamond = progress, circle = focus |
| Structure | obsidian/navy surfaces, cyan/teal routes and active focus |
| Coach | restrained gold for Coach emphasis and published completion |
| Provenance | violet metadata only, never a generic AI gradient |
| Risk | red plus text/icon explanation for degraded/rejected |
| Type | existing Oxanium display + Manrope body baseline; no Inter/Roboto substitution without a separate audit |
| Motion | 160ms feedback, 320ms state, 700–1200ms handoff, low-frequency ambient only |
| Layout | asymmetric editorial grid; no equal-card wall and no centered form as the whole composition |

### Entry composition

```text
ambient Rift field
  ├─ contour/route SVG layer
  ├─ replaceable fog/crystal/light layers
  ├─ Coach Core focus
  └─ semantic identity calibration form
       ├─ Riot ID
       ├─ routing region
       ├─ self / observed relationship
       └─ explicit action and state explanation
              ↓ route ignition
        existing Broadcast Workbench
```

## 3. Asset and source plan

### Asset pipeline

1. Image2 generates concept/mood and abstract environment candidates with no
   readable copy, logo, champion portrait, or recognizable client recreation.
2. Photoshop removes artifacts, composes layers, color-grades, and exports
   replaceable WebP/PNG plates and masks. The concept image is never used as a
   data-bearing screenshot.
3. CSS/SVG rebuilds all geometry that must respond to state: routes, markers,
   focus rings, borders, progress shapes, and status icons.
4. React renders all real controls, text, profile identity, relationship,
   product state, and workbench handoff.

### Source roles

| Source pool | Use | Adoption gate |
|---|---|---|
| Riot Hextech public language | geometry, timing, material and state inspiration | original implementation; no protected art or logo |
| MotionSites | hero pacing, editorial composition, isolated prototype references | consumer mapping, license check, responsive/reduced-motion fallback |
| React Bits/Aceternity/Magic UI/Motion Primitives | mechanism ideas such as spotlight, tracing, reveal | reimplement only the smallest useful mechanism; no library collage |
| Uiverse | small controls and focus details | keyboard/focus and license check |
| OP.GG/Mobalytics/Blitz | game-data information hierarchy | never copy private data, branding, or unsupported claims |
| Langfuse/Honeycomb/TrainingPeaks/Strava | evidence and training narrative | body-free public projection and source attribution |
| Image2/Photoshop | abstract atmosphere and lighting plates | replaceability, compression, no required text/data |

No paid Prompt is acquired until its concrete consumer, license, fallback, and
removal path are recorded in the asset ledger.

## 4. TDD implementation sequence

### Task 1: Freeze the presentation state contract

**Files:**

- Create: `web/src/awakening/model.ts`
- Test: `web/src/awakening/model.test.ts`

Write red tests for the allowlisted states, transition legality, and the rule
that presentation state cannot mutate profile/product truth. Implement the
smallest discriminated union and transition function, then run:

```powershell
cd D:\riftcoach-agent\web
npm test -- --run src/awakening/model.test.ts
```

### Task 2: Build the semantic scene shell

**Files:**

- Create: `web/src/components/AwakeningScene.tsx`
- Create: `web/src/components/IdentityCalibration.tsx`
- Create: `web/src/styles/awakening.css`
- Test: `web/src/components/AwakeningScene.test.tsx`

Cover landmark/heading/form names, explicit relationship status, keyboard
focus, error text, and no fake success. Keep the first implementation CSS/SVG
only and render an explicit preview disclosure when fixture data is used.

### Task 3: Add layered atmosphere and route choreography

**Files:**

- Modify: `web/src/components/RiftAtmosphere.tsx`
- Modify: `web/src/styles/tokens.css`
- Modify: `web/src/styles/awakening.css`
- Test: `web/tests/e2e/awakening.spec.ts`

Add contour/route layers, focus state, and the 700–1200ms handoff. Use the
existing Motion package only for state transitions; ambient effects must be
disabled or frozen under reduced motion. Assert no remote image or font fetch.

### Task 4: Connect the scene to the existing live/fixture boundary

**Files:**

- Modify: `web/src/app/App.tsx`
- Modify: `web/src/workbench/adapters.ts`
- Test: `web/src/app/App.test.tsx`

Use an explicit preview query/surface selector. Profile selection, observed
training restrictions, product-state banners, and live decoder errors must
remain owned by existing adapters. The scene may start or hand off a view;
it may not parse wire data or invent a run.

### Task 5: Visual and accessibility gates

**Files:**

- Modify: `web/tests/e2e/awakening.spec.ts`
- Create: `docs/assets/8e-portal-workbench/` screenshots after human review

Run typecheck, unit tests, production build, Playwright at 1440/1024/390/320,
keyboard/focus, reduced motion, axe critical/serious, and no-horizontal-overflow
checks. Keep JS gzip below 150 kB and CSS/SVG as the default asset path.

### Task 6: Source/asset exit review

**Files:**

- Create: `docs/plans/2026-08-24-8e-visual-asset-adoption-ledger.md`
- Modify: `docs/learning/8e-portal-workbench-visual-contract-walkthrough.md`

Record every adopted mechanism or asset with source URL, license/evidence,
consumer, fallback, bundle/performance cost, accessibility behavior, and
removal path. A concept image alone cannot satisfy this task.

## 5. Verification and limits

- Unit tests prove state transitions and presentation/data separation.
- Browser tests prove the real DOM, interaction, responsive layout, reduced
  motion, focus management, and no remote I/O.
- Existing backend and live integration tests remain the authority for data and
  product-state truth.
- This plan does not implement Auth/RSO, HTTPS, deployment, backup/restore,
  full Timeline DTOs, complete Training mutation flows, OP.GG useful breadth,
  or the 8F README/portfolio pass.


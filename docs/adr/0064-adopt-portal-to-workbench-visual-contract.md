# ADR-0064: Adopt the Portal-to-Workbench Visual Contract

## Status

Accepted for 8E visual preflight; implementation is the next bounded front-end
slice. This decision does not close `8e-productization` and does not authorize
production Auth, RSO, deployment, or external data expansion.

The original placement of identity calibration inside the cinematic entry is
superseded by ADR-0067 and RQ-105. The visual language and progressive-
enhancement rules below remain accepted.

RQ-106 further clarifies that the approved mother image is the composition
target, not permission to keep polishing the earlier aperture/instrumentarium
plates. A flattened keyframe may document direction, while a shipped bitmap
must remove text, UI, and the central core so DOM/React owns the only real
control and handoff.

## Context

The fixture-backed `Rift Command Center` proves that the current React surface
can present owner-scoped product states, evidence boundaries, and relationship-
safe training summaries. It is a construction slice, not the final visual
identity. The earlier Prompt/asset shortlist was too close to generic dark
dashboard references and did not make the approved three-direction combination
executable.

The user has now confirmed the combined direction:

```text
Rift Awakening / Cinematic Portal → Esports Intelligence / Broadcast Workbench
```

`Void Holographic Lab` remains a constrained Hero experiment. `Hextech
Tactical Editorial` is the shared language. Image2/Photoshop may provide
preview and layered visual assets, but a generated bitmap must not become the
source of product truth, readable UI text, or interaction semantics.

## Decision

Adopt a layered portal-to-workbench visual contract:

1. The entry surface uses an abstract Rift environment and a central Hextech
   core. Identity controls live on the separate account-access surface defined
   by ADR-0067; they are no longer composed inside the cinematic entry.
2. The workbench reuses the same geometry, material, color, and state language
   but gives more visual budget to readable analysis, evidence, and training
   structure than to atmosphere.
3. Square, diamond, and circle remain semantic shapes for structure, progress,
   and focus. Cyan/teal expresses structure, coach-gold expresses verified
   coaching emphasis, violet is provenance metadata, and red is a risk state.
4. CSS/SVG and DOM remain the default rendering path. One React motion layer
   may orchestrate state transitions. Full-screen video, Three/Spline, a second
   animation engine, or a persistent particle field require a separate Bad Case,
   performance measurement, mobile fallback, reduced-motion behavior, and
   license review before adoption.
5. Image2/Photoshop outputs are preview or layered atmosphere assets only. They
   must contain no required readable copy, logos, champion portraits, or fake
   data. Real text, data, and status always come from typed React contracts.

## Alternatives considered

### Generic dark analytics dashboard

Rejected. It satisfies basic legibility but loses the product's Rift/LoL
identity and the user's explicit requirement for a memorable, fashionable,
interactive surface.

### Full cinematic game-like shell

Rejected as the default. It risks copying protected game art, hiding real
controls, harming mobile/performance, and making the evidence product look like
decoration.

### Portal → Workbench (chosen)

It provides a memorable first-use narrative while giving the analysis surface a
stable, information-dense layout. The two surfaces can share tokens and a small
set of motion primitives without forcing every screen to be cinematic.

## Consequences

Positive consequences:

- one memorable product story connects identity selection to coaching;
- generated art has a bounded, replaceable role;
- the real API/relationship/product-state contracts remain authoritative;
- motion and visual complexity can be tested as progressive enhancement;
- later Timeline and Training work have an explicit visual home.

Costs and limits:

- the entry needs an additional UI layer and responsive choreography;
- visual QA becomes a first-class gate, not a final screenshot step;
- paid Prompt acquisition is deferred until a source is mapped to a concrete
  consumer and passes license/performance/exit-cost gates;
- the concept image itself is not evidence that the page is implemented.
- the current `portal-background-v2` is a replaceable V1 atmosphere layer;
  `portal-motion-keyframe-v2` is design evidence only, the old aperture is
  fallback-only, and the old instrumentarium no longer ships at runtime.

## Exit criteria for the next implementation slice

- an isolated entry preview renders without remote I/O or fake success;
- a typed state machine covers idle, editing, calibrating, ready, degraded,
  rejected, and reduced-motion presentation;
- the handoff to the existing workbench keeps profile/relationship and product
  state semantics unchanged;
- desktop, tablet, mobile, keyboard/focus, reduced-motion, and no-horizontal-
  overflow evidence exists;
- JavaScript gzip remains below the existing 150 kB budget and no second
  animation engine is introduced;
- the asset/source ledger records origin, license status, consumer, fallback,
  and removal path for every adopted visual mechanism.

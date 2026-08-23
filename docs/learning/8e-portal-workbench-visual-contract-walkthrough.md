# 8E Portal → Workbench Visual Contract Walkthrough

## What this decision solves

The product has a real owner/profile/product-state contract and a working
fixture/live workbench, but a concept image is not a product interface. This
walkthrough records how RiftCoach can gain a memorable visual identity without
letting images, Prompt templates, or animations invent product facts.

## Beginner mental model

Think of the interface as two layers:

```text
truth layer: typed profile, relationship, task, report, evidence, training
presentation layer: layout, materials, routes, focus, transitions, atmosphere
```

The presentation layer can make a transition feel like a Rift route igniting,
but it cannot decide that an account is verified, a report is published, or a
training plan is complete.

## Chosen direction

`Rift Awakening / Cinematic Portal → Esports Intelligence / Broadcast
Workbench` is the chosen combination. `Void Holographic Lab` remains a limited
Hero experiment. `Hextech Tactical Editorial` is the shared language: abstract
geometry, directional energy, cold metal/glass/crystal materials, editorial
asymmetry, and explicit state labels.

## Asset responsibilities

- Image2: moodboards and abstract Rift atmosphere.
- Photoshop: cleanup, compositing, color grade, masks, and export variants.
- CSS/SVG: responsive geometry, routes, markers, focus rings, and state shapes.
- React: real copy, forms, data, relationship restrictions, and handoff.

The generated mother image is therefore a visual reference and possible source
for replaceable background plates. Its tiny generated dashboard text is not
usable product evidence.

## Current implementation evidence

The first bounded slice now includes:

- `web/src/awakening/model.ts`: a typed presentation-only state machine;
- `web/src/components/AwakeningScene.tsx`: semantic Riot ID, routing-region and
  self/observed calibration form;
- `web/src/styles/awakening.css`: self-authored route, core and responsive
  atmosphere layers plus one compressed, replaceable WebP plate;
- `?surface=awakening`: an isolated preview that performs no API/Auth lookup
  and stops honestly at `calibrating`.

The preview is not the completed product entrance. It proves that the visual
story can be implemented with DOM/CSS/SVG and existing Motion boundaries before
we introduce more replaceable Image2/Photoshop plates or real account wiring.

## Evidence and interview wording

Accurate wording:

> I adopted a layered portal-to-workbench visual contract. Generated art is
> replaceable atmosphere; typed React contracts remain authoritative for
> identity, product state, evidence, and training. CSS/SVG handle responsive
> geometry, while one motion layer orchestrates state transitions with a
> reduced-motion fallback.

Do not claim that the concept image is a finished interface, that Image2
generated production data visualizations, or that the 8E productization group
is complete.

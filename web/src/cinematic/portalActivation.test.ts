import { describe, expect, it } from "vitest"

import {
  PORTAL_ACTIVATION_FULL_MOTION_MS,
  cancelPortalActivation,
  commitPortalActivation,
  createPortalActivationState,
  isPortalActivationActive,
  reducePortalActivation,
  shouldUseImmediatePortalActivation,
  startPortalActivation,
} from "./portalActivation"

describe("portal activation state machine", () => {
  it("starts idle with a zero generation and a bounded full-motion duration", () => {
    expect(createPortalActivationState()).toEqual({ phase: "idle", generation: 0 })
    expect(PORTAL_ACTIVATION_FULL_MOTION_MS).toBeGreaterThanOrEqual(600)
    expect(PORTAL_ACTIVATION_FULL_MOTION_MS).toBeLessThanOrEqual(720)
  })

  it("uses the short no-spatial-feedback path for reduced motion or Save-Data", () => {
    expect(shouldUseImmediatePortalActivation(true, false)).toBe(true)
    expect(shouldUseImmediatePortalActivation(false, true)).toBe(true)
    expect(shouldUseImmediatePortalActivation(false, false)).toBe(false)
  })

  it("starts exactly one activating generation", () => {
    const idle = createPortalActivationState()
    const activating = startPortalActivation(idle)

    expect(activating).toEqual({ phase: "activating", generation: 1 })
    expect(startPortalActivation(activating)).toBe(activating)
  })

  it("commits only the current generation", () => {
    const activating = startPortalActivation(createPortalActivationState())

    expect(commitPortalActivation(activating, activating.generation - 1)).toBe(activating)
    expect(commitPortalActivation(activating, activating.generation)).toEqual({
      phase: "committed",
      generation: activating.generation,
    })
  })

  it("cancels and invalidates a current activation", () => {
    const activating = startPortalActivation(createPortalActivationState())
    const cancelled = cancelPortalActivation(activating, activating.generation)

    expect(cancelled).toEqual({ phase: "idle", generation: 2 })
    expect(isPortalActivationActive(cancelled)).toBe(false)
    expect(cancelPortalActivation(cancelled, activating.generation)).toBe(cancelled)
  })

  it("makes reducer events idempotent and stale callbacks no-op", () => {
    const idle = createPortalActivationState()
    const activating = reducePortalActivation(idle, { type: "activate" })
    const committed = reducePortalActivation(activating, {
      type: "commit",
      generation: activating.generation,
    })

    expect(reducePortalActivation(activating, { type: "activate" })).toBe(activating)
    expect(reducePortalActivation(activating, {
      type: "commit",
      generation: activating.generation - 1,
    })).toBe(activating)
    expect(committed).toEqual({ phase: "committed", generation: 1 })
    expect(reducePortalActivation(committed, {
      type: "commit",
      generation: committed.generation,
    })).toBe(committed)
  })
})

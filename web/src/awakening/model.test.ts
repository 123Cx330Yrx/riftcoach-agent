import { describe, expect, it } from "vitest"

import {
  createAwakeningState,
  transitionAwakeningState,
  type AwakeningEvent,
} from "./model"

describe("Awakening presentation state", () => {
  it("starts idle with full motion", () => {
    expect(createAwakeningState()).toEqual({ phase: "idle", motion: "full" })
  })

  it.each([
    ["begin_editing", { phase: "idle", motion: "full" }, "editing"],
    ["begin_calibration", { phase: "editing", motion: "full" }, "calibrating"],
    ["calibration_ready", { phase: "calibrating", motion: "full" }, "ready"],
    ["calibration_degraded", { phase: "calibrating", motion: "full" }, "degraded"],
    ["calibration_rejected", { phase: "calibrating", motion: "full" }, "rejected"],
    ["client_error", { phase: "calibrating", motion: "full" }, "client-error"],
  ] as const)("transitions with %s", (event, state, expectedPhase) => {
    const next = transitionAwakeningState(
      state,
      event as AwakeningEvent,
    )

    expect(next.phase).toBe(expectedPhase)
  })

  it("keeps the current phase when reduced motion is enabled", () => {
    const state = transitionAwakeningState(
      transitionAwakeningState(createAwakeningState(), "begin_editing"),
      "reduce_motion",
    )

    expect(state).toEqual({ phase: "editing", motion: "reduced" })
  })

  it("rejects an impossible transition instead of inventing a result", () => {
    expect(() =>
      transitionAwakeningState(createAwakeningState(), "calibration_ready"),
    ).toThrowError("invalid awakening transition")
  })
})

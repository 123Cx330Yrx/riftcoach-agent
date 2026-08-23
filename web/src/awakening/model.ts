export type AwakeningPhase =
  | "idle"
  | "editing"
  | "calibrating"
  | "ready"
  | "degraded"
  | "rejected"
  | "client-error"

export type AwakeningMotion = "full" | "reduced"

export interface AwakeningPresentationState {
  readonly phase: AwakeningPhase
  readonly motion: AwakeningMotion
}

export type AwakeningEvent =
  | "begin_editing"
  | "begin_calibration"
  | "calibration_ready"
  | "calibration_degraded"
  | "calibration_rejected"
  | "client_error"
  | "reduce_motion"
  | "restore_motion"

export function createAwakeningState(): AwakeningPresentationState {
  return { phase: "idle", motion: "full" }
}

function invalidTransition(
  phase: AwakeningPhase,
  event: Exclude<AwakeningEvent, "reduce_motion" | "restore_motion">,
): never {
  throw new Error(`invalid awakening transition: ${phase} -> ${event}`)
}

export function transitionAwakeningState(
  state: AwakeningPresentationState,
  event: AwakeningEvent,
): AwakeningPresentationState {
  if (event === "reduce_motion") {
    return { ...state, motion: "reduced" }
  }

  if (event === "restore_motion") {
    return { ...state, motion: "full" }
  }

  switch (event) {
    case "begin_editing":
      if (state.phase === "idle") return { ...state, phase: "editing" }
      return invalidTransition(state.phase, event)
    case "begin_calibration":
      if (state.phase === "editing") return { ...state, phase: "calibrating" }
      return invalidTransition(state.phase, event)
    case "calibration_ready":
      if (state.phase === "calibrating") return { ...state, phase: "ready" }
      return invalidTransition(state.phase, event)
    case "calibration_degraded":
      if (state.phase === "calibrating") return { ...state, phase: "degraded" }
      return invalidTransition(state.phase, event)
    case "calibration_rejected":
      if (state.phase === "calibrating") return { ...state, phase: "rejected" }
      return invalidTransition(state.phase, event)
    case "client_error":
      if (state.phase === "calibrating") return { ...state, phase: "client-error" }
      return invalidTransition(state.phase, event)
  }
}

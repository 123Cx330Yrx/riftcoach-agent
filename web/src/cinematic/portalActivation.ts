export type PortalActivationPhase = "idle" | "activating" | "committed"

export interface PortalActivationState {
  readonly phase: PortalActivationPhase
  readonly generation: number
}

export type PortalActivationEvent =
  | { readonly type: "activate" }
  | { readonly type: "commit"; readonly generation: number }
  | { readonly type: "cancel"; readonly generation: number }

export const PORTAL_ACTIVATION_FULL_MOTION_MS = 720
export const PORTAL_ACTIVATION_OVERLAY_EXIT_MS = 360

export function shouldUseImmediatePortalActivation(
  reducedMotion: boolean,
  saveData: boolean,
): boolean {
  return reducedMotion || saveData
}

export function createPortalActivationState(): PortalActivationState {
  return { phase: "idle", generation: 0 }
}

export function startPortalActivation(
  state: PortalActivationState,
): PortalActivationState {
  if (state.phase !== "idle") return state
  return { phase: "activating", generation: state.generation + 1 }
}

export function commitPortalActivation(
  state: PortalActivationState,
  generation: number,
): PortalActivationState {
  if (state.phase !== "activating" || state.generation !== generation) return state
  return { phase: "committed", generation }
}

export function cancelPortalActivation(
  state: PortalActivationState,
  generation: number,
): PortalActivationState {
  if (state.phase === "idle" || state.generation !== generation) return state
  return { phase: "idle", generation: state.generation + 1 }
}

export function isPortalActivationActive(state: PortalActivationState): boolean {
  return state.phase !== "idle"
}

export function reducePortalActivation(
  state: PortalActivationState,
  event: PortalActivationEvent,
): PortalActivationState {
  switch (event.type) {
    case "activate":
      return startPortalActivation(state)
    case "commit":
      return commitPortalActivation(state, event.generation)
    case "cancel":
      return cancelPortalActivation(state, event.generation)
  }
}

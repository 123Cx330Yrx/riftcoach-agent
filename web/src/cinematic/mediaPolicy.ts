import type { CinematicViewport } from "./mediaManifest"

export type { CinematicViewport } from "./mediaManifest"

export const CINEMATIC_MOBILE_MAX_WIDTH_PX = 760
export const CINEMATIC_MOBILE_MEDIA_QUERY = `(max-width: ${CINEMATIC_MOBILE_MAX_WIDTH_PX}px)`
export const CINEMATIC_REDUCED_MOTION_MEDIA_QUERY = "(prefers-reduced-motion: reduce)"

export type CinematicMediaPolicy =
  | {
      readonly mode: "motion"
      readonly viewport: CinematicViewport
    }
  | {
      readonly mode: "poster"
      readonly viewport: CinematicViewport
      readonly reason: "preflight" | "reduced-motion" | "save-data"
    }

export interface CinematicMediaPolicySignals {
  readonly reducedMotion: boolean
  readonly saveData: boolean
  readonly viewport: CinematicViewport
}

export function resolveCinematicViewport(viewportWidth: number): CinematicViewport {
  if (!Number.isFinite(viewportWidth) || viewportWidth < 0) {
    throw new Error("viewportWidth must be a finite non-negative number")
  }
  return viewportWidth <= CINEMATIC_MOBILE_MAX_WIDTH_PX ? "mobile" : "desktop"
}

export function resolveCinematicMediaPolicy(
  signals: CinematicMediaPolicySignals,
): CinematicMediaPolicy {
  if (signals.reducedMotion) {
    return {
      mode: "poster",
      viewport: signals.viewport,
      reason: "reduced-motion",
    }
  }
  if (signals.saveData) {
    return {
      mode: "poster",
      viewport: signals.viewport,
      reason: "save-data",
    }
  }
  return { mode: "motion", viewport: signals.viewport }
}

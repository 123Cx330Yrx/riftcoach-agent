import type { PortalActivationState } from "../cinematic/portalActivation"

export interface PortalActivationOverlayProps {
  readonly state: PortalActivationState
  readonly reducedMotion: boolean
}

export function PortalActivationOverlay({
  state,
  reducedMotion,
}: PortalActivationOverlayProps) {
  if (state.phase === "idle") return null

  const committed = state.phase === "committed"
  return (
    <div
      className={`portal-activation-overlay portal-activation-overlay--${state.phase}`}
      data-testid="portal-activation-overlay"
      data-phase={state.phase}
      data-generation={state.generation}
      data-motion={reducedMotion ? "reduced" : "full"}
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 40,
        pointerEvents: "none",
        opacity: committed ? 1 : 0.82,
        background: reducedMotion
          ? "rgba(3, 9, 13, 0.16)"
          : "radial-gradient(circle at 50% 50%, rgba(236, 217, 140, 0.34), rgba(3, 9, 13, 0.08) 24%, rgba(3, 9, 13, 0.54) 100%)",
        transition: reducedMotion ? "opacity 120ms ease-out" : "opacity 220ms ease-out",
      }}
    >
      <span className="portal-activation-overlay__aperture" />
      <span className="portal-activation-overlay__burst" />
    </div>
  )
}

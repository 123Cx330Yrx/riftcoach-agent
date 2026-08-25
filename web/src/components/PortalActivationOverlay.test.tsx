import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { PortalActivationOverlay } from "./PortalActivationOverlay"

describe("PortalActivationOverlay", () => {
  it("renders nothing while the portal is idle", () => {
    const { container } = render(
      <PortalActivationOverlay state={{ phase: "idle", generation: 0 }} reducedMotion={false} />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it("keeps an activating overlay outside the portal content and exposes no extra control", () => {
    render(
      <PortalActivationOverlay
        state={{ phase: "activating", generation: 2 }}
        reducedMotion={false}
      />,
    )

    const overlay = screen.getByTestId("portal-activation-overlay")
    expect(overlay).toHaveAttribute("data-phase", "activating")
    expect(overlay).toHaveAttribute("data-generation", "2")
    expect(overlay).toHaveAttribute("aria-hidden", "true")
    expect(overlay).toHaveStyle({ pointerEvents: "none" })
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })

  it("marks a reduced-motion commit without introducing spatial animation controls", () => {
    render(
      <PortalActivationOverlay
        state={{ phase: "committed", generation: 3 }}
        reducedMotion
      />,
    )

    const overlay = screen.getByTestId("portal-activation-overlay")
    expect(overlay).toHaveAttribute("data-phase", "committed")
    expect(overlay).toHaveAttribute("data-motion", "reduced")
    expect(overlay).toHaveAttribute("aria-hidden", "true")
  })
})

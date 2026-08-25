import { fireEvent, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { AwakeningScene } from "./AwakeningScene"
import { createAwakeningState, transitionAwakeningState } from "../awakening/model"
import { renderWithLocale as render } from "../test/renderWithLocale"

describe("AwakeningScene", () => {
  it("emits one activation intent and keeps the semantic core latched", () => {
    const onActivate = vi.fn()
    const view = render(
      <AwakeningScene
        state={createAwakeningState()}
        onEnter={vi.fn()}
        onActivate={onActivate}
      />,
    )

    const core = screen.getByRole("button", { name: /enter riftcoach/i })
    expect(core).not.toHaveAttribute("aria-disabled")
    fireEvent.click(core)
    expect(onActivate).toHaveBeenCalledOnce()

    const activating = { phase: "activating", generation: 1 } as const
    view.rerender(
      <AwakeningScene
        state={createAwakeningState()}
        activationState={activating}
        onEnter={vi.fn()}
        onActivate={onActivate}
      />,
    )
    const latchedCore = screen.getByRole("button", { name: /enter riftcoach/i })
    expect(screen.getByTestId("awakening-scene")).toHaveAttribute("data-activation", "activating")
    expect(latchedCore).toHaveAttribute("aria-disabled", "true")
    fireEvent.click(latchedCore)
    expect(onActivate).toHaveBeenCalledOnce()
  })

  it("renders a cinematic portal without mounting account fields", () => {
    render(
      <AwakeningScene
        state={createAwakeningState()}
        disclosure="Preview only · no external lookup"
        onEnter={vi.fn()}
      />,
    )

    expect(screen.getByRole("heading", { name: /read the rift/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /enter riftcoach/i })).toBeInTheDocument()
    expect(screen.queryByLabelText(/riot id/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/^region$/i)).not.toBeInTheDocument()
    expect(screen.getByText(/preview only/i)).toBeInTheDocument()
  })

  it("activates the central core by keyboard while preserving reduced-motion state", async () => {
    const user = userEvent.setup()
    const onActivate = vi.fn()
    const editingReduced = transitionAwakeningState(
      transitionAwakeningState(createAwakeningState(), "begin_editing"),
      "reduce_motion",
    )

    const view = render(
      <AwakeningScene
        state={editingReduced}
        disclosure="Preview only"
        onEnter={vi.fn()}
        activationState={{ phase: "idle", generation: 0 }}
        onActivate={onActivate}
      />,
    )

    const scene = screen.getByTestId("awakening-scene")
    expect(scene).toHaveAttribute("data-phase", "editing")
    expect(scene).toHaveAttribute("data-motion", "reduced")
    const core = screen.getByRole("button", { name: /enter riftcoach/i })
    await user.tab()
    await user.tab()
    await user.tab()
    expect(core).toHaveFocus()
    await user.keyboard("{Enter}")
    view.rerender(
      <AwakeningScene
        state={editingReduced}
        disclosure="Preview only"
        onEnter={vi.fn()}
        activationState={{ phase: "activating", generation: 1 }}
        onActivate={onActivate}
      />,
    )
    await user.keyboard(" ")
    expect(onActivate).toHaveBeenCalledOnce()
  })
})

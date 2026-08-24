import { fireEvent, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { AwakeningScene } from "./AwakeningScene"
import { createAwakeningState, transitionAwakeningState } from "../awakening/model"
import { renderWithLocale as render } from "../test/renderWithLocale"

describe("AwakeningScene", () => {
  it("plays one bounded handoff before entering in full-motion mode", () => {
    vi.useFakeTimers()
    const onEnter = vi.fn()
    render(
      <AwakeningScene
        state={createAwakeningState()}
        onEnter={onEnter}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: /enter riftcoach/i }))
    expect(screen.getByTestId("awakening-scene")).toHaveClass("awakening-scene--departing")
    expect(onEnter).not.toHaveBeenCalled()
    vi.advanceTimersByTime(720)
    expect(onEnter).toHaveBeenCalledOnce()
    vi.useRealTimers()
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
    const onEnter = vi.fn()
    const editingReduced = transitionAwakeningState(
      transitionAwakeningState(createAwakeningState(), "begin_editing"),
      "reduce_motion",
    )

    render(
      <AwakeningScene
        state={editingReduced}
        disclosure="Preview only"
        onEnter={onEnter}
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
    await user.keyboard(" ")
    expect(onEnter).toHaveBeenCalledOnce()
  })
})

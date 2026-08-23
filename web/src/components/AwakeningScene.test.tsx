import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { AwakeningScene } from "./AwakeningScene"
import { createAwakeningState, transitionAwakeningState } from "../awakening/model"

describe("AwakeningScene", () => {
  it("renders an honest identity calibration form", () => {
    render(
      <AwakeningScene
        state={createAwakeningState()}
        disclosure="Preview only · no external lookup"
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByRole("heading", { name: /calibrate your analysis field/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/riot id/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/routing region/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/relationship/i)).toBeInTheDocument()
    expect(screen.getByText(/preview only/i)).toBeInTheDocument()
    expect(screen.queryByText(/verified本人|verified self/i)).not.toBeInTheDocument()
  })

  it("exposes phase and reduced-motion state without changing form semantics", () => {
    const editingReduced = transitionAwakeningState(
      transitionAwakeningState(createAwakeningState(), "begin_editing"),
      "reduce_motion",
    )

    render(
      <AwakeningScene
        state={editingReduced}
        disclosure="Preview only"
        onSubmit={vi.fn()}
      />,
    )

    const scene = screen.getByTestId("awakening-scene")
    expect(scene).toHaveAttribute("data-phase", "editing")
    expect(scene).toHaveAttribute("data-motion", "reduced")
    expect(screen.getByRole("button", { name: /calibrate identity/i })).toBeEnabled()
  })

  it("announces client errors without rewriting them as product rejection", () => {
    const state = transitionAwakeningState(
      transitionAwakeningState(createAwakeningState(), "begin_editing"),
      "begin_calibration",
    )
    const errorState = transitionAwakeningState(state, "client_error")

    render(
      <AwakeningScene
        state={errorState}
        disclosure="Preview only"
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByRole("alert")).toHaveTextContent(/browser could not continue/i)
    expect(screen.queryByText(/publication rejected/i)).not.toBeInTheDocument()
  })

  it("offers an explicit workbench handoff only after a ready projection", () => {
    const calibrating = transitionAwakeningState(
      transitionAwakeningState(createAwakeningState(), "begin_editing"),
      "begin_calibration",
    )
    const ready = transitionAwakeningState(calibrating, "calibration_ready")
    const onHandoff = vi.fn()

    render(
      <AwakeningScene
        state={ready}
        disclosure="Preview only"
        onSubmit={vi.fn()}
        onHandoff={onHandoff}
      />,
    )

    const handoff = screen.getByRole("button", { name: /enter broadcast workbench/i })
    fireEvent.click(handoff)
    expect(onHandoff).toHaveBeenCalledTimes(1)
  })
})

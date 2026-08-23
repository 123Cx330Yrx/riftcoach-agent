import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { App } from "../app/App"

describe("workbench state matrix", () => {
  it("keeps client loading separate from a published product state", () => {
    render(<App scenarioOverride="loading" />)

    expect(screen.getByRole("status")).toHaveTextContent(/calibrating the rift/i)
    expect(screen.queryByText(/^published$/i)).not.toBeInTheDocument()
  })

  it("distinguishes empty from client error", () => {
    const { unmount } = render(<App scenarioOverride="empty" />)
    expect(screen.getByRole("heading", { name: /no player profiles yet/i })).toBeInTheDocument()
    expect(screen.queryByText(/workbench unavailable/i)).not.toBeInTheDocument()

    unmount()
    render(<App scenarioOverride="error" />)
    expect(screen.getByRole("heading", { name: /workbench unavailable/i })).toBeInTheDocument()
    expect(screen.getByText(/fixture_load_failed/i)).toBeInTheDocument()
  })

  it("shows lifecycle truth without inventing progress percentages", () => {
    render(<App scenarioOverride="not_ready" />)

    expect(screen.getByText(/^not ready$/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /analysis in progress/i })).toBeInTheDocument()
    expect(screen.getByText(/task_pending/i)).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/\d+%/)
  })

  it("keeps a degraded brief visible with explicit evidence limitations", () => {
    render(<App scenarioOverride="degraded" />)

    expect(screen.getByText(/^degraded$/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /tactical brief/i })).toBeInTheDocument()
    expect(screen.getByText(/evidence limitations/i)).toBeInTheDocument()
    expect(screen.getByText(/evidence_expired/i)).toBeInTheDocument()
  })

  it("withholds a rejected report instead of rendering unsafe content", () => {
    render(<App scenarioOverride="rejected" />)

    expect(screen.getByText(/^rejected$/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /review withheld/i })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /tactical brief/i })).not.toBeInTheDocument()
  })

  it("turns personal training into a read-only learning observation for observed players", async () => {
    const user = userEvent.setup()
    render(<App scenarioOverride="published" />)

    expect(screen.getByRole("heading", { name: /your training plan/i })).toBeInTheDocument()
    await user.selectOptions(
      screen.getByRole("combobox", { name: /player profile/i }),
      "profile-northstar-kr",
    )

    expect(screen.getByRole("heading", { name: "Northstar#KR" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /learning observation/i })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /your training plan/i })).not.toBeInTheDocument()
  })
})

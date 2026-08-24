import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { App } from "../app/App"

describe("workbench state matrix", () => {
  it("keeps client loading separate from a published product state", () => {
    render(<App scenarioOverride="loading" />)

    expect(screen.getByRole("status")).toHaveTextContent(/preparing the review/i)
    expect(screen.queryByText(/^published$/i)).not.toBeInTheDocument()
  })

  it("distinguishes empty from client error", () => {
    const { unmount } = render(<App scenarioOverride="empty" />)
    expect(screen.getByRole("heading", { name: /no player profiles yet/i })).toBeInTheDocument()
    expect(screen.queryByText(/workbench is unavailable/i)).not.toBeInTheDocument()

    unmount()
    render(<App scenarioOverride="error" />)
    expect(screen.getByRole("heading", { name: /workbench is unavailable/i })).toBeInTheDocument()
    expect(screen.getByText(/demo couldn't be loaded/i)).toBeInTheDocument()
    expect(screen.queryByText(/fixture_load_failed/i)).not.toBeInTheDocument()
  })

  it("shows lifecycle truth without inventing progress percentages", () => {
    render(<App scenarioOverride="not_ready" />)

    expect(screen.getByText(/^in progress$/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /review is still running/i })).toBeInTheDocument()
    expect(screen.queryByText(/task_pending/i)).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/\d+%/)
  })

  it("keeps a degraded brief visible with explicit evidence limitations", () => {
    render(<App scenarioOverride="degraded" />)

    expect(screen.getByText(/^degraded$/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /tactical brief/i })).toBeInTheDocument()
    expect(screen.getByText(/some evidence is missing/i)).toBeInTheDocument()
    expect(screen.queryByText(/evidence_expired/i)).not.toBeInTheDocument()
  })

  it("withholds a rejected report instead of rendering unsafe content", () => {
    render(<App scenarioOverride="rejected" />)

    expect(screen.getByText(/^not published$/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /no coaching brief/i })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /tactical brief/i })).not.toBeInTheDocument()
  })

  it("turns personal training into a read-only learning observation for observed players", async () => {
    const user = userEvent.setup()
    render(<App scenarioOverride="published" />)

    expect(screen.getByRole("heading", { name: /^training plan$/i })).toBeInTheDocument()
    await user.selectOptions(
      screen.getByRole("combobox", { name: /player profile/i }),
      "profile-northstar-kr",
    )

    expect(screen.getByRole("heading", { name: "Northstar#KR" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /study notes/i })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /^training plan$/i })).not.toBeInTheDocument()
  })
})

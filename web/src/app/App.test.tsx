import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { App } from "./App"

describe("Rift Command Center shell", () => {
  it("exposes a semantic, fixture-disclosed workbench", () => {
    render(<App scenarioOverride="published" />)

    expect(screen.getByRole("link", { name: /skip to review workspace/i })).toHaveAttribute(
      "href",
      "#review-workspace",
    )
    expect(screen.getByRole("banner")).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: /command sections/i })).toBeInTheDocument()
    expect(screen.getByRole("main")).toHaveAttribute("id", "review-workspace")
    expect(screen.getByRole("complementary", { name: /review context/i })).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { level: 1, name: /rift command center/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/fixture preview/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Riverline#EUW" })).toBeInTheDocument()
    expect(screen.getByText(/europe routing/i)).toBeInTheDocument()

    const atmosphere = screen.getByTestId("rift-atmosphere")
    expect(atmosphere).toHaveAttribute("aria-hidden", "true")
  })

  it("fails closed for an unknown fixture scenario", () => {
    render(<App scenarioOverride="not-a-real-scenario" />)

    expect(screen.getByRole("heading", { name: /workbench unavailable/i })).toBeInTheDocument()
    expect(screen.getByText(/fixture_scenario_unknown/i)).toBeInTheDocument()
    expect(screen.queryByText(/^published$/i)).not.toBeInTheDocument()
  })
})

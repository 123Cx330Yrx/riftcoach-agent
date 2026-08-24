import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { App } from "../app/App"

describe("Evidence Drawer", () => {
  it("is keyboard operable, restores focus and exposes only safe evidence", async () => {
    const user = userEvent.setup()
    render(<App scenarioOverride="published" />)

    const trigger = screen.getByRole("button", { name: /open evidence/i })
    trigger.focus()
    await user.keyboard("{Enter}")

    const dialog = screen.getByRole("dialog", { name: /review evidence/i })
    expect(dialog).toBeInTheDocument()
    expect(screen.getByText(/riot match api/i)).toBeInTheDocument()
    expect(screen.getByText(/op\.gg meta/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /review log/i })).toBeInTheDocument()
    expect(within(dialog).getAllByText("completed", { exact: true }).length).toBeGreaterThan(0)
    expect(screen.getByText(/integrity check/i)).toBeInTheDocument()

    const text = dialog.textContent?.toLowerCase() ?? ""
    for (const forbidden of [
      "owner_id",
      "puuid",
      "raw_response",
      "lease_token",
      "chain-of-thought",
      "refresh_id",
      "event_cursor",
      "tool_arguments",
    ]) {
      expect(text).not.toContain(forbidden)
    }

    await user.keyboard("{Escape}")
    expect(screen.queryByRole("dialog", { name: /review evidence/i })).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it("localizes an unknown evidence gap without exposing its internal code", async () => {
    const user = userEvent.setup()
    render(<App scenarioOverride="degraded" />)

    await user.click(screen.getByRole("button", { name: /open evidence/i }))
    const dialog = screen.getByRole("dialog", { name: /review evidence/i })

    expect(within(dialog).getByText(/evidence limit/i)).toBeInTheDocument()
    expect(within(dialog).queryByText("meta_join_unavailable", { exact: true })).not.toBeInTheDocument()
  })
})

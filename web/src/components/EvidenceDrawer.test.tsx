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

    const dialog = screen.getByRole("dialog", { name: /evidence ledger/i })
    expect(dialog).toBeInTheDocument()
    expect(screen.getByText(/riot match api/i)).toBeInTheDocument()
    expect(screen.getByText(/op\.gg meta/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /safe run path/i })).toBeInTheDocument()
    expect(within(dialog).getByText("task completed", { exact: true })).toBeInTheDocument()
    expect(screen.getByText(/bundle digest/i)).toBeInTheDocument()

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
    expect(screen.queryByRole("dialog", { name: /evidence ledger/i })).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
})

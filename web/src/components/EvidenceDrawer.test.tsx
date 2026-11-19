import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { App } from "../app/App"
import { ProductLocaleProvider } from "../i18n/ProductLocaleProvider"
import type { WorkbenchEvidence } from "../workbench/model"
import { EvidenceDrawer } from "./EvidenceDrawer"

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

  it("preserves repeated match gaps and champion joins across evidence updates", async () => {
    const user = userEvent.setup()
    const errors = vi.spyOn(console, "error").mockImplementation(() => {})
    const gapCodes = ["data_dragon_missing", "official_patch_missing", "meta_join_missing"]
    const evidence: WorkbenchEvidence = {
      revision: 1,
      bundleDigest: "a".repeat(64),
      snapshotDigest: "b".repeat(64),
      freshness: "current",
      disposition: "degraded",
      confidence: "medium",
      claims: [],
      sources: [],
      joins: Array.from({ length: 5 }, () => ({
        labelCode: "champion_position",
        championName: "Swain",
        position: "mid",
        status: "unjoined",
        sourcesPresent: ["riot_official"],
      })),
      gaps: Array.from({ length: 5 }, () => gapCodes.map((code) => ({ code }))).flat(),
    }
    const drawer = (value: WorkbenchEvidence) => (
      <ProductLocaleProvider navigatorLanguages={["en"]}>
        <EvidenceDrawer evidence={value} events={[]} run={undefined} />
      </ProductLocaleProvider>
    )
    try {
      const { rerender } = render(drawer(evidence))
      await user.click(screen.getByRole("button", { name: /open evidence/i }))
      const gaps = screen.getByRole("region", { name: "Missing pieces" })
      const joins = screen.getByRole("region", { name: "Matched data" })
      expect(within(gaps).getAllByRole("article")).toHaveLength(15)
      expect(within(joins).getAllByRole("article")).toHaveLength(5)

      rerender(drawer({ ...evidence, revision: 2, gaps: evidence.gaps.slice(0, 3), joins: evidence.joins.slice(0, 2) }))
      expect(within(gaps).getAllByRole("article")).toHaveLength(3)
      expect(within(joins).getAllByRole("article")).toHaveLength(2)
      expect(errors).not.toHaveBeenCalled()
    } finally {
      errors.mockRestore()
    }
  })
})

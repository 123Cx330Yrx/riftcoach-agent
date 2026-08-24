import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import type { PlayerAccessApi } from "../api/playerLinkApi"
import { ApiClientError } from "../api/client"
import { renderWithLocale as render } from "../test/renderWithLocale"
import { AccountAccess } from "./AccountAccess"

const PROFILE = "95000000-0000-4000-8000-000000000001"

function api(): PlayerAccessApi {
  return {
    listProfiles: vi.fn(async () => ({
      schema_version: "1.0" as const,
      limit: 50,
      profiles: [{
        schema_version: "1.0" as const,
        player_profile_id: PROFILE,
        riot_id: "Riverline#EUW",
        routing_region: "europe" as const,
        relationship_role: "self" as const,
        verification_status: "unverified_claim" as const,
        last_resolved_at: "2026-08-24T02:00:00Z",
      }],
    })),
    createLink: vi.fn(),
    getLink: vi.fn(),
  }
}

describe("AccountAccess", () => {
  it("selects an existing player before entering the workbench", async () => {
    const user = userEvent.setup()
    const onContinue = vi.fn()
    render(
      <AccountAccess
        api={api()}
        csrfToken="csrf"
        onBack={vi.fn()}
        onContinue={onContinue}
      />,
    )

    expect(await screen.findByRole("heading", { name: /who are we reviewing/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /who are we reviewing/i })).toHaveFocus()
    expect(screen.getByText("Riverline#EUW")).toBeInTheDocument()
    expect(screen.getByText("Europe")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /open this review/i }))
    expect(onContinue).toHaveBeenCalledWith(PROFILE)
  })

  it("uses natural Chinese region and account copy instead of exposing wire codes", async () => {
    const user = userEvent.setup()
    render(
      <AccountAccess
        api={api()}
        csrfToken="csrf"
        onBack={vi.fn()}
        onContinue={vi.fn()}
      />,
    )

    await screen.findByText("Riverline#EUW")
    await user.click(screen.getByRole("button", { name: "中文" }))
    expect(screen.getByRole("heading", { name: "这次想看谁？" })).toBeInTheDocument()
    expect(screen.getByText("欧洲")).toBeInTheDocument()
    expect(screen.queryByText("europe", { exact: true })).not.toBeInTheDocument()
    expect(screen.queryByText(/裂谷指挥中心/)).not.toBeInTheDocument()
  })

  it("propagates an expired account request back to the Auth boundary", async () => {
    const onAuthFailure = vi.fn()
    const expiredApi = api()
    expiredApi.listProfiles = vi.fn(async () => {
      throw new ApiClientError("auth_session_expired", 401)
    })

    render(
      <AccountAccess
        api={expiredApi}
        csrfToken="csrf"
        onBack={vi.fn()}
        onContinue={vi.fn()}
        onAuthFailure={onAuthFailure}
      />,
    )

    await screen.findByRole("heading", { name: /players couldn't be loaded/i })
    expect(onAuthFailure).toHaveBeenCalledWith("auth_session_expired")
  })
})

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { App } from "./App"
import type { LiveWorkbenchControllerLike } from "./App"
import type { PlayerAccessApi } from "../api/playerLinkApi"
import { AuthSessionError } from "../auth/session"

const PROFILE_ID = "95000000-0000-4000-8000-000000000001"

function playerAccessApi(): PlayerAccessApi {
  return {
    listProfiles: vi.fn(async () => ({
      schema_version: "1.0" as const,
      limit: 50,
      profiles: [{
        schema_version: "1.0" as const,
        player_profile_id: PROFILE_ID,
        riot_id: "LiveRiver#EUW",
        routing_region: "europe" as const,
        relationship_role: "self" as const,
        verification_status: "unverified_claim" as const,
        last_resolved_at: "2026-08-23T11:00:00Z",
      }],
    })),
    createLink: vi.fn(),
    getLink: vi.fn(),
  }
}

function authClient() {
  return {
    issue: vi.fn(async () => ({
      schema_version: "1.0" as const,
      csrf_token: "csrf-test",
      expires_at: "2026-08-24T06:00:00Z",
    })),
  }
}

describe("RiftCoach product journey", () => {
  it("starts at the isolated cinematic portal and performs no auth, profile or live work", () => {
    const createAuthSessionClient = vi.fn(authClient)
    const createPlayerAccessApi = vi.fn(playerAccessApi)
    const createLiveController = vi.fn()

    render(<App
      createAuthSessionClient={createAuthSessionClient}
      createPlayerAccessApi={createPlayerAccessApi}
      createLiveController={createLiveController}
    />)

    expect(screen.getByRole("heading", { name: /read the rift/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /enter riftcoach/i })).toBeInTheDocument()
    expect(screen.queryByLabelText(/riot id/i)).not.toBeInTheDocument()
    expect(screen.queryByRole("navigation", { name: /^sections$/i })).not.toBeInTheDocument()
    expect(createAuthSessionClient).not.toHaveBeenCalled()
    expect(createPlayerAccessApi).not.toHaveBeenCalled()
    expect(createLiveController).not.toHaveBeenCalled()
  })

  it("exposes the isolated portal preview without mounting the workbench", () => {
    render(<App surfaceOverride="awakening" />)

    expect(screen.getByTestId("awakening-scene")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /read the rift/i })).toBeInTheDocument()
    expect(screen.queryByRole("navigation", { name: /^sections$/i })).not.toBeInTheDocument()
    expect(screen.getByText(/preview only · no external lookup/i)).toBeInTheDocument()
  })

  it("switches the portal chrome to natural Chinese without adding identity fields", async () => {
    const user = userEvent.setup()
    render(<App surfaceOverride="awakening" />)

    await user.click(screen.getByRole("button", { name: "中文" }))

    expect(screen.getByRole("heading", { name: "看懂这一局，打好下一局。" })).toBeInTheDocument()
    expect(screen.queryByLabelText("Riot ID")).not.toBeInTheDocument()
    expect(screen.getByText(/仅供预览 · 不查询外部数据，也不登录/)).toBeInTheDocument()
  })

  it("exposes a semantic, fixture-disclosed workbench", () => {
    render(<App scenarioOverride="published" />)

    expect(screen.getByRole("link", { name: /skip to review workspace/i })).toHaveAttribute(
      "href",
      "#review-workspace",
    )
    expect(screen.getByRole("banner")).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: /^sections$/i })).toBeInTheDocument()
    expect(screen.getByRole("main")).toHaveAttribute("id", "review-workspace")
    expect(screen.getByRole("complementary", { name: /review context/i })).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { level: 1, name: /match review/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/^demo review$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/data mode/i)).toHaveTextContent(/demo/i)
    expect(screen.getByLabelText(/data mode/i)).toHaveTextContent(/sample data/i)
    expect(screen.getByRole("heading", { name: "Riverline#EUW" })).toBeInTheDocument()
    expect(screen.getByText(/^europe$/i)).toBeInTheDocument()
    expect(document.querySelector(".role-cluster__role")).toHaveTextContent(/^mid$/i)
    expect(screen.queryByText("MIDDLE", { exact: true })).not.toBeInTheDocument()

    const atmosphere = screen.getByTestId("rift-atmosphere")
    expect(atmosphere).toHaveAttribute("aria-hidden", "true")
  })

  it("fails closed for an unknown fixture scenario", () => {
    render(<App scenarioOverride="not-a-real-scenario" />)

    expect(screen.getByRole("heading", { name: /workbench is unavailable/i })).toBeInTheDocument()
    expect(screen.getByText(/demo couldn't be loaded/i)).toBeInTheDocument()
    expect(screen.queryByText(/fixture_scenario_unknown/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^published$/i)).not.toBeInTheDocument()
  })

  it("enters Account only after core activation and starts live work only after profile selection", async () => {
    const user = userEvent.setup()
    const controller: LiveWorkbenchControllerLike = {
      snapshot: {
        state: {
          client: "ready",
          data: {
            profiles: [{
              playerProfileId: PROFILE_ID,
              riotId: "LiveRiver#EUW",
              routingRegion: "europe",
              relationshipRole: "self",
              verificationStatus: "unverified_claim",
              lastResolvedAt: "2026-08-23T11:00:00Z",
            }],
            selectedProfileId: PROFILE_ID,
            events: [],
            training: {
              mode: "personal",
              title: "Wave-state discipline",
              objective: "Name the wave before leaving lane.",
            },
          },
        },
        liveUpdates: "closed",
      },
      subscribe: vi.fn(() => () => undefined),
      start: vi.fn(async () => undefined),
      selectProfile: vi.fn(async () => undefined),
      dispose: vi.fn(),
    }

    const createLiveController = vi.fn(() => controller)
    const createAuthSessionClient = vi.fn(authClient)
    const createPlayerAccessApi = vi.fn(playerAccessApi)
    render(
      <App
        createLiveController={createLiveController}
        createAuthSessionClient={createAuthSessionClient}
        createPlayerAccessApi={createPlayerAccessApi}
      />,
    )

    expect(controller.start).not.toHaveBeenCalled()
    await user.click(screen.getByRole("button", { name: /enter riftcoach/i }))
    expect(await screen.findByRole("heading", { name: /who are we reviewing/i })).toBeInTheDocument()
    expect(controller.start).not.toHaveBeenCalled()
    await user.click(screen.getByRole("button", { name: /open this review/i }))
    await waitFor(() => expect(controller.start).toHaveBeenCalledTimes(1))
    expect(createLiveController).toHaveBeenCalledWith(PROFILE_ID)
    expect(screen.getByRole("heading", { name: "LiveRiver#EUW" })).toBeInTheDocument()
    expect(screen.getByText(/live review/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/data mode/i)).toHaveTextContent(/live/i)
    expect(screen.getByLabelText(/data mode/i)).toHaveTextContent(/current player/i)
    expect(screen.getByLabelText(/data mode/i)).not.toHaveTextContent(/demo/i)
    expect(screen.queryByText(/demo review/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/2\s*\/\s*5/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/next session/i)).not.toBeInTheDocument()
    expect(screen.getByText("Wave-state discipline")).toBeInTheDocument()
    expect(screen.getByText("Name the wave before leaving lane.")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "中文" }))

    expect(screen.getByRole("heading", { level: 1, name: "对局复盘" })).toBeInTheDocument()
    expect(screen.getByText("Wave-state discipline")).toBeInTheDocument()
    expect(screen.getByText("Name the wave before leaving lane.")).toBeInTheDocument()
    expect(screen.getByText("保留原文")).toBeInTheDocument()
    expect(controller.start).toHaveBeenCalledTimes(1)
    expect(controller.selectProfile).not.toHaveBeenCalled()
  })

  it("responds to canonical history changes without mounting two product layers", async () => {
    const user = userEvent.setup()
    render(
      <App
        createAuthSessionClient={vi.fn(authClient)}
        createPlayerAccessApi={vi.fn(playerAccessApi)}
      />,
    )

    await user.click(screen.getByRole("button", { name: /enter riftcoach/i }))
    expect(await screen.findByRole("heading", { name: /who are we reviewing/i })).toBeInTheDocument()
    expect(screen.queryByTestId("awakening-scene")).not.toBeInTheDocument()

    window.history.replaceState(null, "", "/")
    window.dispatchEvent(new PopStateEvent("popstate"))
    expect(await screen.findByRole("heading", { name: /read the rift/i })).toBeInTheDocument()
    expect(screen.queryByTestId("account-access")).not.toBeInTheDocument()

    window.history.replaceState(null, "", "/?stage=account")
    window.dispatchEvent(new PopStateEvent("popstate"))
    expect(await screen.findByRole("heading", { name: /who are we reviewing/i })).toBeInTheDocument()
    expect(screen.queryByTestId("awakening-scene")).not.toBeInTheDocument()
  })

  it("tears down live work and returns to the auth boundary when its session expires", async () => {
    window.history.replaceState(
      null,
      "",
      `/?stage=workbench&player_profile_id=${PROFILE_ID}`,
    )
    const controller: LiveWorkbenchControllerLike = {
      snapshot: {
        state: {
          client: "error",
          code: "auth_session_expired",
          messageCode: "workbench_load_failed",
        },
        liveUpdates: "closed",
      },
      subscribe: vi.fn(() => () => undefined),
      start: vi.fn(async () => undefined),
      selectProfile: vi.fn(async () => undefined),
      dispose: vi.fn(),
    }
    const createLiveController = vi.fn(() => controller)

    render(
      <App
        createAuthSessionClient={vi.fn(authClient)}
        createLiveController={createLiveController}
      />,
    )

    expect(await screen.findByRole("heading", { name: /your session has ended/i })).toBeInTheDocument()
    expect(createLiveController).toHaveBeenCalledWith(PROFILE_ID)
    expect(screen.queryByRole("heading", { name: /match review/i })).not.toBeInTheDocument()
    await waitFor(() => expect(controller.dispose).toHaveBeenCalledTimes(1))
  })

  it("keeps original generated report bytes while translating product chrome", async () => {
    const user = userEvent.setup()
    render(<App scenarioOverride="published" />)
    const original = /Protect your farm baseline, then make every early river move/i

    expect(screen.getByText(original)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "中文" }))

    expect(screen.getByText(original)).toBeInTheDocument()
    expect(screen.getAllByText("保留原文")).toHaveLength(2)
    expect(document.querySelector(".role-cluster__role")).toHaveTextContent("中路")
  })

  it("shows a provider-neutral auth failure instead of loading a live profile", async () => {
    const user = userEvent.setup()
    render(
      <App
        createAuthSessionClient={() => ({
          issue: vi.fn(async () => { throw new AuthSessionError("auth_unavailable", 503) }),
        })}
      />,
    )

    await user.click(screen.getByRole("button", { name: /enter riftcoach/i }))
    expect(await screen.findByRole("heading", { name: /sign-in is unavailable/i })).toBeInTheDocument()
    expect(screen.queryByText("auth_unavailable")).not.toBeInTheDocument()
    expect(screen.queryByText(/match review/i)).not.toBeInTheDocument()
  })
})

import { render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { App } from "./App"
import type { LiveWorkbenchControllerLike } from "./App"
import { AuthSessionError } from "../auth/session"

describe("Rift Command Center shell", () => {
  it("exposes the isolated portal preview without mounting the workbench", () => {
    render(<App surfaceOverride="awakening" />)

    expect(screen.getByTestId("awakening-scene")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /calibrate your analysis field/i })).toBeInTheDocument()
    expect(screen.queryByRole("navigation", { name: /command sections/i })).not.toBeInTheDocument()
    expect(screen.getByText(/preview only · no external lookup/i)).toBeInTheDocument()
  })

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
    expect(screen.getByLabelText(/runtime environment/i)).toHaveTextContent(/fixture/i)
    expect(screen.getByLabelText(/runtime environment/i)).toHaveTextContent(/no live i\/o/i)
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

  it("uses the live controller by default and keeps fixture mode explicit", async () => {
    const controller: LiveWorkbenchControllerLike = {
      snapshot: {
        state: {
          client: "ready",
          data: {
            profiles: [{
              playerProfileId: "95000000-0000-4000-8000-000000000001",
              riotId: "LiveRiver#EUW",
              routingRegion: "europe",
              relationshipRole: "self",
              verificationStatus: "unverified_claim",
              lastResolvedAt: "2026-08-23T11:00:00Z",
            }],
            selectedProfileId: "95000000-0000-4000-8000-000000000001",
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

    render(
      <App
        createLiveController={() => controller}
        createAuthSessionClient={() => ({
          issue: vi.fn(async () => ({
            schema_version: "1.0" as const,
            csrf_token: "csrf-test",
            expires_at: "2026-08-24T06:00:00Z",
          })),
        })}
      />,
    )

    await waitFor(() => expect(controller.start).toHaveBeenCalledTimes(1))
    expect(screen.getByRole("heading", { name: "LiveRiver#EUW" })).toBeInTheDocument()
    expect(screen.getByText(/live server projection/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/runtime environment/i)).toHaveTextContent(/live/i)
    expect(screen.getByLabelText(/runtime environment/i)).toHaveTextContent(/owner scoped/i)
    expect(screen.getByLabelText(/runtime environment/i)).not.toHaveTextContent(/fixture/i)
    expect(screen.queryByText(/fixture preview/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/2\s*\/\s*5/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/next session/i)).not.toBeInTheDocument()
  })

  it("shows a provider-neutral auth failure instead of loading a live profile", async () => {
    render(
      <App
        createAuthSessionClient={() => ({
          issue: vi.fn(async () => { throw new AuthSessionError("auth_unavailable", 503) }),
        })}
      />,
    )

    expect(await screen.findByRole("heading", { name: /sign-in is not ready/i })).toBeInTheDocument()
    expect(screen.getByText("auth_unavailable")).toBeInTheDocument()
    expect(screen.queryByText(/rift command center/i)).not.toBeInTheDocument()
  })
})

import { describe, expect, it, vi } from "vitest"

import type { CreatePlayerLinkInput, PlayerAccessApi } from "../api/playerLinkApi"
import type { PlayerLinkResponseWire, PlayerProfilePageWire } from "../api/wire"
import { PlayerAccessController } from "./playerAccessController"

const EXISTING = "95000000-0000-4000-8000-000000000001"
const ADDED = "95000000-0000-4000-8000-000000000003"
const LINK = "94000000-0000-4000-8000-000000000001"

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((next) => { resolve = next })
  return { promise, resolve }
}

function profiles(includeAdded = false): PlayerProfilePageWire {
  return {
    schema_version: "1.0",
    limit: 50,
    profiles: [
      {
        schema_version: "1.0",
        player_profile_id: EXISTING,
        riot_id: "Riverline#EUW",
        routing_region: "europe",
        relationship_role: "self",
        verification_status: "unverified_claim",
        last_resolved_at: "2026-08-24T02:00:00Z",
      },
      ...(includeAdded ? [{
        schema_version: "1.0" as const,
        player_profile_id: ADDED,
        riot_id: "Faker#KR1",
        routing_region: "asia" as const,
        relationship_role: "observed" as const,
        verification_status: "not_applicable" as const,
        last_resolved_at: "2026-08-24T02:00:02Z",
      }] : []),
    ],
  }
}

function link(status: "queued" | "running" | "succeeded" | "failed"): PlayerLinkResponseWire {
  const terminal = status === "succeeded" || status === "failed"
  return {
    schema_version: "1.0",
    link_task_id: LINK,
    status,
    created_at: "2026-08-24T02:00:00Z",
    updated_at: "2026-08-24T02:00:02Z",
    claimed_at: status === "queued" ? null : "2026-08-24T02:00:01Z",
    finished_at: terminal ? "2026-08-24T02:00:02Z" : null,
    relationship_role: "observed",
    verification_status: "not_applicable",
    player_subject_id: status === "succeeded" ? "93000000-0000-4000-8000-000000000001" : null,
    relationship_id: status === "succeeded" ? ADDED : null,
    confirmed_riot_id: status === "succeeded" ? "Faker#KR1" : null,
    failure: status === "failed" ? { code: "player_not_found", retryable: false } : null,
  }
}

function createApi(overrides: Partial<PlayerAccessApi> = {}): PlayerAccessApi {
  return {
    listProfiles: vi.fn(async () => profiles()),
    createLink: vi.fn(async () => ({
      schema_version: "1.0" as const,
      disposition: "created" as const,
      link_task_id: LINK,
      status: "queued" as const,
      link: `/player-links/${LINK}`,
    })),
    getLink: vi.fn(async () => link("succeeded")),
    ...overrides,
  }
}

describe("PlayerAccessController", () => {
  it("loads owner-scoped profiles and makes no selection outside the returned list", async () => {
    const controller = new PlayerAccessController({ api: createApi(), csrfToken: "csrf" })

    await controller.start()
    expect(controller.snapshot).toMatchObject({
      status: "ready",
      selectedProfileId: EXISTING,
      link: { status: "idle" },
    })

    expect(() => controller.selectProfile("95000000-0000-4000-8000-000000000099")).toThrow(/profile/i)
    expect(controller.snapshot.status === "ready" && controller.snapshot.selectedProfileId).toBe(EXISTING)
  })

  it("polls bounded active states, refreshes profiles and selects the resolved relationship", async () => {
    const listProfiles = vi.fn()
      .mockResolvedValueOnce(profiles())
      .mockResolvedValueOnce(profiles(true))
    const getLink = vi.fn()
      .mockResolvedValueOnce(link("queued"))
      .mockResolvedValueOnce(link("running"))
      .mockResolvedValueOnce(link("succeeded"))
    const api = createApi({ listProfiles, getLink })
    const controller = new PlayerAccessController({
      api,
      csrfToken: "csrf",
      idempotencyKeyFactory: () => "player-link-1",
      pollDelaysMs: [0, 0, 0],
    })

    await controller.start()
    await controller.addPlayer({ riotId: "Faker#KR1", routingRegion: "asia", relationshipRole: "public_observed" })

    expect(api.createLink).toHaveBeenCalledWith(expect.objectContaining({
      riotId: "Faker#KR1",
      csrfToken: "csrf",
      idempotencyKey: "player-link-1",
    }))
    expect(getLink).toHaveBeenCalledTimes(3)
    expect(controller.snapshot).toMatchObject({
      status: "ready",
      selectedProfileId: ADDED,
      link: { status: "succeeded", riotId: "Faker#KR1" },
    })
  })

  it("keeps a timed-out task pending and requires an explicit fresh submission after terminal failure", async () => {
    const keys = ["player-link-1", "player-link-2"]
    const getLink = vi.fn()
      .mockResolvedValueOnce(link("running"))
      .mockResolvedValueOnce(link("failed"))
      .mockResolvedValueOnce(link("failed"))
    const api = createApi({ getLink })
    const controller = new PlayerAccessController({
      api,
      csrfToken: "csrf",
      idempotencyKeyFactory: () => keys.shift()!,
      pollDelaysMs: [0],
    })

    await controller.start()
    await controller.addPlayer({ riotId: "Slow#NA1", routingRegion: "americas", relationshipRole: "self" })
    expect(controller.snapshot.status === "ready" && controller.snapshot.link).toMatchObject({ status: "pending" })

    await expect(controller.addPlayer({ riotId: "Duplicate#NA1", routingRegion: "americas", relationshipRole: "self" }))
      .rejects.toThrow(/already active/i)
    expect(api.createLink).toHaveBeenCalledTimes(1)

    await controller.resumePending()
    expect(controller.snapshot.status === "ready" && controller.snapshot.link).toEqual({ status: "failed", code: "player_not_found", retryable: false })

    await controller.addPlayer({ riotId: "Missing#NA1", routingRegion: "americas", relationshipRole: "self" })
    expect(controller.snapshot.status === "ready" && controller.snapshot.link).toEqual({ status: "failed", code: "player_not_found", retryable: false })
    expect(api.createLink).toHaveBeenNthCalledWith(1, expect.objectContaining({ idempotencyKey: "player-link-1" }))
    expect(api.createLink).toHaveBeenNthCalledWith(2, expect.objectContaining({ idempotencyKey: "player-link-2" }))
  })

  it("aborts an in-flight profile load on dispose and ignores a late response", async () => {
    const pendingProfiles = deferred<PlayerProfilePageWire>()
    const listProfiles = vi.fn((_signal?: AbortSignal) => pendingProfiles.promise)
    const controller = new PlayerAccessController({
      api: createApi({ listProfiles }),
      csrfToken: "csrf",
    })

    const loading = controller.start()
    const signal = listProfiles.mock.calls[0]?.[0]
    expect(signal).toBeInstanceOf(AbortSignal)
    expect(signal?.aborted).toBe(false)

    controller.dispose()
    expect(signal?.aborted).toBe(true)

    pendingProfiles.resolve(profiles())
    await loading
    expect(controller.snapshot).toEqual({ status: "loading" })
  })

  it("cancels an older submission on refresh and rejects its late terminal state", async () => {
    const stalePoll = deferred<PlayerLinkResponseWire>()
    const listProfiles = vi.fn()
      .mockResolvedValueOnce(profiles())
      .mockResolvedValueOnce(profiles())
      .mockResolvedValueOnce(profiles(true))
    const createLink = vi.fn(async (_input: CreatePlayerLinkInput) => ({
      schema_version: "1.0" as const,
      disposition: "created" as const,
      link_task_id: LINK,
      status: "queued" as const,
      link: `/player-links/${LINK}`,
    }))
    const getLink = vi.fn()
      .mockImplementationOnce((_link: string, _signal?: AbortSignal) => stalePoll.promise)
      .mockResolvedValueOnce(link("succeeded"))
    const controller = new PlayerAccessController({
      api: createApi({ listProfiles, createLink, getLink }),
      csrfToken: "csrf",
      idempotencyKeyFactory: (() => {
        const keys = ["player-link-stale", "player-link-current"]
        return () => keys.shift()!
      })(),
      pollDelaysMs: [0],
    })

    await controller.start()
    const staleSubmission = controller.addPlayer({
      riotId: "Stale#NA1",
      routingRegion: "americas",
      relationshipRole: "self",
    })
    await vi.waitFor(() => expect(getLink).toHaveBeenCalledTimes(1))

    const staleCreateSignal = createLink.mock.calls[0]?.[0].signal
    const stalePollSignal = getLink.mock.calls[0]?.[1]
    expect(staleCreateSignal).toBe(stalePollSignal)
    expect(stalePollSignal?.aborted).toBe(false)

    await controller.start()
    const currentSubmission = controller.addPlayer({
      riotId: "Faker#KR1",
      routingRegion: "asia",
      relationshipRole: "public_observed",
    })
    await currentSubmission

    const currentCreateSignal = createLink.mock.calls[1]?.[0].signal
    const currentPollSignal = getLink.mock.calls[1]?.[1]
    const refreshSignal = listProfiles.mock.calls[2]?.[0]
    expect(staleCreateSignal?.aborted).toBe(true)
    expect(stalePollSignal?.aborted).toBe(true)
    expect(currentCreateSignal).toBe(currentPollSignal)
    expect(currentPollSignal).toBe(refreshSignal)
    expect(currentPollSignal?.aborted).toBe(false)
    expect(controller.snapshot).toMatchObject({
      status: "ready",
      selectedProfileId: ADDED,
      link: { status: "succeeded", riotId: "Faker#KR1" },
    })

    stalePoll.resolve(link("failed"))
    await staleSubmission
    expect(controller.snapshot).toMatchObject({
      status: "ready",
      selectedProfileId: ADDED,
      link: { status: "succeeded", riotId: "Faker#KR1" },
    })

    controller.dispose()
    expect(currentPollSignal?.aborted).toBe(true)
  })
})

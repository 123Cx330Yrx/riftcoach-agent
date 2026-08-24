import { describe, expect, it, vi } from "vitest"

import { ApiClient } from "./client"
import { PlayerLinkHttpApi } from "./playerLinkApi"

const LINK_ID = "94000000-0000-4000-8000-000000000001"
const RELATIONSHIP_ID = "95000000-0000-4000-8000-000000000001"

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json" },
  })
}

function linkProjection(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: "1.0",
    link_task_id: LINK_ID,
    status: "queued",
    created_at: "2026-08-24T02:00:00Z",
    updated_at: "2026-08-24T02:00:00Z",
    claimed_at: null,
    finished_at: null,
    relationship_role: "observed",
    verification_status: "not_applicable",
    player_subject_id: null,
    relationship_id: null,
    confirmed_riot_id: null,
    failure: null,
    ...overrides,
  }
}

describe("PlayerLinkHttpApi", () => {
  it("posts a bounded link request with in-memory CSRF and a fresh idempotency key", async () => {
    const fetcher = vi.fn(async () => json({
      schema_version: "1.0",
      disposition: "created",
      link_task_id: LINK_ID,
      status: "queued",
      link: `/player-links/${LINK_ID}`,
    }, 202))
    const api = new PlayerLinkHttpApi(new ApiClient({ fetcher }))

    const result = await api.createLink({
      riotId: "Faker#KR1",
      routingRegion: "asia",
      relationshipRole: "public_observed",
      csrfToken: "csrf-session-only",
      idempotencyKey: "player-link-request-1",
    })

    expect(result.link_task_id).toBe(LINK_ID)
    expect(fetcher).toHaveBeenCalledWith("/api/player-links", expect.objectContaining({
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": "player-link-request-1",
        "X-CSRF-Token": "csrf-session-only",
      },
      body: JSON.stringify({
        riot_id: "Faker#KR1",
        routing_region: "asia",
        relationship_role: "observed",
      }),
    }))
  })

  it("strictly decodes a succeeded terminal response and preserves owner-safe identity", async () => {
    const fetcher = vi.fn(async () => json({
      schema_version: "1.0",
      link_task_id: LINK_ID,
      status: "succeeded",
      created_at: "2026-08-24T02:00:00Z",
      updated_at: "2026-08-24T02:00:02Z",
      claimed_at: "2026-08-24T02:00:01Z",
      finished_at: "2026-08-24T02:00:02Z",
      relationship_role: "observed",
      verification_status: "not_applicable",
      player_subject_id: "93000000-0000-4000-8000-000000000001",
      relationship_id: RELATIONSHIP_ID,
      confirmed_riot_id: "Faker#KR1",
      failure: null,
    }))
    const api = new PlayerLinkHttpApi(new ApiClient({ fetcher }))

    await expect(api.getLink(`/player-links/${LINK_ID}`)).resolves.toMatchObject({
      status: "succeeded",
      relationship_id: RELATIONSHIP_ID,
      confirmed_riot_id: "Faker#KR1",
    })
  })

  it("rejects mismatched link URLs and impossible terminal projections", async () => {
    const api = new PlayerLinkHttpApi(new ApiClient({ fetcher: vi.fn(async () => json({
      schema_version: "1.0",
      link_task_id: LINK_ID,
      status: "succeeded",
      created_at: "2026-08-24T02:00:00Z",
      updated_at: "2026-08-24T02:00:02Z",
      claimed_at: "2026-08-24T02:00:01Z",
      finished_at: "2026-08-24T02:00:02Z",
      relationship_role: "observed",
      verification_status: "not_applicable",
      player_subject_id: null,
      relationship_id: null,
      confirmed_riot_id: null,
      failure: null,
    })) }))

    await expect(api.getLink(`/player-links/${LINK_ID}`)).rejects.toThrow(/succeeded/i)
    await expect(api.getLink("https://private.invalid/player-links/1")).rejects.toThrow(/link path/i)
  })

  it("rejects partial identity and impossible claim timestamps in every state", async () => {
    const invalid = [
      linkProjection({ claimed_at: "2026-08-24T02:00:01Z" }),
      linkProjection({ status: "running" }),
      linkProjection({
        status: "running",
        updated_at: "2026-08-24T02:00:01Z",
        claimed_at: "2026-08-24T01:59:59Z",
      }),
      linkProjection({
        status: "failed",
        claimed_at: "2026-08-24T02:00:01Z",
        finished_at: "2026-08-24T02:00:02Z",
        player_subject_id: "93000000-0000-4000-8000-000000000001",
        failure: { code: "player_not_found", retryable: false },
      }),
    ]

    for (const projection of invalid) {
      const api = new PlayerLinkHttpApi(new ApiClient({
        fetcher: vi.fn(async () => json(projection)),
      }))
      await expect(api.getLink(`/player-links/${LINK_ID}`)).rejects.toThrow()
    }
  })
})

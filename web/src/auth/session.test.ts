import { describe, expect, it, vi } from "vitest"

import { AuthSessionError, BrowserAuthSessionClient } from "./session"

describe("browser auth session boundary", () => {
  it("issues only a same-origin opaque session and decodes the typed response", async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(input).toBe("/api/auth/session")
      expect(init).toMatchObject({ method: "POST", credentials: "same-origin" })
      return new Response(JSON.stringify({
        schema_version: "1.0",
        csrf_token: "csrf-token",
        expires_at: "2026-08-24T06:00:00Z",
      }), { headers: { "content-type": "application/json" } })
    })

    await expect(new BrowserAuthSessionClient(fetcher).issue()).resolves.toMatchObject({
      schema_version: "1.0",
      csrf_token: "csrf-token",
    })
  })

  it("maps body-free provider failures without exposing response text", async () => {
    const client = new BrowserAuthSessionClient(vi.fn(async () => new Response(
      JSON.stringify({ code: "auth_unavailable" }),
      { status: 503, headers: { "content-type": "application/json" } },
    )))

    const caught = await client.issue().catch((error: unknown) => error)
    expect(caught).toBeInstanceOf(AuthSessionError)
    expect(caught).toMatchObject({ code: "auth_unavailable", status: 503 })
    expect(String(caught)).not.toContain("csrf")
  })

  it("fails closed for a malformed success payload", async () => {
    const client = new BrowserAuthSessionClient(vi.fn(async () => new Response(
      JSON.stringify({ schema_version: "1.0", csrf_token: "csrf", expires_at: "not-a-time" }),
      { headers: { "content-type": "application/json" } },
    )))
    await expect(client.issue()).rejects.toMatchObject({ code: "auth_unavailable" })
  })
})

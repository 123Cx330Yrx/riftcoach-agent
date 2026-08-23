import { describe, expect, it, vi } from "vitest"

import { ApiClient, ApiClientError } from "./client"

describe("bounded same-origin API client", () => {
  it("invokes the browser default fetch with its global receiver", async () => {
    const browserFetch = vi.fn(function (this: unknown) {
      if (this !== globalThis) throw new TypeError("Illegal invocation")
      return Promise.resolve(new Response('{"schema_version":"1.0"}', {
        status: 200,
        headers: { "content-type": "application/json" },
      }))
    })
    vi.stubGlobal("fetch", browserFetch)
    const client = new ApiClient()

    await expect(client.getJson("/player-profiles", (value) => value)).resolves.toEqual({
      schema_version: "1.0",
    })
    expect(browserFetch).toHaveBeenCalledOnce()
  })

  it("uses relative /api, forwards AbortSignal and decodes unknown JSON", async () => {
    const controller = new AbortController()
    const fetcher = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response('{"schema_version":"1.0"}', {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    const client = new ApiClient({ fetcher })

    const result = await client.getJson(
      "/player-profiles",
      (value) => value as { schema_version: string },
      controller.signal,
    )

    expect(result.schema_version).toBe("1.0")
    expect(fetcher).toHaveBeenCalledWith(
      "/api/player-profiles",
      expect.objectContaining({ signal: controller.signal, credentials: "same-origin" }),
    )
  })

  it("rejects absolute/traversal paths before fetch", async () => {
    const fetcher = vi.fn()
    const client = new ApiClient({ fetcher })

    await expect(client.getJson("https://private.example/data", (value) => value)).rejects.toThrow(/relative/i)
    await expect(client.getJson("/../secret", (value) => value)).rejects.toThrow(/relative/i)
    expect(fetcher).not.toHaveBeenCalled()
  })

  it("enforces content type and body size without exposing response text", async () => {
    const wrongType = new ApiClient({
      fetcher: vi.fn(async () => new Response("postgresql://secret@private", { headers: { "content-type": "text/plain" } })),
    })
    const tooLarge = new ApiClient({
      fetcher: vi.fn(async () => new Response("{}", { headers: { "content-type": "application/json", "content-length": "3000000" } })),
    })

    await expect(wrongType.getJson("/player-profiles", (value) => value)).rejects.toThrow("api_content_type_invalid")
    await expect(tooLarge.getJson("/player-profiles", (value) => value)).rejects.toThrow("api_body_too_large")
  })

  it("cancels an undeclared streaming body when the byte limit is crossed", async () => {
    let pullCount = 0
    let cancelled = false
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        pullCount += 1
        if (pullCount <= 2) {
          controller.enqueue(new Uint8Array(1_100_000))
          return
        }
        throw new Error("client read beyond the declared safety boundary")
      },
      cancel() {
        cancelled = true
      },
    })
    const client = new ApiClient({
      fetcher: vi.fn(async () => new Response(body, {
        headers: { "content-type": "application/json" },
      })),
    })

    await expect(client.getJson("/player-profiles", (value) => value)).rejects.toThrow("api_body_too_large")
    expect(cancelled).toBe(true)
    expect(pullCount).toBeLessThanOrEqual(3)
  })

  it("maps only allowlisted body-free API errors", async () => {
    const client = new ApiClient({
      fetcher: vi.fn(async () =>
        new Response('{"code":"run_not_ready","run_id":"review_1"}', {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    })

    const caught = await client.getJson("/runs/review_1", (value) => value).catch((error: unknown) => error)

    expect(caught).toBeInstanceOf(ApiClientError)
    expect(caught).toMatchObject({ code: "run_not_ready", status: 409, runId: "review_1" })
    expect(String(caught)).not.toContain("private")
  })

  it("rejects unknown error codes and safely reads Markdown text", async () => {
    const unknown = new ApiClient({
      fetcher: vi.fn(async () =>
        new Response('{"code":"postgresql://secret@private"}', {
          status: 500,
          headers: { "content-type": "application/json" },
        }),
      ),
    })
    const markdown = new ApiClient({
      fetcher: vi.fn(async () =>
        new Response("## Verified", {
          status: 200,
          headers: { "content-type": "text/markdown; charset=utf-8" },
        }),
      ),
    })

    await expect(unknown.getJson("/runs/review_1", (value) => value)).rejects.toThrow("api_error_invalid")
    await expect(markdown.getText("/runs/review_1/report", (value) => value)).resolves.toBe("## Verified")
  })
})

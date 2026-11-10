import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiClient } from "../api/client"
import { RecentReviewApi } from "../api/recentReviewApi"
import { ProductLocaleProvider } from "../i18n/ProductLocaleProvider"
import { RecentReviewStart } from "./RecentReviewStart"

const PROFILE = "82000000-0000-4000-8000-000000000901"
const CONVERSATION = "83000000-0000-4000-8000-000000000901"
const TASK = "84000000-0000-4000-8000-000000000901"
const json = (value: unknown) => new Response(JSON.stringify(value), { headers: { "Content-Type": "application/json" } })
const conversation = { schema_version: "1.0", relationship_id: PROFILE, relationship_role: "observed", status: "active", conversation_id: CONVERSATION, disposition: "created" }
const task = { schema_version: "2.0", disposition: "created", conversation_id: CONVERSATION, task_id: TASK, run_id: "review-browser", status: "queued" }
function show(api: RecentReviewApi, onChanged = vi.fn(), previousTask?: string) {
  return { ...render(<ProductLocaleProvider store={{ read: () => "zh-CN", write: () => undefined }}>
    <RecentReviewStart profileId={PROFILE} role="public_observed" previousTask={previousTask} csrfToken="csrf-test" api={api} onChanged={onChanged} onAuthFailure={vi.fn()} />
  </ProductLocaleProvider>), onChanged }
}
beforeEach(() => sessionStorage.clear())
describe("normal recent-review entry", () => {
  it("keeps both operation keys across a lost response and remount, without automatic sends", async () => {
    const calls: { url: string; init: RequestInit }[] = []
    let lose = true
    const api = new RecentReviewApi(new ApiClient({ fetcher: async (url, init) => {
      calls.push({ url: String(url), init: init! })
      if (String(url).endsWith("/conversations")) return json(conversation)
      if (lose) { lose = false; throw new TypeError("lost response") }
      return json({ ...task, disposition: "replayed" })
    } }))
    const first = show(api)
    expect(calls).toHaveLength(0)
    fireEvent.click(screen.getByRole("button", { name: "发起复盘" }))
    await screen.findByRole("alert")
    first.unmount()
    const next = show(api)
    expect(calls).toHaveLength(2)
    const button = screen.getByRole("button", { name: "发起复盘" })
    fireEvent.click(button); fireEvent.click(button)
    await waitFor(() => expect(next.onChanged).toHaveBeenCalledOnce())
    expect(calls).toHaveLength(4)
    for (const [a, b] of [[0, 2], [1, 3]]) expect(calls[a!]!.init.headers).toEqual(calls[b!]!.init.headers)
    expect(calls[0]!.init.body).toBe(JSON.stringify({ player_profile_id: PROFILE }))
    expect(calls[1]!.init.body).toBe(JSON.stringify({ count: 5, queue: 420, focus: "overall" }))
    expect(new Headers(calls[1]!.init.headers).get("X-CSRF-Token")).toBe("csrf-test")
    expect(calls[1]!.url).toBe(`/api/conversations/${CONVERSATION}/reviews/recent`)
  })
  it.each([{ ...conversation, relationship_id: TASK }, { ...conversation, relationship_role: "self" }])("rejects a conversation for another identity or role", async value => {
    const fetcher = vi.fn(async () => json(value))
    const api = new RecentReviewApi(new ApiClient({ fetcher }))
    await expect(api.start(PROFILE, "public_observed", "review-test", "csrf-test", new AbortController().signal)).rejects.toThrow("review_response_invalid")
    expect(fetcher).toHaveBeenCalledOnce()
  })
})

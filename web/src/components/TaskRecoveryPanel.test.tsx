import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ApiClient, ApiClientError } from "../api/client"
import { TaskContinuationApi } from "../api/taskContinuationApi"
import { ProductLocaleProvider } from "../i18n/ProductLocaleProvider"
import { TaskRecoveryPanel } from "./TaskRecoveryPanel"

const TASK = "95000000-0000-4000-8000-000000000001"
const RUN = "recovery-test"
const ACCOUNTING = { scope: "cumulative_session", requests_reserved: 3, requests_observed: 3,
  known_tokens: 120, unknown_token_reservation: 80384, retries: 0, unresolved_intents: 0 }
const wire = (reason = "session_timeout_awaiting_manual_retry") => ({ task_id: TASK, run_id: RUN,
  status: "recovery_required", profile: "sol-dual-development-v1", checkpoint_sha256: "a".repeat(64),
  reason, session_accounting: ACCOUNTING, publication_allowed: false })
const json = (value: unknown) => new Response(JSON.stringify(value), { headers: { "Content-Type": "application/json" } })
function show(api: TaskContinuationApi, onChanged = vi.fn()) {
  return { ...render(<ProductLocaleProvider store={{ read: () => "zh-CN", write: () => undefined }}>
    <TaskRecoveryPanel taskId={TASK} runId={RUN} csrfToken="csrf-test" api={api} onChanged={onChanged} onAuthFailure={vi.fn()} />
  </ProductLocaleProvider>), onChanged }
}

describe("explicit task recovery", () => {
  it.each(["sol-dual-development-v1", "sol-dual-product-v1"])("does not retry on load; preserves key/checkpoint for %s", async (profile) => {
    const calls: RequestInit[] = []
    const api = new TaskContinuationApi(new ApiClient({ fetcher: async (_url, init) => {
      if (init?.method !== "POST") return json({ ...wire(), profile })
      calls.push(init)
      if (calls.length === 1) throw new TypeError("offline")
      return json({ task_id: TASK, run_id: RUN, status: "queued", replayed: true })
    } }))
    const { onChanged } = show(api)
    const button = await screen.findByRole("button", { name: "补测当前步骤一次" })
    expect(calls).toHaveLength(0)
    fireEvent.click(button)
    await screen.findByRole("alert")
    fireEvent.click(button)
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
    expect(calls).toHaveLength(2)
    expect(calls[0]?.body).toBe(JSON.stringify({ checkpoint_sha256: "a".repeat(64), manual_retry: true }))
    expect(calls[1]?.headers).toEqual(calls[0]?.headers)
    expect(new Headers(calls[0]?.headers).get("X-CSRF-Token")).toBe("csrf-test")
  })

  it("uses ordinary continuation for a repaired local step and suppresses double clicks", async () => {
    const api = new TaskContinuationApi()
    vi.spyOn(api, "get").mockResolvedValue({ checkpoint: "b".repeat(64), reason: "session_projection_changed", accounting: { ...ACCOUNTING, scope: "cumulative_session" } })
    let finish!: () => void
    const resume = vi.spyOn(api, "resume").mockImplementation(() => new Promise(resolve => { finish = resolve }))
    const { onChanged } = show(api)
    const button = await screen.findByRole("button", { name: "检查并继续" })
    fireEvent.click(button); fireEvent.click(button)
    expect(resume).toHaveBeenCalledTimes(1)
    expect(resume.mock.calls[0]?.slice(0, 4)).toEqual([TASK, RUN, "b".repeat(64), false])
    finish()
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1))
  })

  it("allows cancellation but no resend while an intent remains unresolved", async () => {
    const calls: RequestInit[] = []
    const api = new TaskContinuationApi(new ApiClient({ fetcher: async (_url, init) => {
      if (init?.method !== "POST") return json({ ...wire(), session_accounting: { ...ACCOUNTING, unresolved_intents: 1 } })
      calls.push(init)
      return json({ schema_version: "1.0", task_id: TASK, disposition: "cancelled", status: "cancelled" })
    } }))
    const { onChanged } = show(api)
    fireEvent.click(await screen.findByRole("button", { name: "取消此任务" }))
    await waitFor(() => expect(onChanged).toHaveBeenCalledOnce())
    expect(screen.queryByRole("button", { name: "补测当前步骤一次" })).toBeNull()
    expect(calls[0]?.body).toBeUndefined()
    expect(new Headers(calls[0]?.headers).get("Idempotency-Key")).toMatch(/^recovery-/)
  })

  it("disables stale actions and ignores a completion after leaving the task", async () => {
    const api = new TaskContinuationApi()
    vi.spyOn(api, "get").mockResolvedValue({ checkpoint: "a".repeat(64), reason: "session_model_boundary", accounting: { ...ACCOUNTING, scope: "cumulative_session" } })
    vi.spyOn(api, "resume").mockRejectedValue(new ApiClientError("continuation_conflict", 409))
    const view = show(api)
    fireEvent.click(await screen.findByRole("button", { name: "检查并继续" }))
    await screen.findByRole("alert")
    expect(screen.getByRole("button", { name: "检查并继续" })).toBeDisabled()
    expect(view.onChanged).not.toHaveBeenCalled()
    view.unmount()
    let finish!: () => void
    vi.spyOn(api, "resume").mockImplementation(() => new Promise(resolve => { finish = resolve }))
    const second = show(api)
    fireEvent.click(await screen.findByRole("button", { name: "检查并继续" }))
    second.unmount(); finish()
    await Promise.resolve()
    expect(second.onChanged).not.toHaveBeenCalled()
  })

  it("rejects foreign or malformed detail without exposing recovery actions", async () => {
    const api = new TaskContinuationApi(new ApiClient({ fetcher: async () => json({ ...wire(), run_id: "another-run" }) }))
    show(api)
    await screen.findByRole("alert")
    expect(screen.queryByRole("button", { name: "补测当前步骤一次" })).toBeNull()
    expect(screen.queryByRole("button", { name: "取消此任务" })).toBeNull()
  })
})

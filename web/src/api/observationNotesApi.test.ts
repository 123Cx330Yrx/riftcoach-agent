import { describe, expect, it } from "vitest"
import { ApiClient } from "./client"
import { ObservationNotesApi, decodeObservationNotes, type NoteSaveOperation } from "./observationNotesApi"

const profileId = "11111111-1111-4111-8111-111111111111"
const conversationId = "22222222-2222-4222-8222-222222222222"
const candidateId = "33333333-3333-4333-8333-333333333333"
const reference = { kind: "user_attached_archive" as const, source_run_id: "fixture_run", bundle_digest: "a".repeat(64), report_sha256: "b".repeat(64), observed_at: "2026-09-10T00:00:00Z" }
const note = { schema_version: "1.0", record_id: candidateId, target_kind: "review_memory", relationship_id: profileId, relationship_role: "observed", memory_key: "observation_note", version: 1, status: "active", payload: { text: "先观察游走前兵线", archive_reference: reference }, supersedes_record_id: null, created_at: "2026-09-11T00:00:00Z", updated_at: "2026-09-11T00:00:00Z" }
const candidate = { schema_version: "1.0", candidate_id: candidateId, conversation_id: conversationId, target_scope: "owner_player", candidate_kind: "review_memory", memory_key: "observation_note", operation: "append", requires_confirmation: true, status: "pending", gate_policy_version: "memory-gate-v2-user-observation", created_at: "2026-09-11T00:00:00Z", expires_at: "2026-10-11T00:00:00Z", decided_at: null, decision_reason_code: null }
function json(v: unknown) { return new Response(JSON.stringify(v), { headers: { "Content-Type": "application/json" } }) }
describe("observation note API", () => {
  it("reads notes and refuses mismatched relationships and malformed references", () => {
    expect(decodeObservationNotes({ schema_version: "1.0", records: [note] }, profileId)[0]?.reference).toEqual(reference)
    for (const changed of [{ ...note, relationship_role: "self" }, { ...note, relationship_id: candidateId }, { ...note, payload: { text: "test", archive_reference: { ...reference, report_sha256: "bad" } } }]) {
      expect(() => decodeObservationNotes({ schema_version: "1.0", records: [changed] }, profileId)).toThrow()
    }
  })
  it("retries uncertain acceptance without creating another candidate and sends no body to accept", async () => {
    const calls: { path: string; init: RequestInit | undefined }[] = []
    let acceptCount = 0
    const api = new ObservationNotesApi(new ApiClient({ fetcher: async (input, init) => {
      const path = String(input); calls.push({ path, init })
      if (path === "/api/conversations") return json({ schema_version: "1.0", disposition: "created", conversation_id: conversationId, relationship_id: profileId, relationship_role: "observed", status: "active", created_at: "2026-09-11T00:00:00Z", updated_at: "2026-09-11T00:00:00Z", last_message_at: null })
      if (path.endsWith("/memory-candidates")) return json(candidate)
      if (path.endsWith("/accept")) { if (++acceptCount === 1) throw new TypeError("connection_lost"); return json({ ...candidate, status: "accepted" }) }
      throw Error("unexpected_request")
    } }))
    const operation: NoteSaveOperation = { key: "save-1", profileId, text: "自己的观察", reference }
    await expect(api.save(operation, "csrf-test")).rejects.toThrow()
    await api.save(operation, "csrf-test")
    expect(calls.map(c => c.path)).toEqual(["/api/conversations", `/api/conversations/${conversationId}/memory-candidates`, `/api/memory-candidates/${candidateId}/accept`, `/api/memory-candidates/${candidateId}/accept`])
    expect(calls[2]?.init?.body).toBeUndefined()
    expect(new Headers(calls[2]?.init?.headers).get("X-CSRF-Token")).toBe("csrf-test")
    const submitted = JSON.parse(String(calls[1]?.init?.body))
    expect(submitted.proposal_payload.value.archive_reference.kind).toBe("user_attached_archive")
    expect(submitted).not.toHaveProperty("source_task_id")
  })
  it("refuses a conversation belonging to another profile before creating a note", async () => {
    let calls = 0
    const api = new ObservationNotesApi(new ApiClient({ fetcher: async () => {
      calls++; return json({ schema_version: "1.0", disposition: "created", conversation_id: conversationId, relationship_id: candidateId, relationship_role: "observed", status: "active" })
    } }))
    await expect(api.save({ key: "save-1", profileId, text: "note", reference }, "csrf-test")).rejects.toThrow()
    expect(calls).toBe(1)
  })
})

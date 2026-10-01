import { ApiClient } from "./client"
import type { ObservationArchive } from "../workbench/observationArchive"

export interface ArchiveReference {
  kind: "user_attached_archive"
  source_run_id: string
  bundle_digest: string
  report_sha256: string
  observed_at: string
}
export interface ObservationNote { id: string; text: string; createdAt: string; reference?: ArchiveReference }
export interface NoteSaveOperation {
  key: string; text: string; reference: ArchiveReference; profileId: string
  conversationId?: string; candidateId?: string
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const sha = /^[a-f0-9]{64}$/
function fail(): never { throw new Error("observation_note_response_invalid") }
function row(v: unknown): Record<string, unknown> { return v !== null && typeof v === "object" && !Array.isArray(v) ? v as Record<string, unknown> : fail() }
function text(v: unknown, max = 2000): string { return typeof v === "string" && v.trim().length > 0 && v.length <= max ? v : fail() }
function id(v: unknown): string { const s = text(v, 36); return uuid.test(s) ? s : fail() }
function timestamp(v: unknown): string { const s = text(v, 50); return /(?:Z|[+-]\d\d:\d\d)$/.test(s) && Number.isFinite(Date.parse(s)) ? s : fail() }
function exact(v: Record<string, unknown>, keys: string[]) { if (Object.keys(v).some(k => !keys.includes(k))) fail() }
function reference(v: unknown): ArchiveReference {
  const r = row(v)
  exact(r, ["kind", "source_run_id", "bundle_digest", "report_sha256", "observed_at"])
  if (r.kind !== "user_attached_archive" || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$/.test(text(r.source_run_id, 96)) || !sha.test(text(r.bundle_digest, 64)) || !sha.test(text(r.report_sha256, 64))) fail()
  timestamp(r.observed_at)
  return r as unknown as ArchiveReference
}
export function archiveReference(archive: ObservationArchive): ArchiveReference {
  return { kind: "user_attached_archive", source_run_id: archive.source_run_id, bundle_digest: archive.evidence.bundle_digest, report_sha256: archive.report.sha256, observed_at: archive.observed_at }
}
export function decodeObservationNotes(v: unknown, profileId: string): ObservationNote[] {
  id(profileId)
  const page = row(v); exact(page, ["schema_version", "records"])
  if (page.schema_version !== "1.0" || !Array.isArray(page.records) || page.records.length > 100) fail()
  const notes: ObservationNote[] = [], seen = new Set<string>()
  for (const value of page.records) {
    const r = row(value)
    exact(r, ["schema_version", "record_id", "target_kind", "relationship_id", "relationship_role", "memory_key", "version", "status", "payload", "supersedes_record_id", "created_at", "updated_at"])
    if (r.schema_version !== "1.0" || r.target_kind !== "review_memory" || r.relationship_id !== profileId || r.relationship_role !== "observed" || r.status !== "active") fail()
    const recordId = id(r.record_id)
    if (seen.has(recordId)) fail()
    seen.add(recordId)
    const createdAt = timestamp(r.created_at); timestamp(r.updated_at)
    if (!Number.isInteger(r.version) || Number(r.version) < 1) fail()
    if (r.memory_key !== "observation_note") continue
    const p = row(r.payload); exact(p, ["text", "archive_reference"])
    notes.push({ id: recordId, text: text(p.text), createdAt, ...(p.archive_reference == null ? {} : { reference: reference(p.archive_reference) }) })
  }
  return notes.sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
}
function decodeCandidate(v: unknown, conversationId: string, candidateId?: string): { id: string; status: string } {
  const r = row(v)
  exact(r, ["schema_version", "candidate_id", "conversation_id", "target_scope", "candidate_kind", "memory_key", "operation", "requires_confirmation", "status", "gate_policy_version", "created_at", "expires_at", "decided_at", "decision_reason_code"])
  const parsedId = id(r.candidate_id)
  if (r.schema_version !== "1.0" || r.conversation_id !== conversationId || (candidateId !== undefined && parsedId !== candidateId) || r.target_scope !== "owner_player" || r.candidate_kind !== "review_memory" || r.memory_key !== "observation_note" || r.operation !== "append" || !["pending", "accepted"].includes(String(r.status))) fail()
  return { id: parsedId, status: String(r.status) }
}
export class ObservationNotesApi {
  constructor(private readonly client: ApiClient) {}
  list(profileId: string, signal?: AbortSignal) {
    id(profileId)
    return this.client.getJson(`/memory/players/${profileId}/reviews?limit=100`, v => decodeObservationNotes(v, profileId), signal)
  }
  async save(op: NoteSaveOperation, csrfToken: string, signal?: AbortSignal): Promise<void> {
    id(op.profileId); text(op.text); reference(op.reference)
    if (new TextEncoder().encode(JSON.stringify({ text: op.text, archive_reference: op.reference })).byteLength > 4096) throw new Error("observation_note_too_large")
    if (!op.conversationId) {
      op.conversationId = await this.client.postJson("/conversations", { player_profile_id: op.profileId }, v => {
        const r = row(v)
        exact(r, ["schema_version", "disposition", "conversation_id", "relationship_id", "relationship_role", "status", "created_at", "updated_at", "last_message_at"])
        if (!["created", "replayed"].includes(String(r.disposition)) || r.schema_version !== "1.0" || r.relationship_id !== op.profileId || r.relationship_role !== "observed" || r.status !== "active") fail()
        return id(r.conversation_id)
      }, { csrfToken, idempotencyKey: `note-conversation-${op.key}` }, signal)
    }
    const conversationId = op.conversationId
    if (!op.candidateId) {
      const result = await this.client.postJson(`/conversations/${conversationId}/memory-candidates`, {
        target_scope: "owner_player", candidate_kind: "review_memory", memory_key: "observation_note", operation: "append",
        proposal_payload: { value: { text: op.text, archive_reference: op.reference } },
      }, v => decodeCandidate(v, conversationId), { csrfToken, idempotencyKey: `note-${op.key}` }, signal)
      op.candidateId = result.id
      if (result.status === "accepted") return
    }
    const result = await this.client.postEmpty(`/memory-candidates/${op.candidateId}/accept`, v => decodeCandidate(v, conversationId, op.candidateId), csrfToken, signal)
    if (result.status !== "accepted") fail()
  }
}

import { ApiClient } from "./client"

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function row(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("review_response_invalid")
  return value as Record<string, unknown>
}

export class RecentReviewApi {
  constructor(private readonly client = new ApiClient()) {}

  async start(profileId: string, role: "self" | "public_observed", operation: string, csrfToken: string, signal: AbortSignal) {
    const conversation = await this.client.postJson("/conversations", { player_profile_id: profileId }, value => {
      const v = row(value)
      if (v.schema_version !== "1.0" || v.relationship_id !== profileId
        || v.relationship_role !== (role === "self" ? "self" : "observed") || v.status !== "active"
        || typeof v.conversation_id !== "string" || !uuid.test(v.conversation_id)
        || !["created", "replayed"].includes(String(v.disposition))) throw new Error("review_response_invalid")
      return v.conversation_id
    }, { csrfToken, idempotencyKey: `${operation}-conversation` }, signal)
    return this.client.postJson(`/conversations/${conversation}/reviews/recent`,
      { count: 5, queue: 420, focus: "overall" }, value => {
        const v = row(value)
        if (v.schema_version !== "2.0" || v.conversation_id !== conversation
          || typeof v.task_id !== "string" || !uuid.test(v.task_id)
          || typeof v.run_id !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(v.run_id)
          || !["created", "replayed"].includes(String(v.disposition))
          || !["queued", "running", "recovery_required", "succeeded", "failed", "cancelled"].includes(String(v.status))) {
          throw new Error("review_response_invalid")
        }
        return { taskId: v.task_id, runId: v.run_id }
      }, { csrfToken, idempotencyKey: `${operation}-task` }, signal)
  }
}

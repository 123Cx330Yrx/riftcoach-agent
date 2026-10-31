import { ApiClient } from "./client"
import { decodeSessionAccounting } from "./decoders"
import type { SessionAccountingWire } from "./wire"

export interface TaskContinuation {
  readonly checkpoint: string
  readonly reason: string | null
  readonly accounting: SessionAccountingWire
}

function object(value: unknown, keys: readonly string[]): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("continuation_invalid")
  const row = value as Record<string, unknown>
  if (Object.keys(row).length !== keys.length || keys.some(key => !(key in row))) throw new Error("continuation_invalid")
  return row
}

export function decodeContinuation(value: unknown, taskId: string, runId: string): TaskContinuation {
  const row = object(value, ["task_id", "run_id", "status", "profile", "checkpoint_sha256", "reason", "session_accounting", "publication_allowed"])
  if (row.task_id !== taskId || row.run_id !== runId || row.status !== "recovery_required"
    || !["sol-dual-development-v1", "sol-dual-product-v1"].includes(String(row.profile)) || row.publication_allowed !== false
    || typeof row.checkpoint_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(row.checkpoint_sha256)
    || !(row.reason === null || typeof row.reason === "string" && /^[a-z0-9_]{1,128}$/.test(row.reason))) {
    throw new Error("continuation_invalid")
  }
  return { checkpoint: row.checkpoint_sha256, reason: row.reason, accounting: decodeSessionAccounting(row.session_accounting) }
}

export class TaskContinuationApi {
  constructor(private readonly client = new ApiClient()) {}

  get(taskId: string, runId: string, signal: AbortSignal) {
    return this.client.getJson(`/tasks/${encodeURIComponent(taskId)}/continuation`,
      value => decodeContinuation(value, taskId, runId), signal)
  }

  resume(taskId: string, runId: string, checkpoint: string, manualRetry: boolean, key: string, csrf: string, signal: AbortSignal) {
    return this.client.postJson(`/tasks/${encodeURIComponent(taskId)}/resume`,
      { checkpoint_sha256: checkpoint, manual_retry: manualRetry }, value => {
        const row = object(value, ["task_id", "run_id", "status", "replayed"])
        if (row.task_id !== taskId || row.run_id !== runId || typeof row.replayed !== "boolean"
          || !["queued", "running", "recovery_required", "succeeded", "failed", "cancelled"].includes(String(row.status))) throw new Error("continuation_invalid")
      }, { csrfToken: csrf, idempotencyKey: key }, signal)
  }

  cancel(taskId: string, key: string, csrf: string, signal: AbortSignal) {
    return this.client.postEmpty(`/tasks/${encodeURIComponent(taskId)}/cancel`, value => {
      const row = object(value, ["schema_version", "task_id", "disposition", "status"])
      if (row.schema_version !== "1.0" || row.task_id !== taskId
        || !["cancelled", "requested", "already_requested", "already_terminal", "recovery_required"].includes(String(row.disposition))
        || !["queued", "running", "recovery_required", "succeeded", "failed", "cancelled"].includes(String(row.status))) throw new Error("continuation_invalid")
    }, csrf, signal, key)
  }
}

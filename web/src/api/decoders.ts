import type {
  EvidenceClaimWire,
  EvidenceConfidenceWire,
  EvidenceDispositionWire,
  EvidenceFreshnessWire,
  EvidenceJoinKeyWire,
  EvidenceProjectionWire,
  EvidenceSnapshotWire,
  EvidenceSourceWire,
  AuthSessionWire,
  ExpectedTaskRunBinding,
  LatestProfileReviewWire,
  LatestReviewItemWire,
  PlayerProfilePageWire,
  PlayerProfileWire,
  ProductStateReasonWire,
  ProductStateValueWire,
  ProductStateWire,
  PublicationStatusWire,
  RecentAveragesWire,
  RecentMetricRowWire,
  RecentSummaryWire,
  RoutingRegionWire,
  RunWire,
  RunTimelineEventWire,
  RunTimelineMatchWire,
  RunTimelineWire,
  RuntimeUsageWire,
  TaskEventKindWire,
  TaskEventPageWire,
  TaskEventWire,
  TaskStatusWire,
  TaskWire,
  TrainingMetricSpecificationWire,
  TrainingMetricTrendWire,
  TrainingPlanPageWire,
  TrainingPlanWire,
  TrainingProgressPageWire,
  TrainingProgressWire,
} from "./wire"

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const DIGEST_PATTERN = /^[0-9a-f]{64}$/
const SAFE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
const SAFE_CODE_PATTERN = /^[a-z0-9]+(?:[._-][a-z0-9]+)*$/
const PATCH_PATTERN = /^[0-9]{1,3}\.[0-9]{1,3}(?:\.[0-9]{1,3})?$/
const TIMEZONE_PATTERN = /(?:Z|[+-][0-9]{2}:[0-9]{2})$/
const CONTROL_PATTERN = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/
const MAX_REPORT_BYTES = 1_048_576

type UnknownRecord = Record<string, unknown>

function record(value: unknown, path: string): UnknownRecord {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${path} must be an object`)
  }
  return value as UnknownRecord
}

function exact(value: UnknownRecord, keys: readonly string[], path: string): void {
  const expected = new Set(keys)
  for (const key of Object.keys(value)) {
    if (!expected.has(key)) {
      throw new Error(`${path} has unexpected key ${key}`)
    }
  }
  for (const key of keys) {
    if (!(key in value)) {
      throw new Error(`${path} is missing key ${key}`)
    }
  }
}

function string(value: unknown, path: string, max = 1_024): string {
  if (typeof value !== "string" || value.length < 1 || value.length > max || CONTROL_PATTERN.test(value)) {
    throw new Error(`${path} must be bounded text`)
  }
  return value
}

function normalizedText(value: unknown, path: string, max = 1_024): string {
  const result = string(value, path, max)
  if (result.trim() !== result) throw new Error(`${path} must be normalized text`)
  return result
}

function nullable<T>(value: unknown, decode: (item: unknown) => T): T | null {
  return value === null ? null : decode(value)
}

function bool(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${path} must be boolean`)
  return value
}

function number(value: unknown, path: string, options: { integer?: boolean; min?: number; max?: number } = {}): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${path} must be finite`)
  if (options.integer && !Number.isInteger(value)) throw new Error(`${path} must be an integer`)
  if (options.min !== undefined && value < options.min) throw new Error(`${path} is below minimum`)
  if (options.max !== undefined && value > options.max) throw new Error(`${path} exceeds maximum`)
  return value
}

function array<T>(value: unknown, path: string, decode: (item: unknown, index: number) => T, max = 100): readonly T[] {
  if (!Array.isArray(value) || value.length > max) throw new Error(`${path} must be a bounded array`)
  return value.map((item, index) => decode(item, index))
}

function enumeration<T extends string>(value: unknown, allowed: readonly T[], path: string): T {
  if (typeof value !== "string" || !allowed.includes(value as T)) throw new Error(`${path} has an unsupported value`)
  return value as T
}

function literal<T extends string>(value: unknown, expected: T, path: string): T {
  if (value !== expected) throw new Error(`${path} must be ${expected}`)
  return expected
}

function uuid(value: unknown, path: string): string {
  const result = string(value, path, 36)
  if (!UUID_PATTERN.test(result)) throw new Error(`${path} must be a UUID`)
  return result.toLowerCase()
}

function digest(value: unknown, path: string): string {
  const result = string(value, path, 64)
  if (!DIGEST_PATTERN.test(result)) throw new Error(`${path} must be a digest`)
  return result
}

function safeId(value: unknown, path: string): string {
  const result = string(value, path, 128)
  if (!SAFE_ID_PATTERN.test(result)) throw new Error(`${path} must be a safe identifier`)
  return result
}

function safeCode(value: unknown, path: string): string {
  const result = string(value, path, 64)
  if (!SAFE_CODE_PATTERN.test(result)) throw new Error(`${path} must be a safe code`)
  return result
}

function timestamp(value: unknown, path: string): string {
  const result = string(value, path, 64)
  if (!TIMEZONE_PATTERN.test(result) || !Number.isFinite(Date.parse(result))) {
    throw new Error(`${path} must be a timezone-aware timestamp`)
  }
  return result
}

export function decodeAuthSession(value: unknown): AuthSessionWire {
  const row = record(value, "auth_session")
  exact(row, ["schema_version", "csrf_token", "expires_at"], "auth_session")
  return {
    schema_version: literal(row.schema_version, "1.0", "auth_session.schema_version"),
    csrf_token: string(row.csrf_token, "auth_session.csrf_token", 256),
    expires_at: timestamp(row.expires_at, "auth_session.expires_at"),
  }
}

function patch(value: unknown, path: string): string {
  const result = string(value, path, 32)
  if (!PATCH_PATTERN.test(result)) throw new Error(`${path} must be a patch version`)
  return result
}

function taskStatus(value: unknown, path: string): TaskStatusWire {
  return enumeration(value, ["queued", "running", "recovery_required", "succeeded", "failed", "cancelled"], path)
}

function publication(value: unknown, path: string): PublicationStatusWire {
  return enumeration(value, ["published", "degraded", "rejected"], path)
}

function routingRegion(value: unknown, path: string): RoutingRegionWire {
  return enumeration(value, ["americas", "asia", "europe", "sea"], path)
}

function position(value: unknown, path: string) {
  return enumeration(value, ["top", "mid", "jungle", "adc", "support"] as const, path)
}

function decodeProfile(value: unknown, path: string): PlayerProfileWire {
  const row = record(value, path)
  exact(row, ["schema_version", "player_profile_id", "riot_id", "routing_region", "relationship_role", "verification_status", "last_resolved_at"], path)
  return {
    schema_version: literal(row.schema_version, "1.0", `${path}.schema_version`),
    player_profile_id: uuid(row.player_profile_id, `${path}.player_profile_id`),
    riot_id: normalizedText(row.riot_id, `${path}.riot_id`, 97),
    routing_region: routingRegion(row.routing_region, `${path}.routing_region`),
    relationship_role: enumeration(row.relationship_role, ["self", "observed"] as const, `${path}.relationship_role`),
    verification_status: enumeration(row.verification_status, ["unverified_claim", "not_applicable", "rso_verified"] as const, `${path}.verification_status`),
    last_resolved_at: timestamp(row.last_resolved_at, `${path}.last_resolved_at`),
  }
}

export function decodePlayerProfilePage(value: unknown): PlayerProfilePageWire {
  const row = record(value, "profiles")
  exact(row, ["schema_version", "profiles", "limit"], "profiles")
  const profiles = array(row.profiles, "profiles.profiles", (item, index) => decodeProfile(item, `profiles.profiles[${index}]`))
  const ids = profiles.map((item) => item.player_profile_id)
  if (new Set(ids).size !== ids.length) throw new Error("profiles contain duplicate identity")
  return {
    schema_version: literal(row.schema_version, "1.0", "profiles.schema_version"),
    profiles,
    limit: number(row.limit, "profiles.limit", { integer: true, min: 1, max: 100 }),
  }
}

export function decodeLatestProfileReview(value: unknown, expectedProfileId: string): LatestProfileReviewWire {
  const row = record(value, "latest")
  exact(row, ["schema_version", "player_profile_id", "latest_review"], "latest")
  const profileId = uuid(row.player_profile_id, "latest.player_profile_id")
  if (profileId !== uuid(expectedProfileId, "expected player profile")) throw new Error("profile binding mismatch")
  let latestReview: LatestReviewItemWire | null = null
  if (row.latest_review !== null) {
    const item = record(row.latest_review, "latest.latest_review")
    exact(item, ["task_id", "run_id", "status", "created_at", "updated_at", "publication_status", "report_available", "links"], "latest.latest_review")
    const taskId = uuid(item.task_id, "latest.latest_review.task_id")
    const runId = safeId(item.run_id, "latest.latest_review.run_id")
    const links = record(item.links, "latest.latest_review.links")
    exact(links, ["task", "events", "stream", "run", "summary", "timeline", "report", "product_state", "evidence"], "latest.latest_review.links")
    const expectedLinks = {
      task: `/tasks/${taskId}`,
      events: `/tasks/${taskId}/events`,
      stream: `/tasks/${taskId}/events/stream`,
      run: `/runs/${runId}`,
      summary: `/runs/${runId}/recent-summary`,
      timeline: `/runs/${runId}/timeline`,
      report: `/runs/${runId}/report`,
      product_state: `/runs/${runId}/product-state`,
      evidence: `/runs/${runId}/evidence`,
    } as const
    for (const [key, expected] of Object.entries(expectedLinks)) {
      if (links[key] !== expected) throw new Error(`latest link ${key} binding mismatch`)
    }
    latestReview = {
      task_id: taskId,
      run_id: runId,
      status: taskStatus(item.status, "latest.latest_review.status"),
      created_at: timestamp(item.created_at, "latest.latest_review.created_at"),
      updated_at: timestamp(item.updated_at, "latest.latest_review.updated_at"),
      publication_status: nullable(item.publication_status, (nested) => publication(nested, "latest.latest_review.publication_status")),
      report_available: bool(item.report_available, "latest.latest_review.report_available"),
      links: expectedLinks,
    }
  }
  return {
    schema_version: literal(row.schema_version, "1.0", "latest.schema_version"),
    player_profile_id: profileId,
    latest_review: latestReview,
  }
}

function assertBinding(taskId: string, runId: string, expected: ExpectedTaskRunBinding): void {
  if (taskId !== uuid(expected.taskId, "expected task")) throw new Error("task binding mismatch")
  if (runId !== safeId(expected.runId, "expected run")) throw new Error("run binding mismatch")
}

export function decodeTask(value: unknown, expected: ExpectedTaskRunBinding): TaskWire {
  const row = record(value, "task")
  exact(row, ["schema_version", "task_id", "run_id", "status", "created_at", "updated_at", "claimed_at", "finished_at", "terminal_reason", "publication_status", "report_available"], "task")
  const taskId = uuid(row.task_id, "task.task_id")
  const runId = safeId(row.run_id, "task.run_id")
  assertBinding(taskId, runId, expected)
  return {
    schema_version: enumeration(row.schema_version, ["1.0", "2.0"] as const, "task.schema_version"),
    task_id: taskId,
    run_id: runId,
    status: taskStatus(row.status, "task.status"),
    created_at: timestamp(row.created_at, "task.created_at"),
    updated_at: timestamp(row.updated_at, "task.updated_at"),
    claimed_at: nullable(row.claimed_at, (item) => timestamp(item, "task.claimed_at")),
    finished_at: nullable(row.finished_at, (item) => timestamp(item, "task.finished_at")),
    terminal_reason: nullable(row.terminal_reason, (item) => safeCode(item, "task.terminal_reason")),
    publication_status: nullable(row.publication_status, (item) => publication(item, "task.publication_status")),
    report_available: bool(row.report_available, "task.report_available"),
  }
}

export function decodeTaskEvent(value: unknown, expected: ExpectedTaskRunBinding, path = "event"): TaskEventWire {
  const row = record(value, path)
  exact(row, ["event_schema_version", "event_cursor", "event_identity", "task_id", "run_id", "task_sequence", "event_kind", "status_after", "lease_generation", "reason", "occurred_at"], path)
  const taskId = uuid(row.task_id, `${path}.task_id`)
  const runId = safeId(row.run_id, `${path}.run_id`)
  assertBinding(taskId, runId, expected)
  return {
    event_schema_version: literal(row.event_schema_version, "1.0", `${path}.event_schema_version`),
    event_cursor: number(row.event_cursor, `${path}.event_cursor`, { integer: true, min: 1 }),
    event_identity: digest(row.event_identity, `${path}.event_identity`),
    task_id: taskId,
    run_id: runId,
    task_sequence: number(row.task_sequence, `${path}.task_sequence`, { integer: true, min: 1 }),
    event_kind: enumeration(row.event_kind, ["created", "claimed", "execution_started", "heartbeat", "cancel_requested", "checkpoint_saved", "recovery_required", "requeued", "succeeded", "failed", "cancelled"] as const, `${path}.event_kind`) as TaskEventKindWire,
    status_after: taskStatus(row.status_after, `${path}.status_after`),
    lease_generation: number(row.lease_generation, `${path}.lease_generation`, { integer: true, min: 0 }),
    reason: nullable(row.reason, (item) => safeCode(item, `${path}.reason`)),
    occurred_at: timestamp(row.occurred_at, `${path}.occurred_at`),
  }
}

export function decodeTaskEventPage(value: unknown, expected: ExpectedTaskRunBinding): TaskEventPageWire {
  const row = record(value, "events")
  exact(row, ["schema_version", "task_id", "after_cursor", "next_cursor", "limit", "has_more", "events"], "events")
  const taskId = uuid(row.task_id, "events.task_id")
  if (taskId !== uuid(expected.taskId, "expected task")) throw new Error("task binding mismatch")
  const events = array(row.events, "events.events", (item, index) => decodeTaskEvent(item, expected, `events.events[${index}]`))
  let previous = number(row.after_cursor, "events.after_cursor", { integer: true, min: 0 })
  for (const event of events) {
    if (event.event_cursor <= previous) throw new Error("event cursor must increase")
    previous = event.event_cursor
  }
  const nextCursor = number(row.next_cursor, "events.next_cursor", { integer: true, min: 0 })
  if (nextCursor < previous) throw new Error("next cursor precedes events")
  return {
    schema_version: literal(row.schema_version, "1.0", "events.schema_version"),
    task_id: taskId,
    after_cursor: number(row.after_cursor, "events.after_cursor", { integer: true, min: 0 }),
    next_cursor: nextCursor,
    limit: number(row.limit, "events.limit", { integer: true, min: 1, max: 100 }),
    has_more: bool(row.has_more, "events.has_more"),
    events,
  }
}

export function decodeProductState(value: unknown, expected: ExpectedTaskRunBinding): ProductStateWire {
  const row = record(value, "product_state")
  exact(row, ["schema_version", "task_id", "run_id", "state", "reason_code", "task_status", "publication_status", "report_available", "evidence_revision", "evidence_bundle_digest", "evidence_freshness", "evidence_disposition"], "product_state")
  const taskId = uuid(row.task_id, "product_state.task_id")
  const runId = safeId(row.run_id, "product_state.run_id")
  assertBinding(taskId, runId, expected)
  return {
    schema_version: literal(row.schema_version, "1.0", "product_state.schema_version"),
    task_id: taskId,
    run_id: runId,
    state: enumeration(row.state, ["published", "degraded", "rejected", "not_ready"] as const, "product_state.state") as ProductStateValueWire,
    reason_code: enumeration(row.reason_code, ["ready", "task_pending", "recovery_required", "task_failed", "task_cancelled", "quality_rejected", "quality_degraded", "evidence_not_available", "evidence_expired", "evidence_degraded", "evidence_rejected"] as const, "product_state.reason_code") as ProductStateReasonWire,
    task_status: taskStatus(row.task_status, "product_state.task_status"),
    publication_status: nullable(row.publication_status, (item) => publication(item, "product_state.publication_status")),
    report_available: bool(row.report_available, "product_state.report_available"),
    evidence_revision: nullable(row.evidence_revision, (item) => number(item, "product_state.evidence_revision", { integer: true, min: 1 })),
    evidence_bundle_digest: nullable(row.evidence_bundle_digest, (item) => digest(item, "product_state.evidence_bundle_digest")),
    evidence_freshness: nullable(row.evidence_freshness, (item) => enumeration(item, ["current", "expired"] as const, "product_state.evidence_freshness")),
    evidence_disposition: nullable(row.evidence_disposition, (item) => evidenceDisposition(item, "product_state.evidence_disposition")),
  }
}

function decodeUsage(value: unknown): RuntimeUsageWire {
  const row = record(value, "run.usage")
  exact(row, ["provider_calls_attempted", "provider_responses_observed", "observed_input_tokens", "observed_output_tokens", "input_tokens", "output_tokens", "token_observation", "tool_calls", "tool_attempts", "tool_latency_ms", "cost", "currency", "pricing_profile_id", "pricing_profile_version", "cost_observation"], "run.usage")
  return {
    provider_calls_attempted: number(row.provider_calls_attempted, "run.usage.provider_calls_attempted", { integer: true, min: 0 }),
    provider_responses_observed: number(row.provider_responses_observed, "run.usage.provider_responses_observed", { integer: true, min: 0 }),
    observed_input_tokens: number(row.observed_input_tokens, "run.usage.observed_input_tokens", { integer: true, min: 0 }),
    observed_output_tokens: number(row.observed_output_tokens, "run.usage.observed_output_tokens", { integer: true, min: 0 }),
    input_tokens: nullable(row.input_tokens, (item) => number(item, "run.usage.input_tokens", { integer: true, min: 0 })),
    output_tokens: nullable(row.output_tokens, (item) => number(item, "run.usage.output_tokens", { integer: true, min: 0 })),
    token_observation: enumeration(row.token_observation, ["complete", "partial", "unknown", "not_applicable"] as const, "run.usage.token_observation"),
    tool_calls: number(row.tool_calls, "run.usage.tool_calls", { integer: true, min: 0 }),
    tool_attempts: number(row.tool_attempts, "run.usage.tool_attempts", { integer: true, min: 0 }),
    tool_latency_ms: number(row.tool_latency_ms, "run.usage.tool_latency_ms", { min: 0 }),
    cost: nullable(row.cost, (item) => normalizedText(item, "run.usage.cost", 64)),
    currency: nullable(row.currency, (item) => normalizedText(item, "run.usage.currency", 3)),
    pricing_profile_id: nullable(row.pricing_profile_id, (item) => safeId(item, "run.usage.pricing_profile_id")),
    pricing_profile_version: nullable(row.pricing_profile_version, (item) => normalizedText(item, "run.usage.pricing_profile_version", 32)),
    cost_observation: enumeration(row.cost_observation, ["complete", "partial", "unknown", "not_configured"] as const, "run.usage.cost_observation"),
  }
}

export function decodeRun(value: unknown, expectedRunId: string): RunWire {
  const row = record(value, "run")
  exact(row, ["schema_version", "run_id", "runtime_status", "publication_status", "terminal_reason", "skill_name", "skill_version", "prompt_profile_id", "prompt_profile_version", "started_at_utc", "completed_at_utc", "elapsed_ms", "usage", "report_available"], "run")
  const runId = safeId(row.run_id, "run.run_id")
  if (runId !== safeId(expectedRunId, "expected run")) throw new Error("run binding mismatch")
  return {
    schema_version: literal(row.schema_version, "1.0", "run.schema_version"),
    run_id: runId,
    runtime_status: enumeration(row.runtime_status, ["completed", "failed"] as const, "run.runtime_status"),
    publication_status: nullable(row.publication_status, (item) => publication(item, "run.publication_status")),
    terminal_reason: safeCode(row.terminal_reason, "run.terminal_reason"),
    skill_name: nullable(row.skill_name, (item) => safeId(item, "run.skill_name")),
    skill_version: nullable(row.skill_version, (item) => normalizedText(item, "run.skill_version", 32)),
    prompt_profile_id: nullable(row.prompt_profile_id, (item) => safeId(item, "run.prompt_profile_id")),
    prompt_profile_version: nullable(row.prompt_profile_version, (item) => normalizedText(item, "run.prompt_profile_version", 32)),
    started_at_utc: nullable(row.started_at_utc, (item) => timestamp(item, "run.started_at_utc")),
    completed_at_utc: nullable(row.completed_at_utc, (item) => timestamp(item, "run.completed_at_utc")),
    elapsed_ms: nullable(row.elapsed_ms, (item) => number(item, "run.elapsed_ms", { integer: true, min: 0 })),
    usage: nullable(row.usage, decodeUsage),
    report_available: bool(row.report_available, "run.report_available"),
  }
}

function metricRow(value: unknown, path: string): RecentMetricRowWire {
  const row = record(value, path)
  exact(row, ["cs_per_min", "gold_per_min", "damage_per_min", "vision_score", "deaths_before_15"], path)
  return {
    cs_per_min: number(row.cs_per_min, `${path}.cs_per_min`, { min: 0 }),
    gold_per_min: number(row.gold_per_min, `${path}.gold_per_min`, { min: 0 }),
    damage_per_min: number(row.damage_per_min, `${path}.damage_per_min`, { min: 0 }),
    vision_score: number(row.vision_score, `${path}.vision_score`, { min: 0 }),
    deaths_before_15: number(row.deaths_before_15, `${path}.deaths_before_15`, { min: 0 }),
  }
}

function averages(value: unknown): RecentAveragesWire {
  const row = record(value, "summary.averages")
  exact(row, ["kda", "cs_per_min", "gold_per_min", "damage_per_min", "vision_score", "kill_participation_percent", "damage_share_percent", "gold_share_percent", "deaths_before_15"], "summary.averages")
  return {
    ...metricRow({ cs_per_min: row.cs_per_min, gold_per_min: row.gold_per_min, damage_per_min: row.damage_per_min, vision_score: row.vision_score, deaths_before_15: row.deaths_before_15 }, "summary.averages.metrics"),
    kda: number(row.kda, "summary.averages.kda", { min: 0 }),
    kill_participation_percent: number(row.kill_participation_percent, "summary.averages.kill_participation_percent", { min: 0, max: 100 }),
    damage_share_percent: number(row.damage_share_percent, "summary.averages.damage_share_percent", { min: 0, max: 100 }),
    gold_share_percent: number(row.gold_share_percent, "summary.averages.gold_share_percent", { min: 0, max: 100 }),
  }
}

export function decodeRecentSummary(value: unknown, expectedRunId: string): RecentSummaryWire {
  const row = record(value, "summary")
  exact(row, ["schema_version", "run_id", "skill_name", "skill_version", "runtime_status", "publication_status", "terminal_reason", "report_available", "games_analyzed", "wins", "losses", "win_rate", "main_role", "main_champions", "averages", "win_loss_comparison"], "summary")
  const runId = safeId(row.run_id, "summary.run_id")
  if (runId !== safeId(expectedRunId, "expected run")) throw new Error("run binding mismatch")
  const games = number(row.games_analyzed, "summary.games_analyzed", { integer: true, min: 1, max: 100 })
  const wins = number(row.wins, "summary.wins", { integer: true, min: 0, max: 100 })
  const losses = number(row.losses, "summary.losses", { integer: true, min: 0, max: 100 })
  const winRate = number(row.win_rate, "summary.win_rate", { min: 0, max: 100 })
  if (wins + losses !== games || Math.abs(winRate - Math.round((wins / games) * 1_000) / 10) > 0.05) throw new Error("summary win/loss math mismatch")
  const comparison = record(row.win_loss_comparison, "summary.win_loss_comparison")
  exact(comparison, ["wins", "losses"], "summary.win_loss_comparison")
  return {
    schema_version: literal(row.schema_version, "1.0", "summary.schema_version"),
    run_id: runId,
    skill_name: literal(row.skill_name, "recent-form-review", "summary.skill_name"),
    skill_version: normalizedText(row.skill_version, "summary.skill_version", 32),
    runtime_status: literal(row.runtime_status, "completed", "summary.runtime_status"),
    publication_status: enumeration(row.publication_status, ["published", "degraded"] as const, "summary.publication_status"),
    terminal_reason: safeCode(row.terminal_reason, "summary.terminal_reason"),
    report_available: row.report_available === true ? true : (() => { throw new Error("summary.report_available must be true") })(),
    games_analyzed: games,
    wins,
    losses,
    win_rate: winRate,
    main_role: normalizedText(row.main_role, "summary.main_role", 64),
    main_champions: array(row.main_champions, "summary.main_champions", (item, index) => normalizedText(item, `summary.main_champions[${index}]`, 64), 5),
    averages: averages(row.averages),
    win_loss_comparison: {
      wins: metricRow(comparison.wins, "summary.win_loss_comparison.wins"),
      losses: metricRow(comparison.losses, "summary.win_loss_comparison.losses"),
    },
  }
}

function decodeTimelineEvent(value: unknown, path: string): RunTimelineEventWire {
  const row = record(value, path)
  exact(row, ["event_kind", "at_seconds", "phase", "label", "item_id"], path)
  const atSeconds = number(row.at_seconds, `${path}.at_seconds`, { integer: true, min: 0, max: 86_400 })
  const phase = enumeration(row.phase, ["early", "mid", "late"] as const, `${path}.phase`)
  const expectedPhase = atSeconds < 900 ? "early" : atSeconds < 1500 ? "mid" : "late"
  if (phase !== expectedPhase) throw new Error(`${path}.phase disagrees with at_seconds`)
  const eventKind = enumeration(row.event_kind, ["death", "item_purchase", "objective"] as const, `${path}.event_kind`)
  const itemId = nullable(row.item_id, (item) => number(item, `${path}.item_id`, { integer: true, min: 1, max: 999_999 }))
  if (eventKind !== "item_purchase" && itemId !== null) throw new Error(`${path}.item_id belongs only to purchases`)
  return {
    event_kind: eventKind,
    at_seconds: atSeconds,
    phase,
    label: normalizedText(row.label, `${path}.label`, 96),
    item_id: itemId,
  }
}

function decodeTimelineMatch(value: unknown, index: number): RunTimelineMatchWire {
  const path = `timeline.matches[${index}]`
  const row = record(value, path)
  exact(row, ["match_id", "champion_name", "role", "win", "game_duration_seconds", "included_in_aggregate", "timeline_status", "unavailable_reason", "total_events", "projected_events", "events_truncated", "events"], path)
  const status = enumeration(row.timeline_status, ["available", "unavailable"] as const, `${path}.timeline_status`)
  const reason = nullable(row.unavailable_reason, (item) => literal(item, "source_unavailable", `${path}.unavailable_reason`))
  const totalEvents = number(row.total_events, `${path}.total_events`, { integer: true, min: 0, max: 100_000 })
  const projectedEvents = number(row.projected_events, `${path}.projected_events`, { integer: true, min: 0, max: 128 })
  const gameDurationSeconds = number(row.game_duration_seconds, `${path}.game_duration_seconds`, { integer: true, min: 1, max: 86_400 })
  const events = array(row.events, `${path}.events`, (item, eventIndex) => decodeTimelineEvent(item, `${path}.events[${eventIndex}]`), 128)
  if (projectedEvents !== events.length) throw new Error(`${path} event count mismatch`)
  const truncated = bool(row.events_truncated, `${path}.events_truncated`)
  if (truncated !== (totalEvents > projectedEvents)) throw new Error(`${path} truncation mismatch`)
  if (status === "available" && reason !== null) throw new Error(`${path} available timeline has a reason`)
  if (status === "unavailable" && (reason === null || totalEvents !== 0 || events.length !== 0)) {
    throw new Error(`${path} unavailable timeline projects events`)
  }
  for (let eventIndex = 1; eventIndex < events.length; eventIndex += 1) {
    if (events[eventIndex]!.at_seconds < events[eventIndex - 1]!.at_seconds) {
      throw new Error(`${path}.events must be chronological`)
    }
  }
  if (events.some((event) => event.at_seconds > gameDurationSeconds)) {
    throw new Error(`${path}.events exceed the verified match duration`)
  }
  return {
    match_id: safeId(row.match_id, `${path}.match_id`),
    champion_name: normalizedText(row.champion_name, `${path}.champion_name`, 64),
    role: normalizedText(row.role, `${path}.role`, 64),
    win: bool(row.win, `${path}.win`),
    game_duration_seconds: gameDurationSeconds,
    included_in_aggregate: bool(row.included_in_aggregate, `${path}.included_in_aggregate`),
    timeline_status: status,
    unavailable_reason: reason,
    total_events: totalEvents,
    projected_events: projectedEvents,
    events_truncated: truncated,
    events,
  }
}

export function decodeRunTimeline(value: unknown, expectedRunId: string): RunTimelineWire {
  const row = record(value, "timeline")
  exact(row, ["schema_version", "run_id", "skill_name", "skill_version", "runtime_status", "publication_status", "terminal_reason", "source", "timeline_status", "total_matches", "projected_matches", "matches_truncated", "matches"], "timeline")
  const runId = safeId(row.run_id, "timeline.run_id")
  if (runId !== safeId(expectedRunId, "expected timeline run_id")) throw new Error("timeline run binding mismatch")
  const totalMatches = number(row.total_matches, "timeline.total_matches", { integer: true, min: 1, max: 100 })
  const projectedMatches = number(row.projected_matches, "timeline.projected_matches", { integer: true, min: 1, max: 20 })
  const matches = array(row.matches, "timeline.matches", decodeTimelineMatch, 20)
  if (projectedMatches !== matches.length) throw new Error("timeline match count mismatch")
  if (new Set(matches.map((match) => match.match_id)).size !== matches.length) throw new Error("timeline match ids must be unique")
  const matchesTruncated = bool(row.matches_truncated, "timeline.matches_truncated")
  if (matchesTruncated !== (totalMatches > projectedMatches)) throw new Error("timeline match truncation mismatch")
  const status = enumeration(row.timeline_status, ["available", "partial", "unavailable"] as const, "timeline.timeline_status")
  if (!matchesTruncated) {
    const available = matches.filter((match) => match.timeline_status === "available").length
    const expectedStatus = available === matches.length ? "available" : available === 0 ? "unavailable" : "partial"
    if (status !== expectedStatus) throw new Error("timeline status disagrees with match availability")
  }
  return {
    schema_version: literal(row.schema_version, "1.0", "timeline.schema_version"),
    run_id: runId,
    skill_name: literal(row.skill_name, "recent-form-review", "timeline.skill_name"),
    skill_version: normalizedText(row.skill_version, "timeline.skill_version", 32),
    runtime_status: literal(row.runtime_status, "completed", "timeline.runtime_status"),
    publication_status: enumeration(row.publication_status, ["published", "degraded"] as const, "timeline.publication_status"),
    terminal_reason: safeCode(row.terminal_reason, "timeline.terminal_reason"),
    source: literal(row.source, "riot_match_v5_timeline", "timeline.source"),
    timeline_status: status,
    total_matches: totalMatches,
    projected_matches: projectedMatches,
    matches_truncated: matchesTruncated,
    matches,
  }
}

export function decodeReport(value: unknown): string {
  if (typeof value !== "string") throw new Error("report must be text")
  if (new TextEncoder().encode(value).byteLength > MAX_REPORT_BYTES) throw new Error("report exceeds size limit")
  if (!value.trim() || CONTROL_PATTERN.test(value)) throw new Error("report contains invalid control text")
  return value
}

function evidenceDisposition(value: unknown, path: string): EvidenceDispositionWire {
  return enumeration(value, ["complete", "degraded", "rejected"] as const, path)
}

function evidenceConfidence(value: unknown, path: string): EvidenceConfidenceWire {
  return enumeration(value, ["high", "medium", "low", "unknown"] as const, path)
}

function evidenceFreshness(value: unknown, path: string): EvidenceFreshnessWire {
  return enumeration(value, ["current", "stale", "unknown", "expired"] as const, path)
}

function evidenceClaim(value: unknown, path: string): EvidenceClaimWire {
  return enumeration(value, ["riot_match_facts", "data_dragon_static", "official_patch_facts", "current_meta_recommendation", "exact_patch_meta_comparison"] as const, path)
}

function evidenceSource(value: unknown, path: string): EvidenceSourceWire {
  return enumeration(value, ["riot_official", "data_dragon", "riot_patch", "opgg"] as const, path)
}

function joinKey(value: unknown, path: string): EvidenceJoinKeyWire {
  const row = record(value, path)
  exact(row, ["routing_region", "queue_id", "position", "champion_name", "patch_version"], path)
  return {
    routing_region: normalizedText(row.routing_region, `${path}.routing_region`, 16),
    queue_id: number(row.queue_id, `${path}.queue_id`, { integer: true, min: 1, max: 10_000 }),
    position: position(row.position, `${path}.position`),
    champion_name: normalizedText(row.champion_name, `${path}.champion_name`, 64),
    patch_version: nullable(row.patch_version, (item) => patch(item, `${path}.patch_version`)),
  }
}

function projection(value: unknown): EvidenceProjectionWire {
  const row = record(value, "evidence.projection")
  exact(row, ["schema_version", "bundle_digest", "disposition", "confidence", "claims", "matches", "joins", "conflicts", "gaps", "sources"], "evidence.projection")
  const sources = record(row.sources, "evidence.projection.sources")
  exact(sources, ["riot_official", "data_dragon", "riot_patch", "opgg"], "evidence.projection.sources")
  const riot = record(sources.riot_official, "evidence.projection.sources.riot_official")
  exact(riot, ["match_count", "digests", "freshness"], "evidence.projection.sources.riot_official")
  const dataDragon = record(sources.data_dragon, "evidence.projection.sources.data_dragon")
  exact(dataDragon, ["version", "catalog_digest", "freshness"], "evidence.projection.sources.data_dragon")
  const riotPatch = record(sources.riot_patch, "evidence.projection.sources.riot_patch")
  exact(riotPatch, ["patch_version", "source_digest", "freshness"], "evidence.projection.sources.riot_patch")
  const opgg = record(sources.opgg, "evidence.projection.sources.opgg")
  exact(opgg, ["evidence_count", "digests", "provenance", "freshness"], "evidence.projection.sources.opgg")
  const matches = array(row.matches, "evidence.projection.matches", (item, index) => {
    const match = record(item, `evidence.projection.matches[${index}]`)
    exact(match, ["match_id", "champion_name", "position", "patch_version", "win", "timeline_available"], `evidence.projection.matches[${index}]`)
    return {
      match_id: safeId(match.match_id, `evidence.projection.matches[${index}].match_id`),
      champion_name: normalizedText(match.champion_name, `evidence.projection.matches[${index}].champion_name`, 64),
      position: position(match.position, `evidence.projection.matches[${index}].position`),
      patch_version: nullable(match.patch_version, (nested) => patch(nested, `evidence.projection.matches[${index}].patch_version`)),
      win: bool(match.win, `evidence.projection.matches[${index}].win`),
      timeline_available: bool(match.timeline_available, `evidence.projection.matches[${index}].timeline_available`),
    }
  })
  const joins = array(row.joins, "evidence.projection.joins", (item, index) => {
    const join = record(item, `evidence.projection.joins[${index}]`)
    exact(join, ["key", "status", "confidence", "sources_present"], `evidence.projection.joins[${index}]`)
    const present = record(join.sources_present, `evidence.projection.joins[${index}].sources_present`)
    exact(present, ["riot", "data_dragon", "riot_patch", "opgg"], `evidence.projection.joins[${index}].sources_present`)
    return {
      key: joinKey(join.key, `evidence.projection.joins[${index}].key`),
      status: enumeration(join.status, ["joined", "joined_partial", "unjoined", "stale", "conflict"] as const, `evidence.projection.joins[${index}].status`),
      confidence: evidenceConfidence(join.confidence, `evidence.projection.joins[${index}].confidence`),
      sources_present: {
        riot: bool(present.riot, `evidence.projection.joins[${index}].sources_present.riot`),
        data_dragon: bool(present.data_dragon, `evidence.projection.joins[${index}].sources_present.data_dragon`),
        riot_patch: bool(present.riot_patch, `evidence.projection.joins[${index}].sources_present.riot_patch`),
        opgg: bool(present.opgg, `evidence.projection.joins[${index}].sources_present.opgg`),
      },
    }
  })
  if (matches.length !== joins.length) throw new Error("evidence projection join cardinality mismatch")
  const conflicts = array(row.conflicts, "evidence.projection.conflicts", (item, index) => {
    const conflict = record(item, `evidence.projection.conflicts[${index}]`)
    exact(conflict, ["code", "sources", "key"], `evidence.projection.conflicts[${index}]`)
    return {
      code: safeCode(conflict.code, `evidence.projection.conflicts[${index}].code`),
      sources: array(conflict.sources, `evidence.projection.conflicts[${index}].sources`, (nested, sourceIndex) => evidenceSource(nested, `evidence.projection.conflicts[${index}].sources[${sourceIndex}]`), 4),
      key: nullable(conflict.key, (nested) => joinKey(nested, `evidence.projection.conflicts[${index}].key`)),
    }
  })
  const gaps = array(row.gaps, "evidence.projection.gaps", (item, index) => {
    const gap = record(item, `evidence.projection.gaps[${index}]`)
    exact(gap, ["code", "source", "key"], `evidence.projection.gaps[${index}]`)
    return {
      code: safeCode(gap.code, `evidence.projection.gaps[${index}].code`),
      source: evidenceSource(gap.source, `evidence.projection.gaps[${index}].source`),
      key: nullable(gap.key, (nested) => joinKey(nested, `evidence.projection.gaps[${index}].key`)),
    }
  })
  return {
    schema_version: literal(row.schema_version, "1.0", "evidence.projection.schema_version"),
    bundle_digest: digest(row.bundle_digest, "evidence.projection.bundle_digest"),
    disposition: evidenceDisposition(row.disposition, "evidence.projection.disposition"),
    confidence: evidenceConfidence(row.confidence, "evidence.projection.confidence"),
    claims: array(row.claims, "evidence.projection.claims", (item, index) => evidenceClaim(item, `evidence.projection.claims[${index}]`), 5),
    matches,
    joins,
    conflicts,
    gaps,
    sources: {
      riot_official: {
        match_count: number(riot.match_count, "evidence.projection.sources.riot_official.match_count", { integer: true, min: 0, max: 100 }),
        digests: array(riot.digests, "evidence.projection.sources.riot_official.digests", (item, index) => digest(item, `evidence.projection.sources.riot_official.digests[${index}]`)),
        freshness: evidenceFreshness(riot.freshness, "evidence.projection.sources.riot_official.freshness"),
      },
      data_dragon: {
        version: nullable(dataDragon.version, (item) => patch(item, "evidence.projection.sources.data_dragon.version")),
        catalog_digest: nullable(dataDragon.catalog_digest, (item) => digest(item, "evidence.projection.sources.data_dragon.catalog_digest")),
        freshness: evidenceFreshness(dataDragon.freshness, "evidence.projection.sources.data_dragon.freshness"),
      },
      riot_patch: {
        patch_version: nullable(riotPatch.patch_version, (item) => patch(item, "evidence.projection.sources.riot_patch.patch_version")),
        source_digest: nullable(riotPatch.source_digest, (item) => digest(item, "evidence.projection.sources.riot_patch.source_digest")),
        freshness: evidenceFreshness(riotPatch.freshness, "evidence.projection.sources.riot_patch.freshness"),
      },
      opgg: {
        evidence_count: number(opgg.evidence_count, "evidence.projection.sources.opgg.evidence_count", { integer: true, min: 0, max: 100 }),
        digests: array(opgg.digests, "evidence.projection.sources.opgg.digests", (item, index) => digest(item, `evidence.projection.sources.opgg.digests[${index}]`)),
        provenance: array(opgg.provenance, "evidence.projection.sources.opgg.provenance", (item, index) => enumeration(item, ["complete", "partial"] as const, `evidence.projection.sources.opgg.provenance[${index}]`)),
        freshness: evidenceFreshness(opgg.freshness, "evidence.projection.sources.opgg.freshness"),
      },
    },
  }
}

export function decodeEvidence(value: unknown, expected: ExpectedTaskRunBinding): EvidenceSnapshotWire {
  const row = record(value, "evidence")
  exact(row, ["schema_version", "snapshot_id", "task_id", "run_id", "revision", "bundle_digest", "snapshot_digest", "stored_at", "expires_at", "freshness", "bundle_disposition", "confidence", "usable_claims", "projection"], "evidence")
  const taskId = uuid(row.task_id, "evidence.task_id")
  const runId = safeId(row.run_id, "evidence.run_id")
  assertBinding(taskId, runId, expected)
  const decodedProjection = projection(row.projection)
  const bundleDigest = digest(row.bundle_digest, "evidence.bundle_digest")
  const disposition = evidenceDisposition(row.bundle_disposition, "evidence.bundle_disposition")
  const confidence = evidenceConfidence(row.confidence, "evidence.confidence")
  if (decodedProjection.bundle_digest !== bundleDigest || decodedProjection.disposition !== disposition || decodedProjection.confidence !== confidence) throw new Error("evidence projection identity mismatch")
  return {
    schema_version: literal(row.schema_version, "1.0", "evidence.schema_version"),
    snapshot_id: uuid(row.snapshot_id, "evidence.snapshot_id"),
    task_id: taskId,
    run_id: runId,
    revision: number(row.revision, "evidence.revision", { integer: true, min: 1 }),
    bundle_digest: bundleDigest,
    snapshot_digest: digest(row.snapshot_digest, "evidence.snapshot_digest"),
    stored_at: timestamp(row.stored_at, "evidence.stored_at"),
    expires_at: nullable(row.expires_at, (item) => timestamp(item, "evidence.expires_at")),
    freshness: enumeration(row.freshness, ["current", "expired"] as const, "evidence.freshness"),
    bundle_disposition: disposition,
    confidence,
    usable_claims: array(row.usable_claims, "evidence.usable_claims", (item, index) => evidenceClaim(item, `evidence.usable_claims[${index}]`), 5),
    projection: decodedProjection,
  }
}

function metricSpec(value: unknown, path: string): TrainingMetricSpecificationWire {
  const row = record(value, path)
  const required = ["metric_key", "direction", "unit", "stable_tolerance"]
  const allowed = [...required, "baseline", "target"]
  for (const key of Object.keys(row)) if (!allowed.includes(key)) throw new Error(`${path} has unexpected key ${key}`)
  for (const key of required) if (!(key in row)) throw new Error(`${path} is missing key ${key}`)
  const result: TrainingMetricSpecificationWire = {
    metric_key: safeId(row.metric_key, `${path}.metric_key`),
    direction: enumeration(row.direction, ["increase", "decrease", "maintain"] as const, `${path}.direction`),
    unit: enumeration(row.unit, ["count", "ratio", "percent", "seconds", "score"] as const, `${path}.unit`),
    stable_tolerance: number(row.stable_tolerance, `${path}.stable_tolerance`, { min: 0 }),
    ...(row.baseline === undefined ? {} : { baseline: number(row.baseline, `${path}.baseline`) }),
    ...(row.target === undefined ? {} : { target: number(row.target, `${path}.target`) }),
  }
  return result
}

function trainingPlan(value: unknown, path: string, expectedRelationshipId: string): TrainingPlanWire {
  const row = record(value, path)
  exact(row, ["schema_version", "plan_id", "relationship_id", "version", "status", "payload", "supersedes_plan_id", "created_at", "updated_at"], path)
  const relationshipId = uuid(row.relationship_id, `${path}.relationship_id`)
  if (relationshipId !== uuid(expectedRelationshipId, "expected relationship")) throw new Error("training relationship binding mismatch")
  const payload = record(row.payload, `${path}.payload`)
  exact(payload, ["title", "objective", "metrics"], `${path}.payload`)
  return {
    schema_version: literal(row.schema_version, "1.0", `${path}.schema_version`),
    plan_id: uuid(row.plan_id, `${path}.plan_id`),
    relationship_id: relationshipId,
    version: number(row.version, `${path}.version`, { integer: true, min: 1 }),
    status: enumeration(row.status, ["active", "completed", "abandoned", "superseded"] as const, `${path}.status`),
    payload: {
      title: normalizedText(payload.title, `${path}.payload.title`, 120),
      objective: normalizedText(payload.objective, `${path}.payload.objective`, 1_000),
      metrics: array(payload.metrics, `${path}.payload.metrics`, (item, index) => metricSpec(item, `${path}.payload.metrics[${index}]`), 8),
    },
    supersedes_plan_id: nullable(row.supersedes_plan_id, (item) => uuid(item, `${path}.supersedes_plan_id`)),
    created_at: timestamp(row.created_at, `${path}.created_at`),
    updated_at: timestamp(row.updated_at, `${path}.updated_at`),
  }
}

export function decodeTrainingPlanPage(value: unknown, expectedRelationshipId: string): TrainingPlanPageWire {
  const row = record(value, "training_plans")
  exact(row, ["schema_version", "plans"], "training_plans")
  return {
    schema_version: literal(row.schema_version, "1.0", "training_plans.schema_version"),
    plans: array(row.plans, "training_plans.plans", (item, index) => trainingPlan(item, `training_plans.plans[${index}]`, expectedRelationshipId)),
  }
}

function trainingProgress(value: unknown, path: string, expectedRelationshipId: string): TrainingProgressWire {
  const row = record(value, path)
  exact(row, ["schema_version", "progress_id", "plan_id", "relationship_id", "metric_key", "metric_value", "observed_at", "source_run_id", "source_artifact_sha256", "status", "supersedes_progress_id", "created_at", "updated_at"], path)
  const relationshipId = uuid(row.relationship_id, `${path}.relationship_id`)
  if (relationshipId !== uuid(expectedRelationshipId, "expected relationship")) throw new Error("training relationship binding mismatch")
  return {
    schema_version: literal(row.schema_version, "1.0", `${path}.schema_version`),
    progress_id: uuid(row.progress_id, `${path}.progress_id`),
    plan_id: uuid(row.plan_id, `${path}.plan_id`),
    relationship_id: relationshipId,
    metric_key: safeId(row.metric_key, `${path}.metric_key`),
    metric_value: number(row.metric_value, `${path}.metric_value`),
    observed_at: timestamp(row.observed_at, `${path}.observed_at`),
    source_run_id: safeId(row.source_run_id, `${path}.source_run_id`),
    source_artifact_sha256: digest(row.source_artifact_sha256, `${path}.source_artifact_sha256`),
    status: enumeration(row.status, ["active", "superseded"] as const, `${path}.status`),
    supersedes_progress_id: nullable(row.supersedes_progress_id, (item) => uuid(item, `${path}.supersedes_progress_id`)),
    created_at: timestamp(row.created_at, `${path}.created_at`),
    updated_at: timestamp(row.updated_at, `${path}.updated_at`),
  }
}

function trainingTrend(value: unknown, path: string): TrainingMetricTrendWire {
  const row = record(value, path)
  exact(row, ["metric_key", "direction", "comparison"], path)
  const comparison = record(row.comparison, `${path}.comparison`)
  exact(comparison, ["trend", "sample_count", "previous_value", "current_value", "delta"], `${path}.comparison`)
  return {
    metric_key: safeId(row.metric_key, `${path}.metric_key`),
    direction: enumeration(row.direction, ["increase", "decrease", "maintain"] as const, `${path}.direction`),
    comparison: {
      trend: enumeration(comparison.trend, ["improving", "declining", "stable", "insufficient_data"] as const, `${path}.comparison.trend`),
      sample_count: number(comparison.sample_count, `${path}.comparison.sample_count`, { integer: true, min: 0 }),
      previous_value: nullable(comparison.previous_value, (item) => number(item, `${path}.comparison.previous_value`)),
      current_value: nullable(comparison.current_value, (item) => number(item, `${path}.comparison.current_value`)),
      delta: nullable(comparison.delta, (item) => number(item, `${path}.comparison.delta`)),
    },
  }
}

export function decodeTrainingProgressPage(value: unknown, expectedRelationshipId: string): TrainingProgressPageWire {
  const row = record(value, "training_progress")
  exact(row, ["schema_version", "events", "trends"], "training_progress")
  return {
    schema_version: literal(row.schema_version, "1.0", "training_progress.schema_version"),
    events: array(row.events, "training_progress.events", (item, index) => trainingProgress(item, `training_progress.events[${index}]`, expectedRelationshipId)),
    trends: array(row.trends, "training_progress.trends", (item, index) => trainingTrend(item, `training_progress.trends[${index}]`), 8),
  }
}

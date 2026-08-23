import { describe, expect, it } from "vitest"

import {
  decodeEvidence,
  decodeLatestProfileReview,
  decodePlayerProfilePage,
  decodeProductState,
  decodeRecentSummary,
  decodeReport,
  decodeRun,
  decodeTask,
  decodeTaskEventPage,
  decodeTrainingPlanPage,
  decodeTrainingProgressPage,
} from "./decoders"

const PROFILE_ID = "95000000-0000-4000-8000-000000000001"
const TASK_ID = "96000000-0000-4000-8000-000000000001"
const RUN_ID = "review_live_workbench_1"
const NOW = "2026-08-23T11:00:00Z"
const DIGEST = "a".repeat(64)

const profilePage = () => ({
  schema_version: "1.0",
  profiles: [
    {
      schema_version: "1.0",
      player_profile_id: PROFILE_ID,
      riot_id: "Riverline#EUW",
      routing_region: "europe",
      relationship_role: "self",
      verification_status: "unverified_claim",
      last_resolved_at: NOW,
    },
  ],
  limit: 50,
})

const latest = () => ({
  schema_version: "1.0",
  player_profile_id: PROFILE_ID,
  latest_review: {
    task_id: TASK_ID,
    run_id: RUN_ID,
    status: "running",
    created_at: NOW,
    updated_at: NOW,
    publication_status: null,
    report_available: false,
    links: {
      task: `/tasks/${TASK_ID}`,
      events: `/tasks/${TASK_ID}/events`,
      stream: `/tasks/${TASK_ID}/events/stream`,
      run: `/runs/${RUN_ID}`,
      summary: `/runs/${RUN_ID}/recent-summary`,
      report: `/runs/${RUN_ID}/report`,
      product_state: `/runs/${RUN_ID}/product-state`,
      evidence: `/runs/${RUN_ID}/evidence`,
    },
  },
})

const task = () => ({
  schema_version: "2.0",
  task_id: TASK_ID,
  run_id: RUN_ID,
  status: "running",
  created_at: NOW,
  updated_at: NOW,
  claimed_at: NOW,
  finished_at: null,
  terminal_reason: null,
  publication_status: null,
  report_available: false,
})

const eventPage = () => ({
  schema_version: "1.0",
  task_id: TASK_ID,
  after_cursor: 0,
  next_cursor: 3,
  limit: 50,
  has_more: false,
  events: [
    {
      event_schema_version: "1.0",
      event_cursor: 3,
      event_identity: DIGEST,
      task_id: TASK_ID,
      run_id: RUN_ID,
      task_sequence: 2,
      event_kind: "execution_started",
      status_after: "running",
      lease_generation: 1,
      reason: null,
      occurred_at: NOW,
    },
  ],
})

const productState = () => ({
  schema_version: "1.0",
  task_id: TASK_ID,
  run_id: RUN_ID,
  state: "not_ready",
  reason_code: "task_pending",
  task_status: "running",
  publication_status: null,
  report_available: false,
  evidence_revision: null,
  evidence_bundle_digest: null,
  evidence_freshness: null,
  evidence_disposition: null,
})

const run = () => ({
  schema_version: "1.0",
  run_id: RUN_ID,
  runtime_status: "completed",
  publication_status: "published",
  terminal_reason: "quality_gate_passed",
  skill_name: "recent-form-review",
  skill_version: "0.2.0",
  prompt_profile_id: "recent-form-review-coach",
  prompt_profile_version: "1.0.0",
  started_at_utc: NOW,
  completed_at_utc: NOW,
  elapsed_ms: 1234,
  usage: null,
  report_available: true,
})

const summary = () => ({
  schema_version: "1.0",
  run_id: RUN_ID,
  skill_name: "recent-form-review",
  skill_version: "0.2.0",
  runtime_status: "completed",
  publication_status: "published",
  terminal_reason: "quality_gate_passed",
  report_available: true,
  games_analyzed: 2,
  wins: 1,
  losses: 1,
  win_rate: 50,
  main_role: "MIDDLE",
  main_champions: ["Ahri", "Akali"],
  averages: {
    kda: 3.2,
    cs_per_min: 8,
    gold_per_min: 410,
    damage_per_min: 550,
    vision_score: 21,
    kill_participation_percent: 62,
    damage_share_percent: 27,
    gold_share_percent: 24,
    deaths_before_15: 0.5,
  },
  win_loss_comparison: {
    wins: {
      cs_per_min: 8,
      gold_per_min: 410,
      damage_per_min: 550,
      vision_score: 21,
      deaths_before_15: 0.5,
    },
    losses: {
      cs_per_min: 8,
      gold_per_min: 410,
      damage_per_min: 550,
      vision_score: 21,
      deaths_before_15: 0.5,
    },
  },
})

const evidence = () => ({
  schema_version: "1.0",
  snapshot_id: "97000000-0000-4000-8000-000000000001",
  task_id: TASK_ID,
  run_id: RUN_ID,
  revision: 1,
  bundle_digest: DIGEST,
  snapshot_digest: "b".repeat(64),
  stored_at: NOW,
  expires_at: null,
  freshness: "current",
  bundle_disposition: "degraded",
  confidence: "medium",
  usable_claims: ["riot_match_facts"],
  projection: {
    schema_version: "1.0",
    bundle_digest: DIGEST,
    disposition: "degraded",
    confidence: "medium",
    claims: ["riot_match_facts"],
    matches: [
      {
        match_id: "ASIA1_123",
        champion_name: "Ahri",
        position: "mid",
        patch_version: "16.16",
        win: true,
        timeline_available: true,
      },
    ],
    joins: [
      {
        key: {
          routing_region: "asia",
          queue_id: 420,
          position: "mid",
          champion_name: "Ahri",
          patch_version: "16.16",
        },
        status: "unjoined",
        confidence: "medium",
        sources_present: {
          riot: true,
          data_dragon: false,
          riot_patch: false,
          opgg: false,
        },
      },
    ],
    conflicts: [],
    gaps: [
      {
        code: "data_dragon_missing",
        source: "data_dragon",
        key: null,
      },
    ],
    sources: {
      riot_official: {
        match_count: 1,
        digests: ["c".repeat(64)],
        freshness: "current",
      },
      data_dragon: {
        version: null,
        catalog_digest: null,
        freshness: "unknown",
      },
      riot_patch: {
        patch_version: null,
        source_digest: null,
        freshness: "unknown",
      },
      opgg: {
        evidence_count: 0,
        digests: [],
        provenance: [],
        freshness: "unknown",
      },
    },
  },
})

const planPage = () => ({
  schema_version: "1.0",
  plans: [
    {
      schema_version: "1.0",
      plan_id: "98000000-0000-4000-8000-000000000001",
      relationship_id: PROFILE_ID,
      version: 1,
      status: "active",
      payload: {
        title: "Early death control",
        objective: "Reduce deaths before 15 minutes",
        metrics: [
          {
            metric_key: "deaths_before_15",
            direction: "decrease",
            unit: "count",
            baseline: 1.2,
            target: 0.7,
            stable_tolerance: 0.1,
          },
        ],
      },
      supersedes_plan_id: null,
      created_at: NOW,
      updated_at: NOW,
    },
  ],
})

const progressPage = () => ({
  schema_version: "1.0",
  events: [
    {
      schema_version: "1.0",
      progress_id: "99000000-0000-4000-8000-000000000001",
      plan_id: "98000000-0000-4000-8000-000000000001",
      relationship_id: PROFILE_ID,
      metric_key: "deaths_before_15",
      metric_value: 0.8,
      observed_at: NOW,
      source_run_id: RUN_ID,
      source_artifact_sha256: DIGEST,
      status: "active",
      supersedes_progress_id: null,
      created_at: NOW,
      updated_at: NOW,
    },
  ],
  trends: [
    {
      metric_key: "deaths_before_15",
      direction: "decrease",
      comparison: {
        trend: "improving",
        sample_count: 2,
        previous_value: 1,
        current_value: 0.8,
        delta: -0.2,
      },
    },
  ],
})

describe("exact API decoders", () => {
  it("decodes every live workbench resource and keeps snake_case wire truth", () => {
    expect(decodePlayerProfilePage(profilePage()).profiles[0]?.player_profile_id).toBe(PROFILE_ID)
    expect(decodeLatestProfileReview(latest(), PROFILE_ID).latest_review?.task_id).toBe(TASK_ID)
    expect(decodeTask(task(), { taskId: TASK_ID, runId: RUN_ID }).status).toBe("running")
    expect(decodeTaskEventPage(eventPage(), { taskId: TASK_ID, runId: RUN_ID }).next_cursor).toBe(3)
    expect(decodeProductState(productState(), { taskId: TASK_ID, runId: RUN_ID }).state).toBe("not_ready")
    expect(decodeRun(run(), RUN_ID).runtime_status).toBe("completed")
    expect(decodeRecentSummary(summary(), RUN_ID).games_analyzed).toBe(2)
    expect(decodeReport("## Verified brief\n\nKeep the wave stable.")).toContain("Verified brief")
    expect(decodeEvidence(evidence(), { taskId: TASK_ID, runId: RUN_ID }).projection.sources.opgg.evidence_count).toBe(0)
    expect(decodeTrainingPlanPage(planPage(), PROFILE_ID).plans[0]?.payload.metrics[0]?.target).toBe(0.7)
    expect(decodeTrainingProgressPage(progressPage(), PROFILE_ID).trends[0]?.comparison.trend).toBe("improving")
  })

  it("rejects extra keys at nested boundaries", () => {
    const payload = evidence()
    Object.assign(payload.projection.sources.opgg, { raw_body: "secret" })

    expect(() => decodeEvidence(payload, { taskId: TASK_ID, runId: RUN_ID })).toThrow(/unexpected key/i)
  })

  it("rejects unknown schema and enum values", () => {
    const badSchema = profilePage()
    badSchema.schema_version = "2.0"
    const badEnum = productState()
    badEnum.state = "almost_ready"

    expect(() => decodePlayerProfilePage(badSchema)).toThrow(/schema_version/i)
    expect(() => decodeProductState(badEnum, { taskId: TASK_ID, runId: RUN_ID })).toThrow(/state/i)
  })

  it("rejects non-finite numbers, bad timestamps, UUIDs and digests", () => {
    const badNumber = summary()
    badNumber.averages.kda = Number.NaN
    const badTime = task()
    badTime.updated_at = "2026-08-23T11:00:00"
    const badUuid = latest()
    badUuid.player_profile_id = "profile-local"
    const badDigest = evidence()
    badDigest.bundle_digest = "abcd"

    expect(() => decodeRecentSummary(badNumber, RUN_ID)).toThrow(/finite/i)
    expect(() => decodeTask(badTime, { taskId: TASK_ID, runId: RUN_ID })).toThrow(/timestamp/i)
    expect(() => decodeLatestProfileReview(badUuid, PROFILE_ID)).toThrow(/uuid/i)
    expect(() => decodeEvidence(badDigest, { taskId: TASK_ID, runId: RUN_ID })).toThrow(/digest/i)
  })

  it("fails closed when profile, task or run binding differs", () => {
    expect(() => decodeLatestProfileReview(latest(), "95000000-0000-4000-8000-000000000099")).toThrow(/profile binding/i)
    expect(() => decodeTask(task(), { taskId: "96000000-0000-4000-8000-000000000099", runId: RUN_ID })).toThrow(/task binding/i)
    expect(() => decodeEvidence(evidence(), { taskId: TASK_ID, runId: "review_other" })).toThrow(/run binding/i)
  })

  it("keeps report text bounded and rejects non-text/control bodies", () => {
    expect(() => decodeReport({ markdown: "not wire text" })).toThrow(/text/i)
    expect(() => decodeReport("safe\u0000unsafe")).toThrow(/control/i)
    expect(() => decodeReport("x".repeat(1_048_577))).toThrow(/size/i)
  })
})

import { describe, expect, it } from "vitest"

import type {
  EvidenceSnapshotWire,
  PlayerProfileWire,
  ProductStateWire,
  RecentSummaryWire,
  RunWire,
  TaskEventWire,
  TaskWire,
  TrainingPlanPageWire,
  TrainingProgressPageWire,
} from "../api/wire"
import {
  adaptEvidence,
  adaptPlayerProfile,
  adaptProductState,
  adaptRecentSummary,
  adaptRun,
  adaptTask,
  adaptTaskEvent,
  adaptTraining,
} from "./adapters"

const PROFILE_ID = "95000000-0000-4000-8000-000000000001"
const TASK_ID = "96000000-0000-4000-8000-000000000001"
const RUN_ID = "review_live_workbench_1"
const NOW = "2026-08-23T11:00:00Z"
const DIGEST = "a".repeat(64)

const selfProfile: PlayerProfileWire = {
  schema_version: "1.0",
  player_profile_id: PROFILE_ID,
  riot_id: "Riverline#EUW",
  routing_region: "europe",
  relationship_role: "self",
  verification_status: "unverified_claim",
  last_resolved_at: NOW,
}

const observedProfile: PlayerProfileWire = {
  ...selfProfile,
  relationship_role: "observed",
  verification_status: "not_applicable",
}

describe("deterministic wire to workbench adapters", () => {
  it("maps server observed role to public_observed only at the view boundary", () => {
    expect(adaptPlayerProfile(selfProfile).relationshipRole).toBe("self")
    expect(adaptPlayerProfile(observedProfile).relationshipRole).toBe("public_observed")
  })

  it("maps task, event, product, run and Summary without inventing fields", () => {
    const task: TaskWire = {
      schema_version: "2.0",
      task_id: TASK_ID,
      run_id: RUN_ID,
      status: "succeeded",
      created_at: NOW,
      updated_at: NOW,
      claimed_at: NOW,
      finished_at: NOW,
      terminal_reason: "quality_gate_passed",
      publication_status: "published",
      report_available: true,
    }
    const event: TaskEventWire = {
      event_schema_version: "1.0",
      event_cursor: 7,
      event_identity: DIGEST,
      task_id: TASK_ID,
      run_id: RUN_ID,
      task_sequence: 4,
      event_kind: "succeeded",
      status_after: "succeeded",
      lease_generation: 1,
      reason: "quality_gate_passed",
      occurred_at: NOW,
    }
    const product: ProductStateWire = {
      schema_version: "1.0",
      task_id: TASK_ID,
      run_id: RUN_ID,
      state: "published",
      reason_code: "ready",
      task_status: "succeeded",
      publication_status: "published",
      report_available: true,
      evidence_revision: 1,
      evidence_bundle_digest: DIGEST,
      evidence_freshness: "current",
      evidence_disposition: "complete",
    }
    const run: RunWire = {
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
      elapsed_ms: 1200,
      usage: null,
      report_available: true,
    }
    const summary: RecentSummaryWire = {
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
      main_champions: ["Ahri"],
      averages: {
        kda: 3,
        cs_per_min: 8,
        gold_per_min: 410,
        damage_per_min: 550,
        vision_score: 20,
        kill_participation_percent: 60,
        damage_share_percent: 25,
        gold_share_percent: 23,
        deaths_before_15: 0.5,
      },
      win_loss_comparison: {
        wins: { cs_per_min: 9, gold_per_min: 430, damage_per_min: 580, vision_score: 22, deaths_before_15: 0 },
        losses: { cs_per_min: 7, gold_per_min: 390, damage_per_min: 520, vision_score: 18, deaths_before_15: 1 },
      },
    }

    expect(adaptTask(task)).not.toHaveProperty("publicationStatus")
    expect(adaptTaskEvent(event).cursor).toBe(7)
    expect(adaptProductState(product).state).toBe("published")
    expect(adaptRun(run).elapsedMs).toBe(1200)
    expect(adaptRecentSummary(summary).averages.csPerMinute).toBe(8)
  })

  it("maps Evidence through fixed source and gap dictionaries", () => {
    const evidence: EvidenceSnapshotWire = {
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
        matches: [],
        joins: [],
        conflicts: [],
        gaps: [{ code: "future_gap_code", source: "opgg", key: null }],
        sources: {
          riot_official: { match_count: 1, digests: ["c".repeat(64)], freshness: "current" },
          data_dragon: { version: null, catalog_digest: null, freshness: "unknown" },
          riot_patch: { patch_version: null, source_digest: null, freshness: "unknown" },
          opgg: { evidence_count: 0, digests: [], provenance: [], freshness: "unknown" },
        },
      },
    }

    const view = adaptEvidence(evidence)

    expect(view.sources.map((source) => source.label)).toEqual([
      "Riot Match API",
      "Data Dragon catalog",
      "Official patch facts",
      "OP.GG meta snapshot",
    ])
    expect(view.gaps[0]).toMatchObject({ code: "future_gap_code", summary: "Evidence limitation" })
  })

  it("uses only real Training plan/progress fields for self", () => {
    const plans: TrainingPlanPageWire = {
      schema_version: "1.0",
      plans: [{
        schema_version: "1.0",
        plan_id: "98000000-0000-4000-8000-000000000001",
        relationship_id: PROFILE_ID,
        version: 1,
        status: "active",
        payload: {
          title: "Early death control",
          objective: "Reduce deaths before 15",
          metrics: [{ metric_key: "deaths_before_15", direction: "decrease", unit: "count", baseline: 1.2, target: 0.7, stable_tolerance: 0.1 }],
        },
        supersedes_plan_id: null,
        created_at: NOW,
        updated_at: NOW,
      }],
    }
    const progress: TrainingProgressPageWire = {
      schema_version: "1.0",
      events: [],
      trends: [{
        metric_key: "deaths_before_15",
        direction: "decrease",
        comparison: { trend: "improving", sample_count: 2, previous_value: 1, current_value: 0.8, delta: -0.2 },
      }],
    }

    expect(adaptTraining(selfProfile, plans, progress)).toEqual({
      mode: "personal",
      title: "Early death control",
      objective: "Reduce deaths before 15",
      metric: {
        metricKey: "deaths_before_15",
        baseline: 1.2,
        target: 0.7,
        current: 0.8,
        unit: "count",
        trend: "improving",
        sampleCount: 2,
      },
    })
  })

  it("never projects personal Training for observed profiles", () => {
    const view = adaptTraining(observedProfile, undefined, undefined)

    expect(view).toEqual({
      mode: "learning_observation",
      readOnly: true,
      note: "Public observed profiles are read-only; private training state is never inferred.",
    })
    expect(view).not.toHaveProperty("metric")
  })
})

import { describe, expect, it, vi } from "vitest"

import type {
  LatestProfileReviewWire,
  PlayerProfilePageWire,
  ProductStateWire,
  RecentSummaryWire,
  RunTimelineWire,
  RunWire,
  EvidenceSnapshotWire,
  TaskEventPageWire,
  TaskEventWire,
  TaskWire,
} from "../api/wire"
import type { TaskEventStreamCallbacks, TaskEventStreamHandle } from "../api/taskEventStream"
import {
  LiveWorkbenchController,
  type LiveWorkbenchDataApi,
  type LiveWorkbenchStreamFactory,
} from "./liveController"

const SELF = "95000000-0000-4000-8000-000000000001"
const OBSERVED = "95000000-0000-4000-8000-000000000002"
const TASK_ID = "96000000-0000-4000-8000-000000000001"
const RUN_ID = "review_live_workbench_1"
const NOW = "2026-08-23T11:00:00Z"

const profiles = (): PlayerProfilePageWire => ({
  schema_version: "1.0",
  limit: 50,
  profiles: [
    { schema_version: "1.0", player_profile_id: SELF, riot_id: "Riverline#EUW", routing_region: "europe", relationship_role: "self", verification_status: "unverified_claim", last_resolved_at: NOW },
    { schema_version: "1.0", player_profile_id: OBSERVED, riot_id: "Northstar#KR", routing_region: "asia", relationship_role: "observed", verification_status: "not_applicable", last_resolved_at: NOW },
  ],
})

const latest = (profileId = SELF): LatestProfileReviewWire => ({
  schema_version: "1.0",
  player_profile_id: profileId,
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
      timeline: `/runs/${RUN_ID}/timeline`,
      report: `/runs/${RUN_ID}/report`,
      product_state: `/runs/${RUN_ID}/product-state`,
      evidence: `/runs/${RUN_ID}/evidence`,
    },
  },
})

const task = (status: TaskWire["status"] = "running"): TaskWire => ({
  schema_version: "2.0",
  task_id: TASK_ID,
  run_id: RUN_ID,
  status,
  created_at: NOW,
  updated_at: NOW,
  claimed_at: status === "queued" ? null : NOW,
  finished_at: ["succeeded", "failed", "cancelled"].includes(status) ? NOW : null,
  terminal_reason: ["succeeded", "failed", "cancelled"].includes(status) ? "review_finished" : null,
  publication_status: status === "succeeded" ? "published" : null,
  report_available: status === "succeeded",
})

const product = (state: ProductStateWire["state"] = "not_ready"): ProductStateWire => ({
  schema_version: "1.0",
  task_id: TASK_ID,
  run_id: RUN_ID,
  state,
  reason_code: state === "not_ready" ? "task_pending" : state === "published" ? "ready" : state === "degraded" ? "quality_degraded" : "quality_rejected",
  task_status: state === "not_ready" ? "running" : "succeeded",
  publication_status: state === "not_ready" ? null : state === "rejected" ? "rejected" : state,
  report_available: state === "published" || state === "degraded",
  evidence_revision: state === "not_ready" ? null : 1,
  evidence_bundle_digest: state === "not_ready" ? null : "a".repeat(64),
  evidence_freshness: state === "not_ready" ? null : "current",
  evidence_disposition: state === "published" ? "complete" : state === "not_ready" ? null : "degraded",
})

const events = (): TaskEventPageWire => ({
  schema_version: "1.0",
  task_id: TASK_ID,
  after_cursor: 0,
  next_cursor: 0,
  limit: 50,
  has_more: false,
  events: [],
})

class FakeApi implements LiveWorkbenchDataApi {
  profilePage = profiles()
  latestByProfile = new Map([[SELF, latest(SELF)], [OBSERVED, latest(OBSERVED)]])
  taskValue = task()
  productValue = product()
  runValue: RunWire | undefined
  summaryValue: RecentSummaryWire | undefined
  timelineValue: RunTimelineWire | undefined
  reportValue: string | undefined
  evidenceValue: EvidenceSnapshotWire | undefined
  calls: string[] = []

  async listProfiles(_signal: AbortSignal) { this.calls.push("profiles"); return this.profilePage }
  async getLatest(profileId: string, _signal: AbortSignal) { this.calls.push(`latest:${profileId}`); return this.latestByProfile.get(profileId)! }
  async getTask(_taskId: string, _runId: string, _signal: AbortSignal) { this.calls.push("task"); return this.taskValue }
  async getEvents(_taskId: string, _runId: string, _signal: AbortSignal) { this.calls.push("events"); return events() }
  async getProductState(_taskId: string, _runId: string, _signal: AbortSignal) { this.calls.push("product"); return this.productValue }
  async getRun() { this.calls.push("run"); return this.runValue }
  async getSummary() { this.calls.push("summary"); return this.summaryValue }
  async getTimeline() { this.calls.push("timeline"); return this.timelineValue }
  async getReport() { this.calls.push("report"); return this.reportValue }
  async getEvidence() { this.calls.push("evidence"); return this.evidenceValue }
  async getTrainingPlans(_profileId: string, _signal: AbortSignal) { this.calls.push("training-plans"); return { schema_version: "1.0" as const, plans: [] } }
  async getTrainingProgress(_profileId: string, _signal: AbortSignal) { this.calls.push("training-progress"); return { schema_version: "1.0" as const, events: [], trends: [] } }
}

function streamHarness() {
  const handles: { close: ReturnType<typeof vi.fn>; callbacks: TaskEventStreamCallbacks }[] = []
  const factory: LiveWorkbenchStreamFactory = (_binding, callbacks) => {
    const handle = { close: vi.fn(), callbacks }
    handles.push(handle)
    return handle as TaskEventStreamHandle
  }
  return { handles, factory }
}

describe("generation-guarded live controller", () => {
  it("uses finite client message codes instead of English display strings", async () => {
    const controller = new LiveWorkbenchController({
      api: new FakeApi(),
      streamFactory: streamHarness().factory,
    })

    expect(controller.snapshot.state).toEqual({ client: "loading", messageCode: "profiles_loading" })
    await controller.selectProfile("missing-profile")

    expect(controller.snapshot.state).toEqual({
      client: "error",
      code: "player_profile_not_found",
      messageCode: "selected_profile_unavailable",
    })
  })

  it("loads the verified Timeline with terminal published content", async () => {
    const api = new FakeApi()
    api.taskValue = task("succeeded")
    api.productValue = product("published")
    api.runValue = {
      schema_version: "1.0", run_id: RUN_ID, runtime_status: "completed", publication_status: "published",
      terminal_reason: "quality_gate_passed", skill_name: "recent-form-review", skill_version: "0.2.0",
      prompt_profile_id: "recent-form-review-coach", prompt_profile_version: "1.0.0", started_at_utc: NOW,
      completed_at_utc: NOW, elapsed_ms: 100, usage: null, report_available: true,
    }
    api.summaryValue = {
      schema_version: "1.0", run_id: RUN_ID, skill_name: "recent-form-review", skill_version: "0.2.0",
      runtime_status: "completed", publication_status: "published", terminal_reason: "quality_gate_passed",
      report_available: true, games_analyzed: 1, wins: 1, losses: 0, win_rate: 100, main_role: "MIDDLE",
      main_champions: ["Ahri"],
      averages: { kda: 3, cs_per_min: 8, gold_per_min: 410, damage_per_min: 550, vision_score: 21,
        kill_participation_percent: 62, damage_share_percent: 27, gold_share_percent: 24, deaths_before_15: 0 },
      win_loss_comparison: {
        wins: { cs_per_min: 8, gold_per_min: 410, damage_per_min: 550, vision_score: 21, deaths_before_15: 0 },
        losses: { cs_per_min: 0, gold_per_min: 0, damage_per_min: 0, vision_score: 0, deaths_before_15: 0 },
      },
    }
    api.timelineValue = {
      schema_version: "1.0", run_id: RUN_ID, skill_name: "recent-form-review", skill_version: "0.2.0",
      runtime_status: "completed", publication_status: "published", terminal_reason: "quality_gate_passed",
      source: "riot_match_v5_timeline", timeline_status: "available", total_matches: 1, projected_matches: 1,
      matches_truncated: false, matches: [{ match_id: "EUW1_123", champion_name: "Ahri", role: "MIDDLE",
        win: true, game_duration_seconds: 1800, included_in_aggregate: true, timeline_status: "available",
        unavailable_reason: null, total_events: 1, projected_events: 1, events_truncated: false,
        events: [{ event_kind: "objective", at_seconds: 1200, phase: "mid", label: "Dragon secured", item_id: null }] }],
    }
    api.reportValue = "## Verified brief"
    api.evidenceValue = {
      schema_version: "1.0", snapshot_id: "97000000-0000-4000-8000-000000000001", task_id: TASK_ID,
      run_id: RUN_ID, revision: 1, bundle_digest: "a".repeat(64), snapshot_digest: "b".repeat(64),
      stored_at: NOW, expires_at: null, freshness: "current", bundle_disposition: "complete", confidence: "high",
      usable_claims: ["riot_match_facts"], projection: { schema_version: "1.0", bundle_digest: "a".repeat(64),
        disposition: "complete", confidence: "high", claims: ["riot_match_facts"], matches: [], joins: [], conflicts: [],
        sources: { riot_official: { match_count: 1, digests: ["c".repeat(64)], freshness: "current" },
          data_dragon: { version: null, catalog_digest: null, freshness: "unknown" },
          riot_patch: { patch_version: null, source_digest: null, freshness: "unknown" },
          opgg: { evidence_count: 0, digests: [], provenance: [], freshness: "unknown" } }, gaps: [] },
    }

    const controller = new LiveWorkbenchController({ api, streamFactory: streamHarness().factory })
    await controller.start()

    expect(controller.snapshot.state.client === "ready" && controller.snapshot.state.data.timeline?.matches[0]?.events[0]?.phase).toBe("mid")
  })
  it("loads profiles, active control state and opens at most one stream", async () => {
    const api = new FakeApi()
    const stream = streamHarness()
    const controller = new LiveWorkbenchController({ api, streamFactory: stream.factory })

    await controller.start()

    expect(controller.snapshot.state.client).toBe("ready")
    expect(controller.snapshot.state.client === "ready" && controller.snapshot.state.data.selectedProfileId).toBe(SELF)
    expect(stream.handles).toHaveLength(1)
    expect(api.calls).toEqual(["profiles", `latest:${SELF}`, "task", "product", "events", "training-plans", "training-progress"])
  })

  it("treats latest null as a legal empty profile state", async () => {
    const api = new FakeApi()
    api.latestByProfile.set(SELF, { schema_version: "1.0", player_profile_id: SELF, latest_review: null })
    const controller = new LiveWorkbenchController({ api, streamFactory: streamHarness().factory })

    await controller.start()

    expect(controller.snapshot.state.client).toBe("ready")
    expect(controller.snapshot.state.client === "ready" && controller.snapshot.state.data.task).toBeUndefined()
  })

  it("keeps reconnecting transport separate and authoritatively reloads terminal", async () => {
    const api = new FakeApi()
    const stream = streamHarness()
    const controller = new LiveWorkbenchController({ api, streamFactory: stream.factory })
    await controller.start()

    stream.handles[0]!.callbacks.onState("reconnecting")
    expect(controller.snapshot.liveUpdates).toBe("reconnecting")
    expect(controller.snapshot.state.client === "ready" && controller.snapshot.state.data.productState?.state).toBe("not_ready")

    api.taskValue = task("succeeded")
    api.productValue = product("rejected")
    const terminal: TaskEventWire = {
      event_schema_version: "1.0",
      event_cursor: 5,
      event_identity: "a".repeat(64),
      task_id: TASK_ID,
      run_id: RUN_ID,
      task_sequence: 5,
      event_kind: "succeeded",
      status_after: "succeeded",
      lease_generation: 1,
      reason: "quality_gate_passed",
      occurred_at: NOW,
    }
    await stream.handles[0]!.callbacks.onTerminal(terminal)

    expect(stream.handles[0]!.close).toHaveBeenCalled()
    expect(controller.snapshot.state.client === "ready" && controller.snapshot.state.data.productState?.state).toBe("rejected")
  })

  it("closes the old stream and never requests Training for observed", async () => {
    const api = new FakeApi()
    const stream = streamHarness()
    const controller = new LiveWorkbenchController({ api, streamFactory: stream.factory })
    await controller.start()
    api.calls = []

    await controller.selectProfile(OBSERVED)

    expect(stream.handles[0]!.close).toHaveBeenCalledTimes(1)
    expect(stream.handles).toHaveLength(2)
    expect(api.calls).not.toContain("training-plans")
    expect(api.calls).not.toContain("training-progress")
    expect(controller.snapshot.state.client === "ready" && controller.snapshot.state.data.training?.mode).toBe("learning_observation")
  })

  it("closes the active selection before rejecting an unknown profile", async () => {
    const api = new FakeApi()
    const stream = streamHarness()
    const controller = new LiveWorkbenchController({ api, streamFactory: stream.factory })
    await controller.start()

    await controller.selectProfile("33333333-3333-4333-8333-333333333333")

    expect(stream.handles[0]!.close).toHaveBeenCalledOnce()
    expect(stream.handles).toHaveLength(1)
    expect(controller.snapshot.state).toMatchObject({
      client: "error",
      code: "player_profile_not_found",
    })
    expect(controller.snapshot.liveUpdates).toBe("closed")
  })

  it("drops late profile responses after a generation switch", async () => {
    const api = new FakeApi()
    let releaseSelf!: () => void
    const original = api.getLatest.bind(api)
    api.getLatest = async (profileId, signal) => {
      if (profileId === SELF) await new Promise<void>((resolve) => { releaseSelf = resolve })
      return original(profileId, signal)
    }
    const controller = new LiveWorkbenchController({ api, streamFactory: streamHarness().factory })
    const starting = controller.start()
    await Promise.resolve()
    const switched = controller.selectProfile(OBSERVED)
    releaseSelf()
    await Promise.all([starting, switched])

    expect(controller.snapshot.state.client === "ready" && controller.snapshot.state.data.selectedProfileId).toBe(OBSERVED)
  })

  it("dispose aborts requests, closes stream and ignores late events", async () => {
    const api = new FakeApi()
    const stream = streamHarness()
    const controller = new LiveWorkbenchController({ api, streamFactory: stream.factory })
    await controller.start()

    controller.dispose()
    stream.handles[0]!.callbacks.onEvent({} as TaskEventWire)

    expect(stream.handles[0]!.close).toHaveBeenCalledTimes(1)
    expect(controller.snapshot.liveUpdates).toBe("closed")
  })
})

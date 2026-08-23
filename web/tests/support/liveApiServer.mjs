import { createServer } from "node:http"

const HOST = "127.0.0.1"
const PORT = 4174
const SELF = "95000000-0000-4000-8000-000000000001"
const OBSERVED = "95000000-0000-4000-8000-000000000002"
const TASK = "96000000-0000-4000-8000-000000000001"
const RUN = "review_live_workbench_1"
const NOW = "2026-08-23T11:00:00Z"
const DIGEST_A = "a".repeat(64)
const DIGEST_B = "b".repeat(64)
const ledgers = new Map()

function cookies(request) {
  return Object.fromEntries(
    (request.headers.cookie ?? "")
      .split(";")
      .map((item) => item.trim().split("=", 2))
      .filter(([key, value]) => key && value)
      .map(([key, value]) => [key, decodeURIComponent(value)]),
  )
}

function context(request) {
  const values = cookies(request)
  const scenario = values["riftcoach-test-scenario"] ?? "active"
  const testId = values["riftcoach-test-id"] ?? `anonymous-${scenario}`
  let ledger = ledgers.get(testId)
  if (ledger === undefined) {
    ledger = { requests: [], openStreams: 0, closedStreams: 0, terminal: false, latestSelfCalls: 0 }
    ledgers.set(testId, ledger)
  }
  return { scenario, testId, ledger }
}

function sendJson(response, value, status = 200) {
  const body = JSON.stringify(value)
  response.writeHead(status, {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(body),
    "cache-control": "no-store",
  })
  response.end(body)
}

function sendText(response, value, mediaType = "text/plain") {
  response.writeHead(200, {
    "content-type": `${mediaType}; charset=utf-8`,
    "content-length": Buffer.byteLength(value),
    "cache-control": "no-store",
  })
  response.end(value)
}

function profiles(scenario) {
  if (scenario === "empty") return []
  return [
    {
      schema_version: "1.0",
      player_profile_id: SELF,
      riot_id: "Riverline#EUW",
      routing_region: "europe",
      relationship_role: "self",
      verification_status: "unverified_claim",
      last_resolved_at: NOW,
    },
    {
      schema_version: "1.0",
      player_profile_id: OBSERVED,
      riot_id: "Northstar#KR",
      routing_region: "asia",
      relationship_role: "observed",
      verification_status: "not_applicable",
      last_resolved_at: NOW,
    },
  ]
}

function productMode(scenario, ledger) {
  if (scenario === "degraded") return "degraded"
  if (scenario === "rejected") return "rejected"
  if (scenario === "published" || scenario === "race") return "published"
  if (scenario === "active" && ledger.terminal) return "published"
  return "not_ready"
}

function taskPayload(scenario, ledger) {
  const mode = productMode(scenario, ledger)
  const terminal = mode !== "not_ready"
  return {
    schema_version: "2.0",
    task_id: TASK,
    run_id: RUN,
    status: terminal ? "succeeded" : "running",
    created_at: NOW,
    updated_at: terminal ? "2026-08-23T11:00:04Z" : NOW,
    claimed_at: NOW,
    finished_at: terminal ? "2026-08-23T11:00:04Z" : null,
    terminal_reason: terminal ? "quality_gate_complete" : null,
    publication_status: mode === "published" ? "published" : mode === "degraded" ? "degraded" : mode === "rejected" ? "rejected" : null,
    report_available: mode === "published" || mode === "degraded",
  }
}

function links() {
  return {
    task: `/tasks/${TASK}`,
    events: `/tasks/${TASK}/events`,
    stream: `/tasks/${TASK}/events/stream`,
    run: `/runs/${RUN}`,
    summary: `/runs/${RUN}/recent-summary`,
    report: `/runs/${RUN}/report`,
    product_state: `/runs/${RUN}/product-state`,
    evidence: `/runs/${RUN}/evidence`,
  }
}

function latest(profileId, scenario, ledger) {
  if (profileId === OBSERVED) {
    return { schema_version: "1.0", player_profile_id: OBSERVED, latest_review: null }
  }
  const task = taskPayload(scenario, ledger)
  return {
    schema_version: "1.0",
    player_profile_id: SELF,
    latest_review: {
      task_id: TASK,
      run_id: RUN,
      status: task.status,
      created_at: task.created_at,
      updated_at: task.updated_at,
      publication_status: task.publication_status,
      report_available: task.report_available,
      links: links(),
    },
  }
}

function lifecycleEvent(cursor, kind, status) {
  return {
    event_schema_version: "1.0",
    event_cursor: cursor,
    event_identity: cursor === 1 ? DIGEST_A : cursor === 2 ? DIGEST_B : "c".repeat(64),
    task_id: TASK,
    run_id: RUN,
    task_sequence: cursor,
    event_kind: kind,
    status_after: status,
    lease_generation: 1,
    reason: kind === "succeeded" ? "quality_gate_complete" : null,
    occurred_at: `2026-08-23T11:00:0${cursor}Z`,
  }
}

function eventPage(scenario, ledger) {
  const terminal = productMode(scenario, ledger) !== "not_ready"
  const events = terminal
    ? [lifecycleEvent(1, "created", "queued"), lifecycleEvent(3, "succeeded", "succeeded")]
    : [lifecycleEvent(1, "created", "queued")]
  return {
    schema_version: "1.0",
    task_id: TASK,
    after_cursor: 0,
    next_cursor: terminal ? 3 : 1,
    limit: 50,
    has_more: false,
    events,
  }
}

function productPayload(scenario, ledger) {
  const mode = productMode(scenario, ledger)
  const reason = mode === "published" ? "ready" : mode === "degraded" ? "evidence_expired" : mode === "rejected" ? "quality_rejected" : "task_pending"
  return {
    schema_version: "1.0",
    task_id: TASK,
    run_id: RUN,
    state: mode,
    reason_code: reason,
    task_status: mode === "not_ready" ? "running" : "succeeded",
    publication_status: mode === "not_ready" ? null : mode,
    report_available: mode === "published" || mode === "degraded",
    evidence_revision: mode === "not_ready" ? null : 1,
    evidence_bundle_digest: mode === "not_ready" ? null : DIGEST_A,
    evidence_freshness: mode === "not_ready" ? null : mode === "degraded" ? "expired" : "current",
    evidence_disposition: mode === "not_ready" ? null : mode === "published" ? "complete" : "degraded",
  }
}

function runPayload(scenario) {
  const mode = scenario === "degraded" ? "degraded" : "published"
  return {
    schema_version: "1.0",
    run_id: RUN,
    runtime_status: "completed",
    publication_status: mode,
    terminal_reason: "quality_gate_complete",
    skill_name: "recent-form-review",
    skill_version: "0.2.0",
    prompt_profile_id: "recent-form-review-coach",
    prompt_profile_version: "1.0.0",
    started_at_utc: NOW,
    completed_at_utc: "2026-08-23T11:00:04Z",
    elapsed_ms: 4000,
    usage: null,
    report_available: true,
  }
}

function metricRow(overrides = {}) {
  return {
    cs_per_min: 8.1,
    gold_per_min: 421,
    damage_per_min: 552,
    vision_score: 20,
    deaths_before_15: 0.5,
    ...overrides,
  }
}

function summaryPayload(scenario) {
  return {
    schema_version: "1.0",
    run_id: RUN,
    skill_name: "recent-form-review",
    skill_version: "0.2.0",
    runtime_status: "completed",
    publication_status: scenario === "degraded" ? "degraded" : "published",
    terminal_reason: "quality_gate_complete",
    report_available: true,
    games_analyzed: 8,
    wins: 5,
    losses: 3,
    win_rate: 62.5,
    main_role: "MIDDLE",
    main_champions: ["Ahri", "Akali"],
    averages: {
      ...metricRow(),
      kda: 3.2,
      kill_participation_percent: 62,
      damage_share_percent: 27,
      gold_share_percent: 24,
    },
    win_loss_comparison: {
      wins: metricRow({ gold_per_min: 452, deaths_before_15: 0.2 }),
      losses: metricRow({ gold_per_min: 378, deaths_before_15: 1 }),
    },
  }
}

function evidencePayload(scenario) {
  const expired = scenario === "degraded"
  return {
    schema_version: "1.0",
    snapshot_id: "97000000-0000-4000-8000-000000000001",
    task_id: TASK,
    run_id: RUN,
    revision: 1,
    bundle_digest: DIGEST_A,
    snapshot_digest: DIGEST_B,
    stored_at: NOW,
    expires_at: expired ? "2026-08-23T11:30:00Z" : null,
    freshness: expired ? "expired" : "current",
    bundle_disposition: expired ? "degraded" : "complete",
    confidence: expired ? "medium" : "high",
    usable_claims: ["riot_match_facts", "data_dragon_static", "official_patch_facts", "current_meta_recommendation"],
    projection: {
      schema_version: "1.0",
      bundle_digest: DIGEST_A,
      disposition: expired ? "degraded" : "complete",
      confidence: expired ? "medium" : "high",
      claims: ["riot_match_facts", "data_dragon_static", "official_patch_facts", "current_meta_recommendation"],
      matches: [{
        match_id: "EUW1_123",
        champion_name: "Ahri",
        position: "mid",
        patch_version: "16.16",
        win: true,
        timeline_available: true,
      }],
      joins: [{
        key: { routing_region: "europe", queue_id: 420, position: "mid", champion_name: "Ahri", patch_version: "16.16" },
        status: "joined",
        confidence: "high",
        sources_present: { riot: true, data_dragon: true, riot_patch: true, opgg: true },
      }],
      conflicts: [],
      gaps: expired ? [{ code: "opgg_meta_missing", source: "opgg", key: null }] : [],
      sources: {
        riot_official: { match_count: 1, digests: [DIGEST_A], freshness: "current" },
        data_dragon: { version: "16.16.1", catalog_digest: DIGEST_B, freshness: "current" },
        riot_patch: { patch_version: "16.16", source_digest: "c".repeat(64), freshness: "current" },
        opgg: { evidence_count: 1, digests: ["d".repeat(64)], provenance: ["partial"], freshness: expired ? "expired" : "current" },
      },
    },
  }
}

function trainingPlan() {
  return {
    schema_version: "1.0",
    plans: [{
      schema_version: "1.0",
      plan_id: "98000000-0000-4000-8000-000000000001",
      relationship_id: SELF,
      version: 1,
      status: "active",
      payload: {
        title: "Early death control",
        objective: "Reduce deaths before 15 minutes",
        metrics: [{ metric_key: "deaths_before_15", direction: "decrease", unit: "count", baseline: 1.2, target: 0.7, stable_tolerance: 0.1 }],
      },
      supersedes_plan_id: null,
      created_at: NOW,
      updated_at: NOW,
    }],
  }
}

function trainingProgress() {
  return {
    schema_version: "1.0",
    events: [{
      schema_version: "1.0",
      progress_id: "99000000-0000-4000-8000-000000000001",
      plan_id: "98000000-0000-4000-8000-000000000001",
      relationship_id: SELF,
      metric_key: "deaths_before_15",
      metric_value: 0.8,
      observed_at: NOW,
      source_run_id: RUN,
      source_artifact_sha256: DIGEST_A,
      status: "active",
      supersedes_progress_id: null,
      created_at: NOW,
      updated_at: NOW,
    }],
    trends: [{
      metric_key: "deaths_before_15",
      direction: "decrease",
      comparison: { trend: "improving", sample_count: 2, previous_value: 1, current_value: 0.8, delta: -0.2 },
    }],
  }
}

function closeStream(ledger) {
  if (ledger.openStreams > 0) ledger.openStreams -= 1
  ledger.closedStreams += 1
}

function stream(response, scenario, ledger) {
  response.writeHead(200, {
    "content-type": "text/event-stream",
    "cache-control": "no-cache, no-transform",
    connection: "keep-alive",
  })
  ledger.openStreams += 1
  let closed = false
  const timers = []
  const close = () => {
    if (closed) return
    closed = true
    for (const timer of timers) clearTimeout(timer)
    closeStream(ledger)
  }
  response.on("close", close)
  response.write(`id: 2\nevent: task.lifecycle\ndata: ${JSON.stringify(lifecycleEvent(2, "heartbeat", "running"))}\n\n`)
  if (scenario === "active") {
    timers.push(setTimeout(() => {
      if (closed) return
      ledger.terminal = true
      response.write(`id: 3\nevent: task.lifecycle\ndata: ${JSON.stringify(lifecycleEvent(3, "succeeded", "succeeded"))}\n\n`)
      response.end()
    }, 1500))
  } else {
    const keepalive = setInterval(() => {
      if (!closed) response.write(": keepalive\n\n")
    }, 1000)
    response.on("close", () => clearInterval(keepalive))
  }
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://${HOST}:${PORT}`)
  if (url.pathname === "/health") return sendJson(response, { status: "ok" })
  if (url.pathname === "/__requests") {
    const ledger = ledgers.get(url.searchParams.get("test_id") ?? "") ?? { requests: [], openStreams: 0, closedStreams: 0 }
    return sendJson(response, { requests: ledger.requests, open_streams: ledger.openStreams, closed_streams: ledger.closedStreams })
  }

  const { scenario, ledger } = context(request)
  ledger.requests.push(`${request.method ?? "GET"} ${url.pathname}${url.search}`)
  if (request.method !== "GET") return sendJson(response, { code: "request_invalid" }, 405)

  if (url.pathname === "/player-profiles") {
    return sendJson(response, { schema_version: "1.0", profiles: profiles(scenario), limit: 50 })
  }
  const latestMatch = /^\/player-profiles\/([^/]+)\/reviews\/recent\/latest$/.exec(url.pathname)
  if (latestMatch !== null) {
    const profileId = decodeURIComponent(latestMatch[1])
    if (profileId === SELF) ledger.latestSelfCalls += 1
    if (scenario === "race" && profileId === SELF && ledger.latestSelfCalls > 1) {
      await new Promise((resolve) => setTimeout(resolve, 600))
    }
    return sendJson(response, latest(profileId, scenario, ledger))
  }
  if (url.pathname === `/tasks/${TASK}`) return sendJson(response, taskPayload(scenario, ledger))
  if (url.pathname === `/tasks/${TASK}/events`) return sendJson(response, eventPage(scenario, ledger))
  if (url.pathname === `/tasks/${TASK}/events/stream`) return stream(response, scenario, ledger)
  if (url.pathname === `/runs/${RUN}/product-state`) return sendJson(response, productPayload(scenario, ledger))
  if (url.pathname === `/runs/${RUN}`) return sendJson(response, runPayload(scenario))
  if (url.pathname === `/runs/${RUN}/recent-summary`) return sendJson(response, summaryPayload(scenario))
  if (url.pathname === `/runs/${RUN}/report`) {
    const report = scenario === "degraded"
      ? '## Limited brief\n\nEvidence is expired.\n\n<script>window.pwned=true</script>\n\n[external](https://evil.invalid)\n\n![pixel](https://evil.invalid/pixel.png)'
      : "## Verified brief\n\nKeep the wave stable before the first river move."
    return sendText(response, report, "text/markdown")
  }
  if (url.pathname === `/runs/${RUN}/evidence`) return sendJson(response, evidencePayload(scenario))
  if (url.pathname === `/memory/players/${SELF}/training-plan`) return sendJson(response, trainingPlan())
  if (url.pathname === `/memory/players/${SELF}/training-progress`) return sendJson(response, trainingProgress())

  return sendJson(response, { code: "run_not_found" }, 404)
})

server.listen(PORT, HOST, () => {
  process.stdout.write(`live-api-ready http://${HOST}:${PORT}\n`)
})

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)))
}

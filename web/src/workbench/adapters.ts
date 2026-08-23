import type {
  EvidenceSnapshotWire,
  PlayerProfileWire,
  ProductStateWire,
  RecentMetricRowWire,
  RecentSummaryWire,
  RunWire,
  TaskEventWire,
  TaskWire,
  TrainingPlanPageWire,
  TrainingProgressPageWire,
} from "../api/wire"
import type {
  LiveWorkbenchView,
  WorkbenchEvidence,
  WorkbenchEvidenceSource,
  WorkbenchPlayerProfile,
  WorkbenchProductState,
  WorkbenchRecentMetricRow,
  WorkbenchRecentSummary,
  WorkbenchRun,
  WorkbenchTask,
  WorkbenchTaskEvent,
  WorkbenchTraining,
} from "./model"
import type {
  ReviewWorkbenchFixture,
  TaskEventFixture,
} from "../contracts/workbench"

const sourceLabels = {
  riot_official: "Riot Match API",
  data_dragon: "Data Dragon catalog",
  riot_patch: "Official patch facts",
  opgg: "OP.GG meta snapshot",
} as const

const gapCopy: Readonly<Record<string, { summary: string; impact: string }>> = {
  data_dragon_missing: {
    summary: "Static catalog unavailable",
    impact: "Champion labels cannot claim an exact Data Dragon version.",
  },
  official_patch_missing: {
    summary: "Official patch evidence unavailable",
    impact: "The review cannot claim exact official patch alignment.",
  },
  opgg_meta_missing: {
    summary: "Meta comparison unavailable",
    impact: "Coaching remains grounded in Riot facts without a current Meta comparison.",
  },
}

export function adaptPlayerProfile(value: PlayerProfileWire): WorkbenchPlayerProfile {
  return {
    playerProfileId: value.player_profile_id,
    riotId: value.riot_id,
    routingRegion: value.routing_region,
    relationshipRole: value.relationship_role === "observed" ? "public_observed" : "self",
    verificationStatus: value.verification_status,
    lastResolvedAt: value.last_resolved_at,
  }
}

export function adaptTask(value: TaskWire): WorkbenchTask {
  return {
    taskId: value.task_id,
    runId: value.run_id,
    status: value.status,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
    ...(value.terminal_reason === null ? {} : { terminalReason: value.terminal_reason }),
  }
}

export function adaptTaskEvent(value: TaskEventWire): WorkbenchTaskEvent {
  return {
    cursor: value.event_cursor,
    sequence: value.task_sequence,
    eventKind: value.event_kind,
    statusAfter: value.status_after,
    ...(value.reason === null ? {} : { reason: value.reason }),
    occurredAt: value.occurred_at,
  }
}

export function adaptProductState(value: ProductStateWire): WorkbenchProductState {
  return {
    state: value.state,
    reasonCode: value.reason_code,
    taskStatus: value.task_status,
    ...(value.publication_status === null ? {} : { publicationStatus: value.publication_status }),
    reportAvailable: value.report_available,
    ...(value.evidence_revision === null ? {} : { evidenceRevision: value.evidence_revision }),
    ...(value.evidence_freshness === null ? {} : { evidenceFreshness: value.evidence_freshness }),
    ...(value.evidence_disposition === null ? {} : { evidenceDisposition: value.evidence_disposition }),
  }
}

export function adaptRun(value: RunWire): WorkbenchRun {
  return {
    runtimeStatus: value.runtime_status,
    ...(value.publication_status === null ? {} : { publicationStatus: value.publication_status }),
    terminalReason: value.terminal_reason,
    ...(value.elapsed_ms === null ? {} : { elapsedMs: value.elapsed_ms }),
    reportAvailable: value.report_available,
  }
}

function adaptMetricRow(value: RecentMetricRowWire): WorkbenchRecentMetricRow {
  return {
    csPerMinute: value.cs_per_min,
    goldPerMinute: value.gold_per_min,
    damagePerMinute: value.damage_per_min,
    visionScore: value.vision_score,
    deathsBefore15: value.deaths_before_15,
  }
}

export function adaptRecentSummary(value: RecentSummaryWire): WorkbenchRecentSummary {
  return {
    gamesAnalyzed: value.games_analyzed,
    wins: value.wins,
    losses: value.losses,
    winRate: value.win_rate,
    mainRole: value.main_role,
    mainChampions: value.main_champions,
    averages: {
      ...adaptMetricRow(value.averages),
      kda: value.averages.kda,
      killParticipationPercent: value.averages.kill_participation_percent,
      damageSharePercent: value.averages.damage_share_percent,
      goldSharePercent: value.averages.gold_share_percent,
    },
    winLossComparison: {
      wins: adaptMetricRow(value.win_loss_comparison.wins),
      losses: adaptMetricRow(value.win_loss_comparison.losses),
    },
  }
}

function adaptSources(value: EvidenceSnapshotWire): readonly WorkbenchEvidenceSource[] {
  const { sources } = value.projection
  return [
    {
      sourceKind: "riot_official",
      label: sourceLabels.riot_official,
      status: sources.riot_official.match_count > 0 ? "verified" : "unavailable",
      freshness: sources.riot_official.freshness,
      detail: sources.riot_official.match_count > 0
        ? `${sources.riot_official.match_count} typed Riot match projection${sources.riot_official.match_count === 1 ? "" : "s"}.`
        : "No Riot match projection is available.",
    },
    {
      sourceKind: "data_dragon",
      label: sourceLabels.data_dragon,
      status: sources.data_dragon.version === null ? "unavailable" : "verified",
      freshness: sources.data_dragon.freshness,
      detail: sources.data_dragon.version === null
        ? "No versioned static catalog is attached."
        : `Version ${sources.data_dragon.version} is attached to the evidence bundle.`,
    },
    {
      sourceKind: "riot_patch",
      label: sourceLabels.riot_patch,
      status: sources.riot_patch.patch_version === null ? "unavailable" : "verified",
      freshness: sources.riot_patch.freshness,
      detail: sources.riot_patch.patch_version === null
        ? "No official patch projection is attached."
        : `Official patch ${sources.riot_patch.patch_version} is attached.`,
    },
    {
      sourceKind: "opgg",
      label: sourceLabels.opgg,
      status: sources.opgg.evidence_count === 0
        ? "unavailable"
        : sources.opgg.provenance.every((item) => item === "complete")
          ? "verified"
          : "partial",
      freshness: sources.opgg.freshness,
      detail: sources.opgg.evidence_count === 0
        ? "No OP.GG Meta snapshot is attached."
        : `${sources.opgg.evidence_count} typed OP.GG snapshot${sources.opgg.evidence_count === 1 ? "" : "s"}; provenance remains explicit.`,
    },
  ]
}

export function adaptEvidence(value: EvidenceSnapshotWire): WorkbenchEvidence {
  return {
    revision: value.revision,
    bundleDigest: value.bundle_digest,
    snapshotDigest: value.snapshot_digest,
    freshness: value.freshness,
    disposition: value.bundle_disposition,
    confidence: value.confidence,
    claims: value.usable_claims,
    sources: adaptSources(value),
    joins: value.projection.joins.map((join) => ({
      label: `${join.key.champion_name} · ${join.key.position}`,
      status: join.status,
      detail: `Sources present: ${Object.entries(join.sources_present).filter(([, present]) => present).map(([source]) => source.replaceAll("_", " ")).join(", ") || "none"}.`,
    })),
    gaps: value.projection.gaps.map((gap) => ({
      code: gap.code,
      ...(gapCopy[gap.code] ?? {
        summary: "Evidence limitation",
        impact: `The ${gap.source.replaceAll("_", " ")} source cannot support this claim.`,
      }),
    })),
  }
}

export function adaptTraining(
  profile: PlayerProfileWire,
  plans: TrainingPlanPageWire | undefined,
  progress: TrainingProgressPageWire | undefined,
): WorkbenchTraining | undefined {
  if (profile.relationship_role === "observed") {
    return {
      mode: "learning_observation",
      readOnly: true,
      note: "Public observed profiles are read-only; private training state is never inferred.",
    }
  }
  const plan = plans?.plans.find((item) => item.status === "active")
  if (plan === undefined) return undefined
  const specification = plan.payload.metrics[0]
  const trend = specification === undefined
    ? undefined
    : progress?.trends.find((item) => item.metric_key === specification.metric_key)
  return {
    mode: "personal",
    title: plan.payload.title,
    objective: plan.payload.objective,
    ...(specification === undefined ? {} : {
      metric: {
        metricKey: specification.metric_key,
        ...(specification.baseline === undefined ? {} : { baseline: specification.baseline }),
        ...(specification.target === undefined ? {} : { target: specification.target }),
        ...(trend?.comparison.current_value === null || trend?.comparison.current_value === undefined
          ? {}
          : { current: trend.comparison.current_value }),
        unit: specification.unit,
        trend: trend?.comparison.trend ?? "insufficient_data",
        sampleCount: trend?.comparison.sample_count ?? 0,
      },
    }),
  }
}

const fixtureEventKinds: Readonly<Record<TaskEventFixture["eventKind"], WorkbenchTaskEvent["eventKind"]>> = {
  task_created: "created",
  task_claimed: "claimed",
  task_completed: "succeeded",
  task_failed: "failed",
  cancel_requested: "cancel_requested",
  task_cancelled: "cancelled",
  recovery_required: "recovery_required",
}

export function adaptFixtureWorkbench(
  fixture: ReviewWorkbenchFixture,
  selectedProfileId = fixture.selectedProfileId,
): LiveWorkbenchView {
  const selected = fixture.profiles.find((profile) => profile.playerProfileId === selectedProfileId)
    ?? fixture.profiles[0]
  if (selected === undefined) throw new Error("fixture profile is unavailable")
  const profiles: readonly WorkbenchPlayerProfile[] = fixture.profiles.map((profile) => ({
    playerProfileId: profile.playerProfileId,
    riotId: profile.riotId,
    routingRegion: profile.routingRegion,
    relationshipRole: profile.relationshipRole,
    verificationStatus: profile.verificationStatus,
    lastResolvedAt: profile.lastResolvedAt,
  }))
  const fixtureTraining = fixture.trainingByProfile[selected.playerProfileId]
  const training: WorkbenchTraining | undefined = fixtureTraining?.mode === "personal"
    ? {
        mode: "personal",
        title: fixtureTraining.title,
        objective: fixtureTraining.focus,
      }
    : fixtureTraining?.mode === "learning_observation"
      ? {
          mode: "learning_observation",
          readOnly: true,
          note: fixtureTraining.note,
        }
      : undefined

  const base: LiveWorkbenchView = {
    profiles,
    selectedProfileId: selected.playerProfileId,
    events: [],
    ...(training === undefined ? {} : { training }),
  }
  if (selected.playerProfileId !== fixture.selectedProfileId) return base

  const productState: WorkbenchProductState = {
    state: fixture.productState.state,
    reasonCode: fixture.productState.reasonCode,
    taskStatus: fixture.productState.taskStatus,
    ...(fixture.productState.publicationStatus === undefined ? {} : { publicationStatus: fixture.productState.publicationStatus }),
    reportAvailable: fixture.productState.reportAvailable,
    ...(fixture.productState.evidenceRevision === undefined ? {} : { evidenceRevision: fixture.productState.evidenceRevision }),
    ...(fixture.productState.evidenceFreshness === undefined ? {} : { evidenceFreshness: fixture.productState.evidenceFreshness }),
    ...(fixture.productState.evidenceDisposition === undefined ? {} : { evidenceDisposition: fixture.productState.evidenceDisposition }),
  }
  const events: readonly WorkbenchTaskEvent[] = fixture.events.map((event, index) => ({
    cursor: index + 1,
    sequence: event.sequence,
    eventKind: fixtureEventKinds[event.eventKind],
    statusAfter: event.statusAfter,
    ...(event.reason === undefined ? {} : { reason: event.reason }),
    occurredAt: event.occurredAt,
  }))
  const run = fixture.run?.runtimeStatus === "completed" || fixture.run?.runtimeStatus === "failed"
    ? {
        runtimeStatus: fixture.run.runtimeStatus,
        ...(fixture.run.publicationStatus === undefined ? {} : { publicationStatus: fixture.run.publicationStatus }),
        terminalReason: fixture.run.terminalReason,
        ...(fixture.run.elapsedMs === undefined ? {} : { elapsedMs: fixture.run.elapsedMs }),
        reportAvailable: fixture.run.reportAvailable,
      } satisfies WorkbenchRun
    : undefined
  return {
    ...base,
    productState,
    ...(fixture.summary === undefined ? {} : { summary: fixture.summary }),
    ...(run === undefined ? {} : { run }),
    ...(fixture.report === undefined ? {} : { report: { markdown: fixture.report.markdown } }),
    ...(fixture.evidence === undefined ? {} : { evidence: fixture.evidence }),
    events,
  }
}

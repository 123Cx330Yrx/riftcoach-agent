import {
  assertPublicWorkbenchFixture,
  freezeWorkbenchFixture,
  type CoachReportFixture,
  type EvidenceFixture,
  type PlayerProfileFixture,
  type RecentSummaryFixture,
  type ReviewWorkbenchFixture,
  type TaskEventFixture,
  type WorkbenchTimeline,
  type WorkbenchScenarioName,
  type WorkbenchScreenState,
} from "../contracts/workbench";

const profiles = freezeWorkbenchFixture([
  {
    playerProfileId: "profile-riverline-euw",
    riotId: "Riverline#EUW",
    routingRegion: "europe",
    relationshipRole: "self",
    verificationStatus: "unverified_claim",
    trainingView: "personal",
    lastResolvedAt: "2026-08-21T18:20:00Z",
  },
  {
    playerProfileId: "profile-northstar-kr",
    riotId: "Northstar#KR",
    routingRegion: "asia",
    relationshipRole: "public_observed",
    verificationStatus: "not_applicable",
    trainingView: "learning_observation",
    lastResolvedAt: "2026-08-20T12:05:00Z",
  },
] as const satisfies readonly PlayerProfileFixture[]);

const summary = freezeWorkbenchFixture({
  gamesAnalyzed: 8,
  wins: 5,
  losses: 3,
  winRate: 62.5,
  mainRole: "Middle",
  mainChampions: ["Orianna", "Ahri", "Syndra"],
  averages: {
    kda: 3.42,
    csPerMinute: 7.8,
    goldPerMinute: 412,
    damagePerMinute: 623,
    visionScore: 24.6,
    killParticipationPercent: 68.4,
    damageSharePercent: 27.8,
    goldSharePercent: 24.2,
    deathsBefore15: 0.75,
  },
  winLossComparison: {
    wins: {
      csPerMinute: 8.1,
      goldPerMinute: 438,
      damagePerMinute: 674,
      visionScore: 26.2,
      deathsBefore15: 0.4,
    },
    losses: {
      csPerMinute: 7.3,
      goldPerMinute: 369,
      damagePerMinute: 538,
      visionScore: 21.9,
      deathsBefore15: 1.3,
    },
  },
} as const satisfies RecentSummaryFixture);

const timeline = freezeWorkbenchFixture({
  source: "riot_match_v5_timeline",
  timelineStatus: "available",
  totalMatches: 3,
  projectedMatches: 3,
  matchesTruncated: false,
  matches: [
    {
      matchId: "EUW1_FIXTURE_001",
      championName: "Orianna",
      role: "MIDDLE",
      win: true,
      gameDurationSeconds: 2052,
      includedInAggregate: true,
      timelineStatus: "available",
      totalEvents: 7,
      projectedEvents: 7,
      eventsTruncated: false,
      events: [
        { eventKind: "item_purchase", atSeconds: 246, phase: "early", label: "Lost Chapter", itemId: 3802 },
        { eventKind: "death", atSeconds: 562, phase: "early", label: "Death" },
        { eventKind: "objective", atSeconds: 714, phase: "early", label: "Dragon secured" },
        { eventKind: "item_purchase", atSeconds: 1028, phase: "mid", label: "Archangel's Staff", itemId: 3003 },
        { eventKind: "objective", atSeconds: 1242, phase: "mid", label: "Rift Herald secured" },
        { eventKind: "death", atSeconds: 1584, phase: "late", label: "Death" },
        { eventKind: "objective", atSeconds: 1818, phase: "late", label: "Baron Nashor secured" },
      ],
    },
    {
      matchId: "EUW1_FIXTURE_002",
      championName: "Ahri",
      role: "MIDDLE",
      win: false,
      gameDurationSeconds: 1660,
      includedInAggregate: true,
      timelineStatus: "available",
      totalEvents: 5,
      projectedEvents: 5,
      eventsTruncated: false,
      events: [
        { eventKind: "item_purchase", atSeconds: 312, phase: "early", label: "Hextech Alternator", itemId: 3145 },
        { eventKind: "death", atSeconds: 648, phase: "early", label: "Death" },
        { eventKind: "objective", atSeconds: 986, phase: "mid", label: "Dragon secured" },
        { eventKind: "death", atSeconds: 1324, phase: "mid", label: "Death" },
        { eventKind: "objective", atSeconds: 1540, phase: "late", label: "Baron Nashor secured" },
      ],
    },
    {
      matchId: "EUW1_FIXTURE_003",
      championName: "Syndra",
      role: "MIDDLE",
      win: true,
      gameDurationSeconds: 1335,
      includedInAggregate: true,
      timelineStatus: "available",
      totalEvents: 4,
      projectedEvents: 4,
      eventsTruncated: false,
      events: [
        { eventKind: "item_purchase", atSeconds: 280, phase: "early", label: "Lost Chapter", itemId: 3802 },
        { eventKind: "objective", atSeconds: 702, phase: "early", label: "Dragon secured" },
        { eventKind: "item_purchase", atSeconds: 1016, phase: "mid", label: "Luden's Companion", itemId: 6655 },
        { eventKind: "objective", atSeconds: 1266, phase: "mid", label: "Rift Herald secured" },
      ],
    },
  ],
} as const satisfies WorkbenchTimeline);

const report = freezeWorkbenchFixture({
  title: "Tempo before the second objective",
  verdict: "Stable lane control; conversion timing is the next ceiling.",
  summary:
    "Your recent sample shows reliable farm and damage share. The largest controllable gap is moving first after a won mid-wave.",
  strengths: [
    "Farm stays above the recent baseline in both wins and losses.",
    "Vision contribution rises in winning games without sacrificing damage.",
  ],
  priorities: [
    "Call the next wave state before leaving lane.",
    "Tie the first move to a named objective instead of roaming on instinct.",
  ],
  nextSession:
    "For three games, record whether the wave was neutral, pushing, or crashed before every river move.",
  markdown:
    "## Coach brief\n\nProtect your farm baseline, then make every early river move answer one question: **what objective does this wave buy?**",
} as const satisfies CoachReportFixture);

const publishedEvidence = freezeWorkbenchFixture({
  revision: 3,
  bundleDigest:
    "2dc4286315079443e75695da8ca546e96f4b37efad67770aed3844512821a1c4",
  snapshotDigest:
    "319cad6aa8053c6cd9b596a1e6c906bf3118a4cd68b8e6ecb77fd2d4df639d71",
  freshness: "current",
  disposition: "complete",
  confidence: "high",
  claims: [
    "riot_match_facts",
    "data_dragon_static",
    "official_patch_facts",
    "current_meta_recommendation",
    "exact_patch_meta_comparison",
  ],
  sources: [
    {
      sourceKind: "riot_official",
      label: "Riot Match API",
      status: "verified",
      freshness: "current",
      detail: "Eight aggregate review games passed the typed Riot projection.",
    },
    {
      sourceKind: "data_dragon",
      label: "Data Dragon catalog",
      status: "verified",
      freshness: "current",
      detail: "Champion labels are tied to the review patch catalog.",
    },
    {
      sourceKind: "riot_patch",
      label: "Official patch facts",
      status: "verified",
      freshness: "current",
      detail: "The review patch matches the official update projection.",
    },
    {
      sourceKind: "opgg",
      label: "OP.GG meta snapshot",
      status: "verified",
      freshness: "current",
      detail: "The typed meta projection is usable for this synthetic state.",
    },
  ],
  joins: [
    {
      label: "Review patch → official patch",
      status: "joined",
      detail: "Both projections identify the same patch line.",
    },
    {
      label: "Champion → current meta",
      status: "joined",
      detail: "The selected champion appears in the compatible meta snapshot.",
    },
  ],
  gaps: [],
} as const satisfies EvidenceFixture);

const degradedEvidence = freezeWorkbenchFixture({
  ...publishedEvidence,
  snapshotDigest:
    "7fe79ea7d13eb7ea03e3145759e872aa53961f224e34d929525367a69155482b",
  freshness: "expired",
  disposition: "degraded",
  confidence: "medium",
  claims: [
    "riot_match_facts",
    "data_dragon_static",
    "official_patch_facts",
  ],
  sources: publishedEvidence.sources.map((source) =>
    source.sourceKind === "opgg"
      ? {
          ...source,
          status: "partial" as const,
          freshness: "unknown" as const,
          detail:
            "Meta remains a current-snapshot hint; exact upstream time is unavailable.",
        }
      : source,
  ),
  joins: [
    publishedEvidence.joins[0],
    {
      label: "Champion → current meta",
      status: "unjoined",
      detail: "The reviewed champion is absent from the bounded meta projection.",
    },
  ],
  gaps: [
    {
      code: "meta_join_unavailable",
      summary: "No exact champion-to-meta join is available.",
      impact: "Meta recommendations stay advisory and cannot support patch claims.",
    },
  ],
} as const satisfies EvidenceFixture);

const completedEvents = freezeWorkbenchFixture([
  {
    sequence: 1,
    eventKind: "task_created",
    statusAfter: "queued",
    occurredAt: "2026-08-22T09:12:00Z",
  },
  {
    sequence: 2,
    eventKind: "task_claimed",
    statusAfter: "running",
    occurredAt: "2026-08-22T09:12:04Z",
  },
  {
    sequence: 3,
    eventKind: "task_completed",
    statusAfter: "succeeded",
    reason: "review_terminal_committed",
    occurredAt: "2026-08-22T09:12:47Z",
  },
] as const satisfies readonly TaskEventFixture[]);

const activeEvents = freezeWorkbenchFixture([
  {
    sequence: 1,
    eventKind: "task_created",
    statusAfter: "queued",
    occurredAt: "2026-08-23T08:30:00Z",
  },
  {
    sequence: 2,
    eventKind: "task_claimed",
    statusAfter: "running",
    occurredAt: "2026-08-23T08:30:03Z",
  },
] as const satisfies readonly TaskEventFixture[]);

const trainingByProfile = freezeWorkbenchFixture({
  "profile-riverline-euw": {
    mode: "personal",
    title: "Objective-first movement",
    focus: "Name the wave state before every early river move.",
    completedSessions: 2,
    targetSessions: 5,
    completionPercent: 40,
    metricLabel: "Early deaths per game",
    metricValue: "0.75",
    trend: "improving",
    nextAction: "Complete three more reviewed games with a wave-state note.",
  },
  "profile-northstar-kr": {
    mode: "learning_observation",
    readOnly: true,
    title: "Learning observation",
    note:
      "This public profile is for studying repeatable choices, not personal training completion.",
    focusPoints: [
      "Track how the player creates a safe first move.",
      "Compare objective setup without inferring private intent.",
    ],
  },
} as const);

export const publishedWorkbenchFixture = freezeWorkbenchFixture({
  schemaVersion: "1.0",
  fixture_mode: true,
  disclosure:
    "Invented accounts and synthetic review evidence · no live API",
  profiles,
  selectedProfileId: "profile-riverline-euw",
  task: {
    status: "succeeded",
    statusLabel: "Review complete",
    createdAt: "2026-08-22T09:12:00Z",
    updatedAt: "2026-08-22T09:12:47Z",
  },
  productState: {
    state: "published",
    reasonCode: "ready",
    taskStatus: "succeeded",
    publicationStatus: "published",
    reportAvailable: true,
    evidenceRevision: 3,
    evidenceFreshness: "current",
    evidenceDisposition: "complete",
  },
  summary,
  timeline,
  run: {
    runtimeStatus: "completed",
    publicationStatus: "published",
    terminalReason: "published_after_quality_gate",
    elapsedMs: 47_218,
    reportAvailable: true,
  },
  report,
  evidence: publishedEvidence,
  events: completedEvents,
  trainingByProfile,
} as const satisfies ReviewWorkbenchFixture);

assertPublicWorkbenchFixture(publishedWorkbenchFixture);

const degradedWorkbenchFixture = freezeWorkbenchFixture({
  ...publishedWorkbenchFixture,
  timeline: {
    ...timeline,
    timelineStatus: "partial",
    matches: [
      timeline.matches[0],
      {
        ...timeline.matches[1],
        timelineStatus: "unavailable",
        unavailableReason: "source_unavailable",
        totalEvents: 0,
        projectedEvents: 0,
        events: [],
      },
      timeline.matches[2],
    ],
  },
  productState: {
    state: "degraded",
    reasonCode: "evidence_expired",
    taskStatus: "succeeded",
    publicationStatus: "degraded",
    reportAvailable: true,
    evidenceRevision: 2,
    evidenceFreshness: "expired",
    evidenceDisposition: "degraded",
  },
  run: {
    ...publishedWorkbenchFixture.run,
    publicationStatus: "degraded",
    terminalReason: "deterministic_report_with_evidence_limit",
  },
  report: {
    ...report,
    verdict: "Useful review, with an explicit evidence freshness limit.",
  },
  evidence: degradedEvidence,
} as const satisfies ReviewWorkbenchFixture);

assertPublicWorkbenchFixture(degradedWorkbenchFixture);

const rejectedWorkbenchFixture = freezeWorkbenchFixture({
  schemaVersion: "1.0",
  fixture_mode: true,
  disclosure: publishedWorkbenchFixture.disclosure,
  profiles,
  selectedProfileId: "profile-riverline-euw",
  task: publishedWorkbenchFixture.task,
  productState: {
    state: "rejected",
    reasonCode: "quality_rejected",
    taskStatus: "succeeded",
    publicationStatus: "rejected",
    reportAvailable: false,
    evidenceRevision: 3,
    evidenceFreshness: "current",
    evidenceDisposition: "complete",
  },
  summary,
  run: {
    runtimeStatus: "completed",
    publicationStatus: "rejected",
    terminalReason: "quality_gate_rejected",
    elapsedMs: 45_904,
    reportAvailable: false,
  },
  evidence: publishedEvidence,
  events: completedEvents,
  trainingByProfile,
} as const satisfies ReviewWorkbenchFixture);

assertPublicWorkbenchFixture(rejectedWorkbenchFixture);

const notReadyWorkbenchFixture = freezeWorkbenchFixture({
  schemaVersion: "1.0",
  fixture_mode: true,
  disclosure: publishedWorkbenchFixture.disclosure,
  profiles,
  selectedProfileId: "profile-riverline-euw",
  task: {
    status: "running",
    statusLabel: "Review in progress",
    createdAt: "2026-08-23T08:30:00Z",
    updatedAt: "2026-08-23T08:30:03Z",
  },
  productState: {
    state: "not_ready",
    reasonCode: "task_pending",
    taskStatus: "running",
    reportAvailable: false,
  },
  run: {
    runtimeStatus: "running",
    terminalReason: "task_in_progress",
    reportAvailable: false,
  },
  events: activeEvents,
  trainingByProfile: {},
} as const satisfies ReviewWorkbenchFixture);

assertPublicWorkbenchFixture(notReadyWorkbenchFixture);

export const workbenchScenarios = freezeWorkbenchFixture({
  published: {
    fixture_mode: true,
    client: "ready",
    data: publishedWorkbenchFixture,
  },
  degraded: {
    fixture_mode: true,
    client: "ready",
    data: degradedWorkbenchFixture,
  },
  rejected: {
    fixture_mode: true,
    client: "ready",
    data: rejectedWorkbenchFixture,
  },
  not_ready: {
    fixture_mode: true,
    client: "ready",
    data: notReadyWorkbenchFixture,
  },
  loading: {
    fixture_mode: true,
    client: "loading",
    message: "Preparing the fixture-backed command center…",
  },
  empty: {
    fixture_mode: true,
    client: "empty",
    message: "No player profiles are available in this fixture scenario.",
    actionLabel: "Add a player profile later",
  },
  error: {
    fixture_mode: true,
    client: "error",
    code: "fixture_load_failed",
    message: "The fixture preview could not be loaded.",
  },
} as const satisfies Record<WorkbenchScenarioName, WorkbenchScreenState>);

const unknownScenario = freezeWorkbenchFixture({
  fixture_mode: true,
  client: "error",
  code: "fixture_scenario_unknown",
  message: "This fixture scenario is not available.",
} as const satisfies WorkbenchScreenState);

function isWorkbenchScenarioName(value: string): value is WorkbenchScenarioName {
  return Object.prototype.hasOwnProperty.call(workbenchScenarios, value);
}

export function resolveWorkbenchScenario(
  scenario?: string | null,
): WorkbenchScreenState {
  const normalized = scenario?.trim() ?? "";
  if (normalized.length === 0) {
    return workbenchScenarios.published;
  }
  return isWorkbenchScenarioName(normalized)
    ? workbenchScenarios[normalized]
    : unknownScenario;
}

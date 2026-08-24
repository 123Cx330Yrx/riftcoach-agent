import type {
  EvidenceClaimWire,
  EvidenceConfidenceWire,
  EvidenceDispositionWire,
  ProductStateReasonWire,
  ProductStateValueWire,
  PublicationStatusWire,
  RoutingRegionWire,
  TaskEventKindWire,
  TaskStatusWire,
  VerificationStatusWire,
} from "../api/wire"

export interface WorkbenchPlayerProfile {
  readonly playerProfileId: string
  readonly riotId: string
  readonly routingRegion: RoutingRegionWire
  readonly relationshipRole: "self" | "public_observed"
  readonly verificationStatus: VerificationStatusWire
  readonly lastResolvedAt: string
}

export interface WorkbenchTask {
  readonly taskId: string
  readonly runId: string
  readonly status: TaskStatusWire
  readonly createdAt: string
  readonly updatedAt: string
  readonly terminalReason?: string
}

export interface WorkbenchRun {
  readonly runtimeStatus: "completed" | "failed"
  readonly publicationStatus?: PublicationStatusWire
  readonly terminalReason: string
  readonly elapsedMs?: number
  readonly reportAvailable: boolean
}

export interface WorkbenchProductState {
  readonly state: ProductStateValueWire
  readonly reasonCode: ProductStateReasonWire
  readonly taskStatus: TaskStatusWire
  readonly publicationStatus?: PublicationStatusWire
  readonly reportAvailable: boolean
  readonly evidenceRevision?: number
  readonly evidenceFreshness?: "current" | "expired"
  readonly evidenceDisposition?: EvidenceDispositionWire
}

export interface WorkbenchRecentMetricRow {
  readonly csPerMinute: number
  readonly goldPerMinute: number
  readonly damagePerMinute: number
  readonly visionScore: number
  readonly deathsBefore15: number
}

export interface WorkbenchRecentSummary {
  readonly gamesAnalyzed: number
  readonly wins: number
  readonly losses: number
  readonly winRate: number
  readonly mainRole: string
  readonly mainChampions: readonly string[]
  readonly averages: WorkbenchRecentMetricRow & {
    readonly kda: number
    readonly killParticipationPercent: number
    readonly damageSharePercent: number
    readonly goldSharePercent: number
  }
  readonly winLossComparison: {
    readonly wins: WorkbenchRecentMetricRow
    readonly losses: WorkbenchRecentMetricRow
  }
}

export interface WorkbenchTimelineEvent {
  readonly eventKind: "death" | "item_purchase" | "objective"
  readonly atSeconds: number
  readonly phase: "early" | "mid" | "late"
  readonly label: string
  readonly itemId?: number
}

export interface WorkbenchTimelineMatch {
  readonly matchId: string
  readonly championName: string
  readonly role: string
  readonly win: boolean
  readonly gameDurationSeconds: number
  readonly includedInAggregate: boolean
  readonly timelineStatus: "available" | "unavailable"
  readonly unavailableReason?: "source_unavailable"
  readonly totalEvents: number
  readonly projectedEvents: number
  readonly eventsTruncated: boolean
  readonly events: readonly WorkbenchTimelineEvent[]
}

export interface WorkbenchTimeline {
  readonly source: "riot_match_v5_timeline"
  readonly timelineStatus: "available" | "partial" | "unavailable"
  readonly totalMatches: number
  readonly projectedMatches: number
  readonly matchesTruncated: boolean
  readonly matches: readonly WorkbenchTimelineMatch[]
}

export interface WorkbenchCoachReport {
  readonly markdown: string
}

export interface WorkbenchEvidenceSource {
  readonly sourceKind: "riot_official" | "data_dragon" | "riot_patch" | "opgg"
  readonly status: "verified" | "partial" | "unavailable"
  readonly freshness: "current" | "stale" | "unknown" | "expired"
  readonly matchCount?: number
  readonly version?: string
  readonly patchVersion?: string
  readonly evidenceCount?: number
  readonly provenanceComplete?: boolean
}

export interface WorkbenchEvidence {
  readonly revision: number
  readonly bundleDigest: string
  readonly snapshotDigest: string
  readonly freshness: "current" | "expired"
  readonly disposition: EvidenceDispositionWire
  readonly confidence: EvidenceConfidenceWire
  readonly claims: readonly EvidenceClaimWire[]
  readonly sources: readonly WorkbenchEvidenceSource[]
  readonly joins: readonly {
    readonly labelCode: "review_patch_official_patch" | "champion_current_meta" | "champion_position"
    readonly championName?: string
    readonly position?: "top" | "mid" | "jungle" | "adc" | "support"
    readonly status: "joined" | "joined_partial" | "unjoined" | "stale" | "conflict"
    readonly sourcesPresent: readonly WorkbenchEvidenceSource["sourceKind"][]
  }[]
  readonly gaps: readonly {
    readonly code: string
    readonly sourceKind?: WorkbenchEvidenceSource["sourceKind"]
  }[]
}

export interface WorkbenchTaskEvent {
  readonly cursor: number
  readonly sequence: number
  readonly eventKind: TaskEventKindWire
  readonly statusAfter: TaskStatusWire
  readonly reason?: string
  readonly occurredAt: string
}

export type WorkbenchTraining =
  | {
      readonly mode: "personal"
      readonly title: string
      readonly objective: string
      readonly metric?: {
        readonly metricKey: string
        readonly baseline?: number
        readonly target?: number
        readonly current?: number
        readonly unit: "count" | "ratio" | "percent" | "seconds" | "score"
        readonly trend: "improving" | "declining" | "stable" | "insufficient_data"
        readonly sampleCount: number
      }
    }
  | {
      readonly mode: "learning_observation"
      readonly readOnly: true
      readonly noteCode: "public_observed_read_only"
    }

export interface LiveWorkbenchView {
  readonly profiles: readonly WorkbenchPlayerProfile[]
  readonly selectedProfileId: string
  readonly task?: WorkbenchTask
  readonly productState?: WorkbenchProductState
  readonly summary?: WorkbenchRecentSummary
  readonly timeline?: WorkbenchTimeline
  readonly run?: WorkbenchRun
  readonly report?: WorkbenchCoachReport
  readonly evidence?: WorkbenchEvidence
  readonly events: readonly WorkbenchTaskEvent[]
  readonly training?: WorkbenchTraining
}

export type WorkbenchClientMessageCode =
  | "profiles_loading"
  | "selected_review_loading"
  | "fixture_loading"
  | "profiles_empty"
  | "workbench_load_failed"
  | "selected_profile_unavailable"
  | "profile_projection_invalid"
  | "fixture_unavailable"

export type LiveWorkbenchScreenState =
  | { readonly client: "loading"; readonly messageCode: WorkbenchClientMessageCode }
  | { readonly client: "empty"; readonly messageCode: WorkbenchClientMessageCode }
  | { readonly client: "ready"; readonly data: LiveWorkbenchView }
  | { readonly client: "error"; readonly code: string; readonly messageCode: WorkbenchClientMessageCode }

export type RoutingRegionWire = "americas" | "asia" | "europe" | "sea"
export type RelationshipRoleWire = "self" | "observed"
export type VerificationStatusWire =
  | "unverified_claim"
  | "not_applicable"
  | "rso_verified"
export type TaskStatusWire =
  | "queued"
  | "running"
  | "recovery_required"
  | "succeeded"
  | "failed"
  | "cancelled"
export type PublicationStatusWire = "published" | "degraded" | "rejected"
export type ProductStateValueWire =
  | "published"
  | "degraded"
  | "rejected"
  | "not_ready"
export type ProductStateReasonWire =
  | "ready"
  | "task_pending"
  | "recovery_required"
  | "task_failed"
  | "task_cancelled"
  | "quality_rejected"
  | "quality_degraded"
  | "evidence_not_available"
  | "evidence_expired"
  | "evidence_degraded"
  | "evidence_rejected"
export type EvidenceFreshnessWire = "current" | "stale" | "unknown" | "expired"
export type EvidenceDispositionWire = "complete" | "degraded" | "rejected"
export type EvidenceConfidenceWire = "high" | "medium" | "low" | "unknown"
export type EvidenceClaimWire =
  | "riot_match_facts"
  | "data_dragon_static"
  | "official_patch_facts"
  | "current_meta_recommendation"
  | "exact_patch_meta_comparison"
export type EvidenceSourceWire =
  | "riot_official"
  | "data_dragon"
  | "riot_patch"
  | "opgg"

export interface PlayerProfileWire {
  readonly schema_version: "1.0"
  readonly player_profile_id: string
  readonly riot_id: string
  readonly routing_region: RoutingRegionWire
  readonly relationship_role: RelationshipRoleWire
  readonly verification_status: VerificationStatusWire
  readonly last_resolved_at: string
}

export interface PlayerProfilePageWire {
  readonly schema_version: "1.0"
  readonly profiles: readonly PlayerProfileWire[]
  readonly limit: number
}

export interface LatestReviewLinksWire {
  readonly task: string
  readonly events: string
  readonly stream: string
  readonly run: string
  readonly summary: string
  readonly timeline: string
  readonly report: string
  readonly product_state: string
  readonly evidence: string
}

export interface LatestReviewItemWire {
  readonly task_id: string
  readonly run_id: string
  readonly status: TaskStatusWire
  readonly created_at: string
  readonly updated_at: string
  readonly publication_status: PublicationStatusWire | null
  readonly report_available: boolean
  readonly links: LatestReviewLinksWire
}

export interface LatestProfileReviewWire {
  readonly schema_version: "1.0"
  readonly player_profile_id: string
  readonly latest_review: LatestReviewItemWire | null
}

export interface TaskWire {
  readonly schema_version: "1.0" | "2.0"
  readonly task_id: string
  readonly run_id: string
  readonly status: TaskStatusWire
  readonly created_at: string
  readonly updated_at: string
  readonly claimed_at: string | null
  readonly finished_at: string | null
  readonly terminal_reason: string | null
  readonly publication_status: PublicationStatusWire | null
  readonly report_available: boolean
}

export type TaskEventKindWire =
  | "created"
  | "claimed"
  | "execution_started"
  | "heartbeat"
  | "cancel_requested"
  | "checkpoint_saved"
  | "recovery_required"
  | "requeued"
  | "succeeded"
  | "failed"
  | "cancelled"

export interface TaskEventWire {
  readonly event_schema_version: "1.0"
  readonly event_cursor: number
  readonly event_identity: string
  readonly task_id: string
  readonly run_id: string
  readonly task_sequence: number
  readonly event_kind: TaskEventKindWire
  readonly status_after: TaskStatusWire
  readonly lease_generation: number
  readonly reason: string | null
  readonly occurred_at: string
}

export interface TaskEventPageWire {
  readonly schema_version: "1.0"
  readonly task_id: string
  readonly after_cursor: number
  readonly next_cursor: number
  readonly limit: number
  readonly has_more: boolean
  readonly events: readonly TaskEventWire[]
}

export interface ProductStateWire {
  readonly schema_version: "1.0"
  readonly task_id: string
  readonly run_id: string
  readonly state: ProductStateValueWire
  readonly reason_code: ProductStateReasonWire
  readonly task_status: TaskStatusWire
  readonly publication_status: PublicationStatusWire | null
  readonly report_available: boolean
  readonly evidence_revision: number | null
  readonly evidence_bundle_digest: string | null
  readonly evidence_freshness: "current" | "expired" | null
  readonly evidence_disposition: EvidenceDispositionWire | null
}

export interface RuntimeUsageWire {
  readonly provider_calls_attempted: number
  readonly provider_responses_observed: number
  readonly observed_input_tokens: number
  readonly observed_output_tokens: number
  readonly input_tokens: number | null
  readonly output_tokens: number | null
  readonly token_observation: "complete" | "partial" | "unknown" | "not_applicable"
  readonly tool_calls: number
  readonly tool_attempts: number
  readonly tool_latency_ms: number
  readonly cost: string | null
  readonly currency: string | null
  readonly pricing_profile_id: string | null
  readonly pricing_profile_version: string | null
  readonly cost_observation: "complete" | "partial" | "unknown" | "not_configured"
}

export interface RunWire {
  readonly schema_version: "1.0"
  readonly run_id: string
  readonly runtime_status: "completed" | "failed"
  readonly publication_status: PublicationStatusWire | null
  readonly terminal_reason: string
  readonly skill_name: string | null
  readonly skill_version: string | null
  readonly prompt_profile_id: string | null
  readonly prompt_profile_version: string | null
  readonly started_at_utc: string | null
  readonly completed_at_utc: string | null
  readonly elapsed_ms: number | null
  readonly usage: RuntimeUsageWire | null
  readonly report_available: boolean
}

export interface RecentMetricRowWire {
  readonly cs_per_min: number
  readonly gold_per_min: number
  readonly damage_per_min: number
  readonly vision_score: number
  readonly deaths_before_15: number
}

export interface RecentAveragesWire extends RecentMetricRowWire {
  readonly kda: number
  readonly kill_participation_percent: number
  readonly damage_share_percent: number
  readonly gold_share_percent: number
}

export interface RecentSummaryWire {
  readonly schema_version: "1.0"
  readonly run_id: string
  readonly skill_name: "recent-form-review"
  readonly skill_version: string
  readonly runtime_status: "completed"
  readonly publication_status: "published" | "degraded"
  readonly terminal_reason: string
  readonly report_available: true
  readonly games_analyzed: number
  readonly wins: number
  readonly losses: number
  readonly win_rate: number
  readonly main_role: string
  readonly main_champions: readonly string[]
  readonly averages: RecentAveragesWire
  readonly win_loss_comparison: {
    readonly wins: RecentMetricRowWire
    readonly losses: RecentMetricRowWire
  }
}

export type TimelineEventKindWire = "death" | "item_purchase" | "objective"
export type TimelinePhaseWire = "early" | "mid" | "late"

export interface RunTimelineEventWire {
  readonly event_kind: TimelineEventKindWire
  readonly at_seconds: number
  readonly phase: TimelinePhaseWire
  readonly label: string
  readonly item_id: number | null
}

export interface RunTimelineMatchWire {
  readonly match_id: string
  readonly champion_name: string
  readonly role: string
  readonly win: boolean
  readonly game_duration_seconds: number
  readonly included_in_aggregate: boolean
  readonly timeline_status: "available" | "unavailable"
  readonly unavailable_reason: "source_unavailable" | null
  readonly total_events: number
  readonly projected_events: number
  readonly events_truncated: boolean
  readonly events: readonly RunTimelineEventWire[]
}

export interface RunTimelineWire {
  readonly schema_version: "1.0"
  readonly run_id: string
  readonly skill_name: "recent-form-review"
  readonly skill_version: string
  readonly runtime_status: "completed"
  readonly publication_status: "published" | "degraded"
  readonly terminal_reason: string
  readonly source: "riot_match_v5_timeline"
  readonly timeline_status: "available" | "partial" | "unavailable"
  readonly total_matches: number
  readonly projected_matches: number
  readonly matches_truncated: boolean
  readonly matches: readonly RunTimelineMatchWire[]
}

export interface EvidenceJoinKeyWire {
  readonly routing_region: string
  readonly queue_id: number
  readonly position: "top" | "mid" | "jungle" | "adc" | "support"
  readonly champion_name: string
  readonly patch_version: string | null
}

export interface EvidenceProjectionWire {
  readonly schema_version: "1.0"
  readonly bundle_digest: string
  readonly disposition: EvidenceDispositionWire
  readonly confidence: EvidenceConfidenceWire
  readonly claims: readonly EvidenceClaimWire[]
  readonly matches: readonly {
    readonly match_id: string
    readonly champion_name: string
    readonly position: "top" | "mid" | "jungle" | "adc" | "support"
    readonly patch_version: string | null
    readonly win: boolean
    readonly timeline_available: boolean
  }[]
  readonly joins: readonly {
    readonly key: EvidenceJoinKeyWire
    readonly status: "joined" | "joined_partial" | "unjoined" | "stale" | "conflict"
    readonly confidence: EvidenceConfidenceWire
    readonly sources_present: {
      readonly riot: boolean
      readonly data_dragon: boolean
      readonly riot_patch: boolean
      readonly opgg: boolean
    }
  }[]
  readonly conflicts: readonly {
    readonly code: string
    readonly sources: readonly EvidenceSourceWire[]
    readonly key: EvidenceJoinKeyWire | null
  }[]
  readonly gaps: readonly {
    readonly code: string
    readonly source: EvidenceSourceWire
    readonly key: EvidenceJoinKeyWire | null
  }[]
  readonly sources: {
    readonly riot_official: {
      readonly match_count: number
      readonly digests: readonly string[]
      readonly freshness: EvidenceFreshnessWire
    }
    readonly data_dragon: {
      readonly version: string | null
      readonly catalog_digest: string | null
      readonly freshness: EvidenceFreshnessWire
    }
    readonly riot_patch: {
      readonly patch_version: string | null
      readonly source_digest: string | null
      readonly freshness: EvidenceFreshnessWire
    }
    readonly opgg: {
      readonly evidence_count: number
      readonly digests: readonly string[]
      readonly provenance: readonly ("complete" | "partial")[]
      readonly freshness: EvidenceFreshnessWire
    }
  }
}

export interface EvidenceSnapshotWire {
  readonly schema_version: "1.0"
  readonly snapshot_id: string
  readonly task_id: string
  readonly run_id: string
  readonly revision: number
  readonly bundle_digest: string
  readonly snapshot_digest: string
  readonly stored_at: string
  readonly expires_at: string | null
  readonly freshness: "current" | "expired"
  readonly bundle_disposition: EvidenceDispositionWire
  readonly confidence: EvidenceConfidenceWire
  readonly usable_claims: readonly EvidenceClaimWire[]
  readonly projection: EvidenceProjectionWire
}

export interface TrainingMetricSpecificationWire {
  readonly metric_key: string
  readonly direction: "increase" | "decrease" | "maintain"
  readonly unit: "count" | "ratio" | "percent" | "seconds" | "score"
  readonly baseline?: number
  readonly target?: number
  readonly stable_tolerance: number
}

export interface TrainingPlanWire {
  readonly schema_version: "1.0"
  readonly plan_id: string
  readonly relationship_id: string
  readonly version: number
  readonly status: "active" | "completed" | "abandoned" | "superseded"
  readonly payload: {
    readonly title: string
    readonly objective: string
    readonly metrics: readonly TrainingMetricSpecificationWire[]
  }
  readonly supersedes_plan_id: string | null
  readonly created_at: string
  readonly updated_at: string
}

export interface TrainingPlanPageWire {
  readonly schema_version: "1.0"
  readonly plans: readonly TrainingPlanWire[]
}

export interface TrainingProgressWire {
  readonly schema_version: "1.0"
  readonly progress_id: string
  readonly plan_id: string
  readonly relationship_id: string
  readonly metric_key: string
  readonly metric_value: number
  readonly observed_at: string
  readonly source_run_id: string
  readonly source_artifact_sha256: string
  readonly status: "active" | "superseded"
  readonly supersedes_progress_id: string | null
  readonly created_at: string
  readonly updated_at: string
}

export interface TrainingMetricTrendWire {
  readonly metric_key: string
  readonly direction: "increase" | "decrease" | "maintain"
  readonly comparison: {
    readonly trend: "improving" | "declining" | "stable" | "insufficient_data"
    readonly sample_count: number
    readonly previous_value: number | null
    readonly current_value: number | null
    readonly delta: number | null
  }
}

export interface TrainingProgressPageWire {
  readonly schema_version: "1.0"
  readonly events: readonly TrainingProgressWire[]
  readonly trends: readonly TrainingMetricTrendWire[]
}

export interface ExpectedTaskRunBinding {
  readonly taskId: string
  readonly runId: string
}

export interface AuthSessionWire {
  readonly schema_version: "1.0"
  readonly csrf_token: string
  readonly expires_at: string
}

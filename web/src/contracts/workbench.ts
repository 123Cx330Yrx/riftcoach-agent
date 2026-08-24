import type { WorkbenchTimeline } from "../workbench/model";

export type { WorkbenchTimeline };
export type RoutingRegion = "americas" | "asia" | "europe" | "sea";
export type {
  LiveWorkbenchView,
  LiveWorkbenchScreenState,
} from "../workbench/model";
export type RelationshipRole = "self" | "public_observed";
export type VerificationStatus =
  | "unverified_claim"
  | "not_applicable"
  | "rso_verified";
export type TrainingViewMode = "personal" | "learning_observation";

export type ProductStateValue =
  | "published"
  | "degraded"
  | "rejected"
  | "not_ready";
export type ProductState = ProductStateValue;
export type ProductStateReason =
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
  | "evidence_rejected";
export type TaskStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "recovery_required";
export type RuntimeStatus = "pending" | "running" | "completed" | "failed";
export type PublicationStatus = "published" | "degraded" | "rejected";

interface BasePlayerProfileFixture {
  readonly playerProfileId: string;
  readonly riotId: string;
  readonly routingRegion: RoutingRegion;
  readonly lastResolvedAt: string;
}

export interface SelfPlayerProfileFixture extends BasePlayerProfileFixture {
  readonly relationshipRole: "self";
  readonly verificationStatus: "unverified_claim" | "rso_verified";
  readonly trainingView: "personal";
}

export interface ObservedPlayerProfileFixture
  extends BasePlayerProfileFixture {
  readonly relationshipRole: "public_observed";
  readonly verificationStatus: "not_applicable";
  readonly trainingView: "learning_observation";
}

export type PlayerProfileFixture =
  | SelfPlayerProfileFixture
  | ObservedPlayerProfileFixture;

export interface TaskFixture {
  readonly status: TaskStatus;
  readonly statusLabel: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface RunFixture {
  readonly runtimeStatus: RuntimeStatus;
  readonly publicationStatus?: PublicationStatus;
  readonly terminalReason: string;
  readonly elapsedMs?: number;
  readonly reportAvailable: boolean;
}

export interface ProductStateFixture {
  readonly state: ProductStateValue;
  readonly reasonCode: ProductStateReason;
  readonly taskStatus: TaskStatus;
  readonly publicationStatus?: PublicationStatus;
  readonly reportAvailable: boolean;
  readonly evidenceRevision?: number;
  readonly evidenceFreshness?: "current" | "expired";
  readonly evidenceDisposition?: "complete" | "degraded" | "rejected";
}

export interface RecentMetricRowFixture {
  readonly csPerMinute: number;
  readonly goldPerMinute: number;
  readonly damagePerMinute: number;
  readonly visionScore: number;
  readonly deathsBefore15: number;
}

export interface RecentAveragesFixture extends RecentMetricRowFixture {
  readonly kda: number;
  readonly killParticipationPercent: number;
  readonly damageSharePercent: number;
  readonly goldSharePercent: number;
}

export interface RecentSummaryFixture {
  readonly gamesAnalyzed: number;
  readonly wins: number;
  readonly losses: number;
  readonly winRate: number;
  readonly mainRole: string;
  readonly mainChampions: readonly string[];
  readonly averages: RecentAveragesFixture;
  readonly winLossComparison: {
    readonly wins: RecentMetricRowFixture;
    readonly losses: RecentMetricRowFixture;
  };
}

export interface CoachReportFixture {
  readonly title: string;
  readonly verdict: string;
  readonly summary: string;
  readonly strengths: readonly string[];
  readonly priorities: readonly string[];
  readonly nextSession: string;
  readonly markdown: string;
}

export type EvidenceSourceKind =
  | "riot_official"
  | "data_dragon"
  | "riot_patch"
  | "opgg";

export interface EvidenceSourceFixture {
  readonly sourceKind: EvidenceSourceKind;
  readonly label: string;
  readonly status: "verified" | "partial" | "unavailable";
  readonly freshness: "current" | "stale" | "unknown";
  readonly detail: string;
}

export interface EvidenceJoinFixture {
  readonly label: string;
  readonly status:
    | "joined"
    | "joined_partial"
    | "unjoined"
    | "stale"
    | "conflict";
  readonly detail: string;
}

export interface EvidenceGapFixture {
  readonly code: string;
  readonly summary: string;
  readonly impact: string;
}

export interface EvidenceFixture {
  readonly revision: number;
  readonly bundleDigest: string;
  readonly snapshotDigest: string;
  readonly freshness: "current" | "expired";
  readonly disposition: "complete" | "degraded" | "rejected";
  readonly confidence: "high" | "medium" | "low" | "unknown";
  readonly claims: readonly (
    | "riot_match_facts"
    | "data_dragon_static"
    | "official_patch_facts"
    | "current_meta_recommendation"
    | "exact_patch_meta_comparison"
  )[];
  readonly sources: readonly EvidenceSourceFixture[];
  readonly joins: readonly EvidenceJoinFixture[];
  readonly gaps: readonly EvidenceGapFixture[];
}

export interface PersonalTrainingFixture {
  readonly mode: "personal";
  readonly title: string;
  readonly focus: string;
  readonly completedSessions: number;
  readonly targetSessions: number;
  readonly completionPercent: number;
  readonly metricLabel: string;
  readonly metricValue: string;
  readonly trend: "improving" | "steady" | "needs_attention";
  readonly nextAction: string;
}

export interface LearningObservationTrainingFixture {
  readonly mode: "learning_observation";
  readonly readOnly: true;
  readonly title: string;
  readonly note: string;
  readonly focusPoints: readonly string[];
}

export type ProfileTrainingFixture =
  | PersonalTrainingFixture
  | LearningObservationTrainingFixture;

export interface TaskEventFixture {
  readonly sequence: number;
  readonly eventKind:
    | "task_created"
    | "task_claimed"
    | "task_completed"
    | "task_failed"
    | "cancel_requested"
    | "task_cancelled"
    | "recovery_required";
  readonly statusAfter: TaskStatus;
  readonly reason?: string;
  readonly occurredAt: string;
}

export interface ReviewWorkbenchFixture {
  readonly schemaVersion: "1.0";
  readonly fixture_mode: true;
  readonly disclosure: string;
  readonly profiles: readonly PlayerProfileFixture[];
  readonly selectedProfileId: string;
  readonly task: TaskFixture;
  readonly productState: ProductStateFixture;
  readonly summary?: RecentSummaryFixture;
  readonly timeline?: WorkbenchTimeline;
  readonly run?: RunFixture;
  readonly report?: CoachReportFixture;
  readonly evidence?: EvidenceFixture;
  readonly events: readonly TaskEventFixture[];
  readonly trainingByProfile: Readonly<
    Record<string, ProfileTrainingFixture>
  >;
}

export type WorkbenchScenarioName =
  | "published"
  | "degraded"
  | "rejected"
  | "not_ready"
  | "loading"
  | "empty"
  | "error";

export type ClientResourceState = "loading" | "empty" | "ready" | "error";

export type WorkbenchScreenState =
  | {
      readonly fixture_mode: true;
      readonly client: "loading";
      readonly message: string;
    }
  | {
      readonly fixture_mode: true;
      readonly client: "empty";
      readonly message: string;
      readonly actionLabel: string;
    }
  | {
      readonly fixture_mode: true;
      readonly client: "ready";
      readonly data: ReviewWorkbenchFixture;
    }
  | {
      readonly fixture_mode: true;
      readonly client: "error";
      readonly code: "fixture_load_failed" | "fixture_scenario_unknown";
      readonly message: string;
    };

const forbiddenFieldPatterns = [
  /^owner(?:id)?$/,
  /puuid/,
  /^prompt/,
  /^context(?:body|text|raw|payload)/,
  /^raw(?:response|request|body|payload|error)/,
  /^worker(?:id|identity)?$/,
  /^lease/,
  /^refresh(?:id|identity)?$/,
  /^requestfingerprint$/,
  /^idempotency(?:key)?$/,
  /^checkpoint/,
  /^operation(?:id|identity)?$/,
  /^(?:file|local)?path$/,
  /^dsn$/,
  /^databaseurl$/,
  /^apikey$/,
  /^cookie$/,
  /^authorization$/,
  /^secret$/,
  /^chainofthought$/,
  /^reasoning(?:content|text)?$/,
  /^sourcecandidate(?:id|identity)?$/,
] as const;

const forbiddenValuePatterns = [
  /^[A-Za-z]:[\\/]/,
  /^\\\\[^\\]/,
  /^\/(?:home|Users|var|tmp|etc|opt|srv|mnt|data)\//,
  /^file:\/\//i,
  /^(?:postgres(?:ql)?|mysql|mongodb|redis|sqlite):\/\//i,
  /^RGAPI-/i,
  /^sk-[0-9A-Za-z_-]+$/,
  /^Bearer\s+/i,
  /showmaker/i,
] as const;

function normalizeFixtureKey(key: string): string {
  return key.replace(/[^0-9A-Za-z]/g, "").toLowerCase();
}

function assertSafeFixtureValue(
  value: unknown,
  seen: WeakSet<object>,
  location: string,
): void {
  if (typeof value === "string") {
    if (forbiddenValuePatterns.some((pattern) => pattern.test(value))) {
      throw new Error(`forbidden fixture value at ${location}`);
    }
    return;
  }
  if (
    value === null ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  ) {
    return;
  }
  if (typeof value !== "object") {
    throw new Error(`fixture contains a non-public value at ${location}`);
  }
  if (seen.has(value)) {
    throw new Error("fixture must be acyclic");
  }
  seen.add(value);

  for (const [key, nested] of Object.entries(value)) {
    const normalized = normalizeFixtureKey(key);
    if (forbiddenFieldPatterns.some((pattern) => pattern.test(normalized))) {
      throw new Error(`forbidden fixture field: ${key}`);
    }
    assertSafeFixtureValue(nested, seen, `${location}.${key}`);
  }
}

function assertProfileTrainingBoundary(fixture: ReviewWorkbenchFixture): void {
  const profileIds = new Set<string>();
  for (const profile of fixture.profiles) {
    if (profileIds.has(profile.playerProfileId)) {
      throw new Error("fixture player profiles must be unique");
    }
    profileIds.add(profile.playerProfileId);

    const training = fixture.trainingByProfile[profile.playerProfileId];
    if (training === undefined) {
      continue;
    }
    if (
      (profile.relationshipRole === "self" && training.mode !== "personal") ||
      (profile.relationshipRole === "public_observed" &&
        training.mode !== "learning_observation")
    ) {
      throw new Error("fixture training view violates relationship boundary");
    }
  }
  if (!profileIds.has(fixture.selectedProfileId)) {
    throw new Error("selected fixture profile is unavailable");
  }
  if (
    Object.keys(fixture.trainingByProfile).some(
      (profileId) => !profileIds.has(profileId),
    )
  ) {
    throw new Error("fixture training refers to an unknown profile");
  }
}

function assertProductStateBoundary(fixture: ReviewWorkbenchFixture): void {
  const { productState } = fixture;
  if (productState.state === "published") {
    if (
      !productState.reportAvailable ||
      fixture.report === undefined ||
      fixture.summary === undefined ||
      fixture.timeline === undefined ||
      fixture.evidence?.freshness !== "current" ||
      fixture.evidence.disposition !== "complete"
    ) {
      throw new Error("published fixture is missing publishable evidence");
    }
    return;
  }
  if (productState.state === "degraded") {
    if (!productState.reportAvailable || fixture.report === undefined || fixture.timeline === undefined) {
      throw new Error("degraded fixture must retain its limited report");
    }
    return;
  }
  if (
    productState.reportAvailable ||
    fixture.report !== undefined ||
    (productState.state === "not_ready" && fixture.summary !== undefined)
  ) {
    throw new Error("non-report fixture exposes unavailable product content");
  }
}

export function assertPublicWorkbenchFixture(
  value: unknown,
): asserts value is ReviewWorkbenchFixture {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("fixture must be an object");
  }
  if (!("fixture_mode" in value) || value.fixture_mode !== true) {
    throw new Error("fixture_mode must be true");
  }
  assertSafeFixtureValue(value, new WeakSet<object>(), "fixture");

  const fixture = value as ReviewWorkbenchFixture;
  if (!Array.isArray(fixture.profiles)) {
    throw new Error("fixture profiles must be an array");
  }
  assertProfileTrainingBoundary(fixture);
  assertProductStateBoundary(fixture);
}

export function getSelectedProfile(
  fixture: ReviewWorkbenchFixture,
): PlayerProfileFixture {
  const profile = fixture.profiles.find(
    (candidate) => candidate.playerProfileId === fixture.selectedProfileId,
  );
  if (profile === undefined) {
    throw new Error("selected fixture profile is unavailable");
  }
  return profile;
}

export function getSelectedTraining(
  fixture: ReviewWorkbenchFixture,
): ProfileTrainingFixture {
  const profile = getSelectedProfile(fixture);
  const training = fixture.trainingByProfile[profile.playerProfileId];
  if (training === undefined) {
    throw new Error("selected fixture profile has no training view");
  }
  return training;
}

export function freezeWorkbenchFixture<T>(value: T): T {
  const seen = new WeakSet<object>();

  const freeze = (candidate: unknown): void => {
    if (candidate === null || typeof candidate !== "object") {
      return;
    }
    if (seen.has(candidate)) {
      return;
    }
    seen.add(candidate);
    for (const nested of Object.values(candidate)) {
      freeze(nested);
    }
    Object.freeze(candidate);
  };

  freeze(value);
  return value;
}

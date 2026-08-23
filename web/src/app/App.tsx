import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react"
import { LazyMotion, MotionConfig, domAnimation, m } from "motion/react"

import { ApiClient } from "../api/client"
import { LiveWorkbenchHttpApi } from "../api/liveWorkbenchApi"
import { createTaskEventStream } from "../api/taskEventStream"
import type { WorkbenchScreenState } from "../contracts/workbench"
import { CoachBrief } from "../components/CoachBrief"
import { CommandRail } from "../components/CommandRail"
import { EvidenceDrawer } from "../components/EvidenceDrawer"
import { AwakeningScene, type AwakeningIdentityInput } from "../components/AwakeningScene"
import { ProductStateBanner } from "../components/ProductStateBanner"
import { RecentFormPanel } from "../components/RecentFormPanel"
import { RiftAtmosphere } from "../components/RiftAtmosphere"
import { TrainingPanel } from "../components/TrainingPanel"
import { Glyph } from "../components/VisualGlyphs"
import { resolveWorkbenchScenario } from "../fixtures/workbenchFixtures"
import { adaptFixtureWorkbench } from "../workbench/adapters"
import {
  LiveWorkbenchController,
  type LiveWorkbenchSnapshot,
} from "../workbench/liveController"
import type {
  LiveWorkbenchScreenState,
  LiveWorkbenchView,
  WorkbenchPlayerProfile,
  WorkbenchTaskEvent,
} from "../workbench/model"
import {
  createAwakeningState,
  transitionAwakeningState,
  type AwakeningPresentationState,
} from "../awakening/model"

export interface LiveWorkbenchControllerLike {
  readonly snapshot: LiveWorkbenchSnapshot
  subscribe(listener: () => void): () => void
  start(): Promise<void>
  selectProfile(profileId: string): Promise<void>
  dispose(): void
}

interface AppProps {
  readonly scenarioOverride?: string
  readonly createLiveController?: () => LiveWorkbenchControllerLike
  readonly surfaceOverride?: "awakening"
}

function getAwakeningSurface(override?: "awakening"): boolean {
  if (override === "awakening") return true
  if (typeof window === "undefined") return false
  return new URLSearchParams(window.location.search).get("surface") === "awakening"
}

function getAwakeningPreviewState(): AwakeningPresentationState {
  const demo = typeof window === "undefined"
    ? undefined
    : new URLSearchParams(window.location.search).get("demo")
  if (demo !== "ready" && demo !== "degraded") return createAwakeningState()

  const calibrating = transitionAwakeningState(
    transitionAwakeningState(createAwakeningState(), "begin_editing"),
    "begin_calibration",
  )
  return transitionAwakeningState(calibrating, demo === "ready" ? "calibration_ready" : "calibration_degraded")
}

function movePreviewToCalibration(state: AwakeningPresentationState): AwakeningPresentationState {
  const editing = state.phase === "idle"
    ? transitionAwakeningState(state, "begin_editing")
    : state
  return editing.phase === "editing"
    ? transitionAwakeningState(editing, "begin_calibration")
    : editing
}

function AwakeningPreview() {
  const [state, setState] = useState(getAwakeningPreviewState)
  const handleSubmit = (_input: AwakeningIdentityInput) => {
    setState(movePreviewToCalibration)
  }
  const handleHandoff = () => {
    if (typeof window !== "undefined") window.location.assign("/?scenario=published")
  }

  return (
    <div className="awakening-preview-shell">
      <a className="skip-link" href="#awakening-title">Skip to identity calibration</a>
      <AwakeningScene
        state={state}
        disclosure="Preview only · no external lookup or authentication"
        onSubmit={handleSubmit}
        onHandoff={handleHandoff}
      />
    </div>
  )
}

function createDefaultLiveController(): LiveWorkbenchControllerLike {
  const initialProfileId = typeof window === "undefined"
    ? undefined
    : new URLSearchParams(window.location.search).get("player_profile_id") ?? undefined
  return new LiveWorkbenchController({
    api: new LiveWorkbenchHttpApi(new ApiClient()),
    streamFactory: (binding, callbacks) => createTaskEventStream({ ...binding, ...callbacks }),
    ...(initialProfileId === undefined ? {} : { initialProfileId }),
  })
}

function getExplicitScenario(override?: string): WorkbenchScreenState | undefined {
  if (override !== undefined) return resolveWorkbenchScenario(override)
  if (typeof window === "undefined") return undefined
  const query = new URLSearchParams(window.location.search)
  return query.has("scenario") ? resolveWorkbenchScenario(query.get("scenario")) : undefined
}

function ClientBoundary({
  state,
  mode,
}: {
  readonly state: Exclude<LiveWorkbenchScreenState, { client: "ready" }>
  readonly mode: "fixture" | "live"
}) {
  if (state.client === "loading") {
    return (
      <div className="client-state client-state--loading" role="status" aria-busy="true">
        <div className="loading-core" aria-hidden="true"><span /><span /><span /></div>
        <p className="eyebrow">{mode === "live" ? "LIVE CHANNEL · SYNCHRONIZING" : "FIXTURE CHANNEL · CALIBRATING"}</p>
        <h2>Calibrating the Rift</h2>
        <p>{state.message}</p>
        <div className="skeleton-lines" aria-hidden="true"><span /><span /><span /></div>
      </div>
    )
  }

  if (state.client === "empty") {
    return (
      <div className="client-state client-state--empty">
        <span className="client-state__sigil"><Glyph name="command" /></span>
        <p className="eyebrow">COMMAND ROSTER · EMPTY</p>
        <h2>No player profiles yet</h2>
        <p>{state.message}</p>
        <button type="button" disabled>Add a player profile later</button>
        <small>Profile creation belongs to a later API/Auth batch.</small>
      </div>
    )
  }

  return (
    <div className="client-state client-state--error" role="alert">
      <span className="client-state__sigil"><Glyph name="limit" /></span>
      <p className="eyebrow">CLIENT RESOURCE ERROR</p>
      <h2>Workbench unavailable</h2>
      <p>{state.message}</p>
      <code>{state.code}</code>
      <small>This client resource error does not rewrite the server Product State.</small>
    </div>
  )
}

function ProfileHeader({
  view,
  selectedProfile,
  mode,
  liveUpdates,
  disclosure,
  onSelect,
}: {
  readonly view: LiveWorkbenchView
  readonly selectedProfile: WorkbenchPlayerProfile
  readonly mode: "fixture" | "live"
  readonly liveUpdates: LiveWorkbenchSnapshot["liveUpdates"]
  readonly disclosure: string
  readonly onSelect: (profileId: string) => void
}) {
  return (
    <header className="workspace-header">
      <div className="workspace-header__intro">
        <p className="eyebrow"><span className="eyebrow__line" /> TACTICAL SURFACE / {mode === "live" ? "LIVE DATA" : "STATIC PREVIEW"}</p>
        <h1>Rift Command Center</h1>
        <p className="workspace-header__lede">A quality-gated review surface for the decisions between lane control and objective tempo.</p>
      </div>
      <div className="profile-console">
        <label htmlFor="player-profile">Player profile</label>
        <div className="profile-console__control">
          <select
            id="player-profile"
            aria-label="Player profile"
            value={selectedProfile.playerProfileId}
            onChange={(event) => onSelect(event.target.value)}
          >
            {view.profiles.map((profile) => (
              <option key={profile.playerProfileId} value={profile.playerProfileId}>{profile.riotId}</option>
            ))}
          </select>
          <span className="profile-console__chevron" aria-hidden="true">⌄</span>
        </div>
        <div className="profile-console__meta">
          <span>{selectedProfile.routingRegion} routing</span>
          <span>{selectedProfile.relationshipRole === "self" ? "claimed self" : "public observed"}</span>
          <span>{selectedProfile.verificationStatus.replaceAll("_", " ")}</span>
        </div>
      </div>
      <div className={`fixture-disclosure fixture-disclosure--${mode}`}>
        <span className="fixture-disclosure__beacon" aria-hidden="true" />
        <div>
          <strong>{mode === "live" ? "Live server projection" : "Fixture preview"}</strong>
          <small>{disclosure}</small>
          {mode === "live" ? <small className="live-transport-state">updates: {liveUpdates}</small> : null}
        </div>
      </div>
    </header>
  )
}

function EventStrip({
  events,
  liveUpdates,
}: {
  readonly events: readonly WorkbenchTaskEvent[]
  readonly liveUpdates: LiveWorkbenchSnapshot["liveUpdates"]
}) {
  return (
    <section className="event-strip" aria-label="Safe task lifecycle">
      <span className="event-strip__title">LIFECYCLE</span>
      {events.map((event, index) => (
        <div className="event-strip__event" key={`${event.cursor}-${event.eventKind}`}>
          <span className={`event-node${index === events.length - 1 ? " event-node--active" : ""}`} />
          <span>{event.eventKind.replaceAll("_", " ")}</span>
          <small>{new Date(event.occurredAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC" })}Z</small>
        </div>
      ))}
      {liveUpdates === "reconnecting" ? <span className="event-strip__transport" role="status">LIVE UPDATES RECONNECTING</span> : null}
    </section>
  )
}

function EmptyProfileView({
  profile,
  view,
  fixtureMode,
}: {
  readonly profile: WorkbenchPlayerProfile
  readonly view: LiveWorkbenchView
  readonly fixtureMode: boolean
}) {
  const observed = profile.relationshipRole === "public_observed"
  return (
    <div className="alternate-profile-view">
      <section className="profile-observation panel">
        <p className="eyebrow">RELATIONSHIP-SAFE PROFILE VIEW</p>
        <h2>{observed ? "Observation mode" : "No recent review"}</h2>
        <p>
          {observed
            ? `This public-observed profile has no loaded review${fixtureMode ? " in the current fixture" : ""}. Aggregate metrics and a published brief remain hidden instead of being rebound to the wrong player.`
            : "This profile has no visible recent review. RiftCoach does not borrow content from another profile."}
        </p>
        <dl>
          <div><dt>Routing</dt><dd>{profile.routingRegion}</dd></div>
          <div><dt>Relationship</dt><dd>{observed ? "public observed" : "claimed self"}</dd></div>
          <div><dt>Access</dt><dd>{observed ? "read-only public study" : "owner-scoped review"}</dd></div>
        </dl>
      </section>
      <TrainingPanel profile={profile} training={view.training} />
    </div>
  )
}

function ReadyWorkbench({
  view,
  mode,
  liveUpdates,
  disclosure,
  onSelect,
}: {
  readonly view: LiveWorkbenchView
  readonly mode: "fixture" | "live"
  readonly liveUpdates: LiveWorkbenchSnapshot["liveUpdates"]
  readonly disclosure: string
  readonly onSelect: (profileId: string) => void
}) {
  const selectedProfile = view.profiles.find((profile) => profile.playerProfileId === view.selectedProfileId)
    ?? view.profiles[0]
  if (selectedProfile === undefined) {
    return <ClientBoundary mode={mode} state={{ client: "error", code: "profile_projection_invalid", message: "No safe player profile was available." }} />
  }

  return (
    <>
      <ProfileHeader
        view={view}
        selectedProfile={selectedProfile}
        mode={mode}
        liveUpdates={liveUpdates}
        disclosure={disclosure}
        onSelect={onSelect}
      />
      <h2 className="profile-name-heading">{selectedProfile.riotId}</h2>
      {view.productState === undefined ? (
        <EmptyProfileView profile={selectedProfile} view={view} fixtureMode={mode === "fixture"} />
      ) : (
        <div className="command-layout">
          <div className="command-layout__primary">
            <ProductStateBanner state={view.productState} />
            <EventStrip events={view.events} liveUpdates={liveUpdates} />
            {view.summary !== undefined ? <RecentFormPanel summary={view.summary} /> : null}
            {view.summary === undefined && view.productState.state === "not_ready" ? (
              <section className="analysis-pending panel" aria-labelledby="analysis-pending-title">
                <span className="analysis-pending__route" aria-hidden="true" />
                <p className="eyebrow">RUNNING · NO SYNTHETIC ETA</p>
                <h3 id="analysis-pending-title">Waiting for a terminal review</h3>
                <p>RiftCoach is waiting for a terminal, quality-gated result. The event rail above is the only progress signal.</p>
              </section>
            ) : null}
            <CoachBrief productState={view.productState} report={view.report} />
          </div>
          <aside className="context-rail" aria-label="Review context">
            <div className="context-rail__header"><span>CONTEXT CHANNEL</span><small>SAFE PROJECTION</small></div>
            <TrainingPanel profile={selectedProfile} training={view.training} />
            <EvidenceDrawer evidence={view.evidence} events={view.events} run={view.run} />
            <section className="source-summary panel" aria-labelledby="source-summary-title">
              <p className="eyebrow">SOURCE POSTURE</p>
              <h3 id="source-summary-title">What the brief can claim</h3>
              <div className="source-summary__facts">
                <span><b>{view.evidence?.sources.length ?? 0}</b> typed sources</span>
                <span><b>{view.evidence?.joins.length ?? 0}</b> explicit joins</span>
                <span><b>{view.evidence?.gaps.length ?? 0}</b> known gaps</span>
              </div>
              <p>Evidence is visible. Hidden reasoning is not.</p>
            </section>
          </aside>
        </div>
      )}
    </>
  )
}

function FixtureWorkbench({ state }: { readonly state: WorkbenchScreenState }) {
  const [selectedProfileId, setSelectedProfileId] = useState(
    state.client === "ready" ? state.data.selectedProfileId : "",
  )
  if (state.client !== "ready") {
    const safeState: Exclude<LiveWorkbenchScreenState, { client: "ready" }> = state.client === "empty"
      ? { client: "empty", message: state.message }
      : state.client === "error"
        ? { client: "error", code: state.code, message: state.message }
        : { client: "loading", message: state.message }
    return <ClientBoundary state={safeState} mode="fixture" />
  }
  const view = adaptFixtureWorkbench(state.data, selectedProfileId)
  return (
    <ReadyWorkbench
      view={view}
      mode="fixture"
      liveUpdates="closed"
      disclosure={state.data.disclosure}
      onSelect={setSelectedProfileId}
    />
  )
}

function LiveWorkbench({ createController }: { readonly createController: () => LiveWorkbenchControllerLike }) {
  const [controller] = useState(createController)
  const started = useRef(false)
  const mountToken = useRef(0)
  const subscribe = useCallback((listener: () => void) => controller.subscribe(listener), [controller])
  const getSnapshot = useCallback(() => controller.snapshot, [controller])
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)

  useEffect(() => {
    mountToken.current += 1
    if (!started.current) {
      started.current = true
      void controller.start()
    }
    return () => {
      const closingToken = ++mountToken.current
      queueMicrotask(() => {
        if (mountToken.current === closingToken) controller.dispose()
      })
    }
  }, [controller])

  if (snapshot.state.client !== "ready") return <ClientBoundary state={snapshot.state} mode="live" />
  return (
    <ReadyWorkbench
      view={snapshot.state.data}
      mode="live"
      liveUpdates={snapshot.liveUpdates}
      disclosure="Owner-scoped typed API · no browser secrets"
      onSelect={(profileId) => { void controller.selectProfile(profileId) }}
    />
  )
}

function AppFrame({
  children,
  mode,
}: {
  readonly children: ReactNode
  readonly mode: "fixture" | "live"
}) {
  return (
    <MotionConfig reducedMotion="user">
      <LazyMotion features={domAnimation}>
        <div className="app-shell">
          <a className="skip-link" href="#review-workspace">Skip to review workspace</a>
          <RiftAtmosphere />
          <CommandRail mode={mode} />
          <m.main
            id="review-workspace"
            className="review-workspace"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
          >
            {children}
          </m.main>
          <footer className="app-footer">
            <span>RIFTCOACH / 8E LIVE INTEGRATION</span>
            <span>{mode === "live" ? "OWNER-SCOPED CONTRACT SURFACE" : "STATIC SCENARIO · EXTERNAL CALLS 0"}</span>
          </footer>
        </div>
      </LazyMotion>
    </MotionConfig>
  )
}

export function App({ scenarioOverride, createLiveController, surfaceOverride }: AppProps) {
  if (getAwakeningSurface(surfaceOverride)) return <AwakeningPreview />
  const fixtureState = useMemo(() => getExplicitScenario(scenarioOverride), [scenarioOverride])
  if (fixtureState !== undefined) {
    return <AppFrame mode="fixture"><FixtureWorkbench state={fixtureState} /></AppFrame>
  }
  return (
    <AppFrame mode="live">
      <LiveWorkbench createController={createLiveController ?? createDefaultLiveController} />
    </AppFrame>
  )
}

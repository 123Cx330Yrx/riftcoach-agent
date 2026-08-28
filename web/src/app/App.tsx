import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react"
import { LazyMotion, MotionConfig, domAnimation, m } from "motion/react"

import { ApiClient } from "../api/client"
import { LiveWorkbenchHttpApi } from "../api/liveWorkbenchApi"
import { PlayerLinkHttpApi, type PlayerAccessApi } from "../api/playerLinkApi"
import { createTaskEventStream } from "../api/taskEventStream"
import type { AuthSessionWire } from "../api/wire"
import { AuthGate } from "../auth/AuthGate"
import { BrowserAuthSessionClient, isAuthSessionFailure, type AuthSessionClient } from "../auth/session"
import type { WorkbenchScreenState } from "../contracts/workbench"
import { CoachBrief } from "../components/CoachBrief"
import { AccountAccess } from "../components/AccountAccess"
import { CommandRail } from "../components/CommandRail"
import { EvidenceDrawer } from "../components/EvidenceDrawer"
import { AwakeningScene } from "../components/AwakeningScene"
import { ProductStateBanner } from "../components/ProductStateBanner"
import { RecentFormPanel } from "../components/RecentFormPanel"
import { TimelinePanel } from "../components/TimelinePanel"
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
  WorkbenchClientMessageCode,
  WorkbenchPlayerProfile,
  WorkbenchTaskEvent,
} from "../workbench/model"
import {
  createAwakeningState,
  transitionAwakeningState,
  type AwakeningPresentationState,
} from "../awakening/model"
import { ProductLocaleProvider, useI18n } from "../i18n/ProductLocaleProvider"
import { eventMessageKeys, regionMessageKeys, verificationMessageKeys } from "../i18n/productCopy"
import type { MessageKey } from "../i18n/locale"
import {
  parseProductJourney,
  productJourneyUrl,
  type ProductJourneyLocation,
  type ProductJourneyTarget,
} from "./productJourney"
import { useCinematicMediaPolicy } from "../cinematic/useCinematicMediaPolicy"
import {
  PORTAL_ACTIVATION_FULL_MOTION_MS,
  PORTAL_ACTIVATION_OVERLAY_EXIT_MS,
  cancelPortalActivation,
  commitPortalActivation,
  createPortalActivationState,
  startPortalActivation,
  shouldUseImmediatePortalActivation,
  type PortalActivationState,
} from "../cinematic/portalActivation"
import { PortalActivationOverlay } from "../components/PortalActivationOverlay"
import { RegionWallpaperLab } from "../components/RegionWallpaperLab"

export interface LiveWorkbenchControllerLike {
  readonly snapshot: LiveWorkbenchSnapshot
  subscribe(listener: () => void): () => void
  start(): Promise<void>
  selectProfile(profileId: string): Promise<void>
  dispose(): void
}

interface AppProps {
  readonly scenarioOverride?: string
  readonly createLiveController?: (initialProfileId: string) => LiveWorkbenchControllerLike
  readonly createAuthSessionClient?: () => AuthSessionClient
  readonly createPlayerAccessApi?: () => PlayerAccessApi
  readonly surfaceOverride?: "awakening"
}

function getAwakeningSurface(override?: "awakening"): boolean {
  if (override === "awakening") return true
  if (typeof window === "undefined") return false
  return new URLSearchParams(window.location.search).get("surface") === "awakening"
}

function getWallpaperLabSurface(): boolean {
  if (typeof window === "undefined") return false
  return new URLSearchParams(window.location.search).get("surface") === "wallpaper-lab"
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

function AwakeningPreview() {
  const { t } = useI18n()
  const [state] = useState(getAwakeningPreviewState)
  const handleEnter = () => {
    if (typeof window !== "undefined") window.location.assign("/?scenario=published")
  }

  return (
    <div className="awakening-preview-shell">
      <a className="skip-link" href="#awakening-title">{t("app.skip_identity")}</a>
      <AwakeningScene
        state={state}
        disclosure={t("app.preview_disclosure")}
        onEnter={handleEnter}
        entryMode="demo"
      />
    </div>
  )
}

function createDefaultLiveController(initialProfileId: string): LiveWorkbenchControllerLike {
  return new LiveWorkbenchController({
    api: new LiveWorkbenchHttpApi(new ApiClient()),
    streamFactory: (binding, callbacks) => createTaskEventStream({ ...binding, ...callbacks }),
    initialProfileId,
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
  const { t } = useI18n()
  const messageKeys: Readonly<Record<WorkbenchClientMessageCode, Parameters<typeof t>[0]>> = {
    profiles_loading: "client.message.profiles_loading",
    selected_review_loading: "client.message.selected_review_loading",
    fixture_loading: "client.message.fixture_loading",
    profiles_empty: "client.message.profiles_empty",
    workbench_load_failed: "client.message.workbench_load_failed",
    selected_profile_unavailable: "client.message.selected_profile_unavailable",
    profile_projection_invalid: "client.message.profile_projection_invalid",
    fixture_unavailable: "client.message.fixture_unavailable",
  }
  if (state.client === "loading") {
    return (
      <div className="client-state client-state--loading" role="status" aria-busy="true">
        <div className="loading-core" aria-hidden="true"><span /><span /><span /></div>
        <p className="eyebrow">{mode === "live" ? t("client.live_sync") : t("client.fixture_sync")}</p>
        <h2>{t("client.calibrating_title")}</h2>
        <p>{t(messageKeys[state.messageCode])}</p>
        <div className="skeleton-lines" aria-hidden="true"><span /><span /><span /></div>
      </div>
    )
  }

  if (state.client === "empty") {
    return (
      <div className="client-state client-state--empty">
        <span className="client-state__sigil"><Glyph name="command" /></span>
        <p className="eyebrow">{t("client.roster_empty")}</p>
        <h2>{t("client.empty_title")}</h2>
        <p>{t(messageKeys[state.messageCode])}</p>
        <button type="button" disabled>{t("client.add_profile_later")}</button>
        <small>{t("client.profile_future_boundary")}</small>
      </div>
    )
  }

  return (
    <div className="client-state client-state--error" role="alert">
      <span className="client-state__sigil"><Glyph name="limit" /></span>
      <p className="eyebrow">{t("client.error_kicker")}</p>
      <h2>{t("client.error_title")}</h2>
      <p>{t(messageKeys[state.messageCode])}</p>
      <small>{t("client.error_boundary")}</small>
    </div>
  )
}

function ProfileHeader({
  view,
  selectedProfile,
  mode,
  liveUpdates,
  onSelect,
}: {
  readonly view: LiveWorkbenchView
  readonly selectedProfile: WorkbenchPlayerProfile
  readonly mode: "fixture" | "live"
  readonly liveUpdates: LiveWorkbenchSnapshot["liveUpdates"]
  readonly onSelect: (profileId: string) => void
}) {
  const { t } = useI18n()
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => headingRef.current?.focus(), [])
  const transportKeys: Readonly<Record<LiveWorkbenchSnapshot["liveUpdates"], MessageKey>> = {
    connecting: "transport.connecting",
    live: "transport.live",
    reconnecting: "transport.reconnecting",
    closed: "transport.closed",
    error: "transport.error",
  }
  return (
    <header className="workspace-header">
      <div className="workspace-header__intro">
        <p className="eyebrow"><span className="eyebrow__line" /> {mode === "live" ? t("profile.surface_live") : t("profile.surface_fixture")}</p>
        <h1 ref={headingRef} tabIndex={-1}>{t("app.workbench_title")}</h1>
        <p className="workspace-header__lede">{t("app.workbench_lede")}</p>
      </div>
      <div className="profile-console">
        <label htmlFor="player-profile">{t("profile.label")}</label>
        <div className="profile-console__control">
          <select
            id="player-profile"
            aria-label={t("profile.label")}
            value={selectedProfile.playerProfileId}
            onChange={(event) => onSelect(event.target.value)}
          >
            {view.profiles.map((profile) => (
              <option key={profile.playerProfileId} value={profile.playerProfileId} translate="no">{profile.riotId}</option>
            ))}
          </select>
          <span className="profile-console__chevron" aria-hidden="true">⌄</span>
        </div>
        <div className="profile-console__meta">
          <span>{t("profile.routing", { region: t(regionMessageKeys[selectedProfile.routingRegion]) })}</span>
          <span>{selectedProfile.relationshipRole === "self" ? t("profile.relationship_self") : t("profile.relationship_observed")}</span>
          <span>{t(verificationMessageKeys[selectedProfile.verificationStatus])}</span>
        </div>
      </div>
      <div className={`fixture-disclosure fixture-disclosure--${mode}`}>
        <span className="fixture-disclosure__beacon" aria-hidden="true" />
        <div>
          <strong>{mode === "live" ? t("profile.live_projection") : t("profile.fixture_preview")}</strong>
          <small>{mode === "live" ? t("profile.live_disclosure") : t("profile.fixture_disclosure")}</small>
          {mode === "live" ? <small className="live-transport-state">{t("profile.updates", { state: t(transportKeys[liveUpdates]) })}</small> : null}
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
  const { formatUtcTime, t } = useI18n()
  return (
    <section className="event-strip" aria-label={t("event.safe_lifecycle")} tabIndex={0}>
      <span className="event-strip__title">{t("event.lifecycle")}</span>
      {events.map((event, index) => (
        <div className="event-strip__event" key={`${event.cursor}-${event.eventKind}`}>
          <span className={`event-node${index === events.length - 1 ? " event-node--active" : ""}`} />
          <span>{t(eventMessageKeys[event.eventKind])}</span>
          <small>{formatUtcTime(event.occurredAt)}Z</small>
        </div>
      ))}
      {liveUpdates === "reconnecting" ? <span className="event-strip__transport" role="status">{t("event.reconnecting")}</span> : null}
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
  const { t } = useI18n()
  const observed = profile.relationshipRole === "public_observed"
  return (
    <div className="alternate-profile-view">
      <section className="profile-observation panel">
        <p className="eyebrow">{t("profile.relationship_safe")}</p>
        <h2>{observed ? t("profile.observation_mode") : t("profile.no_recent_review")}</h2>
        <p>
          {observed
            ? t(fixtureMode ? "profile.observed_empty_fixture" : "profile.observed_empty_live")
            : t("profile.self_empty")}
        </p>
        <dl>
          <div><dt>{t("profile.routing_label")}</dt><dd>{t(regionMessageKeys[profile.routingRegion])}</dd></div>
          <div><dt>{t("profile.relationship_label")}</dt><dd>{observed ? t("profile.relationship_observed") : t("profile.relationship_self")}</dd></div>
          <div><dt>{t("profile.access_label")}</dt><dd>{observed ? t("profile.access_observed") : t("profile.access_self")}</dd></div>
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
  onSelect,
}: {
  readonly view: LiveWorkbenchView
  readonly mode: "fixture" | "live"
  readonly liveUpdates: LiveWorkbenchSnapshot["liveUpdates"]
  readonly onSelect: (profileId: string) => void
}) {
  const { formatNumber, t } = useI18n()
  const selectedProfile = view.profiles.find((profile) => profile.playerProfileId === view.selectedProfileId)
    ?? view.profiles[0]
  if (selectedProfile === undefined) {
    return <ClientBoundary mode={mode} state={{ client: "error", code: "profile_projection_invalid", messageCode: "profile_projection_invalid" }} />
  }

  return (
    <>
      <ProfileHeader
        view={view}
        selectedProfile={selectedProfile}
        mode={mode}
        liveUpdates={liveUpdates}
        onSelect={onSelect}
      />
      <h2 className="profile-name-heading" translate="no">{selectedProfile.riotId}</h2>
      {view.productState === undefined ? (
        <EmptyProfileView profile={selectedProfile} view={view} fixtureMode={mode === "fixture"} />
      ) : (
        <div className="command-layout">
          <div className="command-layout__primary">
            <ProductStateBanner state={view.productState} />
            <EventStrip events={view.events} liveUpdates={liveUpdates} />
            {view.summary !== undefined ? <RecentFormPanel summary={view.summary} /> : null}
            {view.timeline !== undefined ? <TimelinePanel timeline={view.timeline} /> : null}
            {view.summary === undefined && view.productState.state === "not_ready" ? (
              <section className="analysis-pending panel" aria-labelledby="analysis-pending-title">
                <span className="analysis-pending__route" aria-hidden="true" />
                <p className="eyebrow">{t("analysis.running_kicker")}</p>
                <h3 id="analysis-pending-title">{t("analysis.pending_title")}</h3>
                <p>{t("analysis.pending_body")}</p>
              </section>
            ) : null}
            <CoachBrief productState={view.productState} report={view.report} />
          </div>
          <aside className="context-rail" aria-label={t("context.aria")}>
            <div className="context-rail__header"><span>{t("context.channel")}</span><small>{t("context.safe_projection")}</small></div>
            <TrainingPanel profile={selectedProfile} training={view.training} />
            <EvidenceDrawer evidence={view.evidence} events={view.events} run={view.run} />
            <section className="source-summary panel" aria-labelledby="source-summary-title">
              <p className="eyebrow">{t("common.source_posture")}</p>
              <h3 id="source-summary-title">{t("source.claim_title")}</h3>
              <div className="source-summary__facts">
                <span><b>{formatNumber(view.evidence?.sources.length ?? 0)}</b> {t("source.typed_sources")}</span>
                <span><b>{formatNumber(view.evidence?.joins.length ?? 0)}</b> {t("source.explicit_joins")}</span>
                <span><b>{formatNumber(view.evidence?.gaps.length ?? 0)}</b> {t("source.known_gaps")}</span>
              </div>
              <p>{t("source.reasoning_boundary")}</p>
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
      ? { client: "empty", messageCode: "profiles_empty" }
      : state.client === "error"
        ? { client: "error", code: state.code, messageCode: "fixture_unavailable" }
        : { client: "loading", messageCode: "fixture_loading" }
    return <ClientBoundary state={safeState} mode="fixture" />
  }
  const view = adaptFixtureWorkbench(state.data, selectedProfileId)
  return (
    <ReadyWorkbench
      view={view}
      mode="fixture"
      liveUpdates="closed"
      onSelect={setSelectedProfileId}
    />
  )
}

function LiveWorkbench({
  createController,
  initialProfileId,
  onAuthFailure,
  onSelectProfile,
}: {
  readonly createController: (initialProfileId: string) => LiveWorkbenchControllerLike
  readonly initialProfileId: string
  readonly onAuthFailure: (code: string) => void
  readonly onSelectProfile: (profileId: string) => void
}) {
  const [controller] = useState(() => createController(initialProfileId))
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

  const authFailureCode = snapshot.state.client === "error" && isAuthSessionFailure(snapshot.state.code)
    ? snapshot.state.code
    : undefined
  useEffect(() => {
    if (authFailureCode !== undefined) onAuthFailure(authFailureCode)
  }, [authFailureCode, onAuthFailure])

  if (authFailureCode !== undefined) return null
  if (snapshot.state.client !== "ready") return <ClientBoundary state={snapshot.state} mode="live" />
  return (
    <ReadyWorkbench
      view={snapshot.state.data}
      mode="live"
      liveUpdates={snapshot.liveUpdates}
      onSelect={onSelectProfile}
    />
  )
}

function AccountAccessHost({
  createPlayerAccessApi,
  session,
  focusReady,
  onBack,
  onContinue,
  onAuthFailure,
}: {
  readonly createPlayerAccessApi?: () => PlayerAccessApi
  readonly session: AuthSessionWire
  readonly focusReady: boolean
  readonly onBack: () => void
  readonly onContinue: (profileId: string) => void
  readonly onAuthFailure: (code: string) => void
}) {
  const [api] = useState(() => createPlayerAccessApi?.() ?? new PlayerLinkHttpApi(new ApiClient()))
  return (
    <AccountAccess
      api={api}
      csrfToken={session.csrf_token}
      focusReady={focusReady}
      onBack={onBack}
      onContinue={onContinue}
      onAuthFailure={onAuthFailure}
    />
  )
}

function AuthenticatedProduct({
  journey,
  accountFocusReady,
  createController,
  createAuthSessionClient,
  createPlayerAccessApi,
  onNavigate,
}: {
  readonly journey: Exclude<ProductJourneyLocation, { stage: "portal" }>
  readonly accountFocusReady: boolean
  readonly createController: (initialProfileId: string) => LiveWorkbenchControllerLike
  readonly createAuthSessionClient?: () => AuthSessionClient
  readonly createPlayerAccessApi?: () => PlayerAccessApi
  readonly onNavigate: (target: ProductJourneyTarget) => void
}) {
  const [authClient] = useState(
    () => createAuthSessionClient?.() ?? new BrowserAuthSessionClient(),
  )
  const [authFailureCode, setAuthFailureCode] = useState<string>()
  const clearAuthFailure = useCallback(() => setAuthFailureCode(undefined), [])
  const onAuthFailure = useCallback((code: string) => setAuthFailureCode(code), [])
  return (
    <AuthGate
      client={authClient}
      {...(authFailureCode === undefined ? {} : { failureCode: authFailureCode })}
      onRetry={clearAuthFailure}
      onBack={() => onNavigate({ stage: "portal" })}
    >
      {(session) => journey.stage === "account" ? (
        <AccountAccessHost
          {...(createPlayerAccessApi === undefined ? {} : { createPlayerAccessApi })}
          session={session}
          focusReady={accountFocusReady}
          onBack={() => onNavigate({ stage: "portal" })}
          onContinue={(profileId) => onNavigate({ stage: "workbench", profileId })}
          onAuthFailure={onAuthFailure}
        />
      ) : (
        <AppFrame mode="live">
          <LiveWorkbench
            key={journey.profileId}
            createController={createController}
            initialProfileId={journey.profileId}
            onAuthFailure={onAuthFailure}
            onSelectProfile={(profileId) => onNavigate({ stage: "workbench", profileId })}
          />
        </AppFrame>
      )}
    </AuthGate>
  )
}

function currentJourney(): ProductJourneyLocation {
  if (typeof window === "undefined") return { stage: "portal", canonical: true }
  return parseProductJourney(window.location.search)
}

function ProductJourney({
  createLiveController,
  createAuthSessionClient,
  createPlayerAccessApi,
}: Pick<AppProps, "createLiveController" | "createAuthSessionClient" | "createPlayerAccessApi">) {
  const { t } = useI18n()
  const [journey, setJourney] = useState(currentJourney)
  const [activation, setActivation] = useState<PortalActivationState>(createPortalActivationState)
  const cinematicPolicy = useCinematicMediaPolicy()
  const reducedMotion = cinematicPolicy.mode === "poster"
    && cinematicPolicy.reason === "reduced-motion"
  const saveData = cinematicPolicy.mode === "poster"
    && cinematicPolicy.reason === "save-data"
  const activationNoSpatialMotion = shouldUseImmediatePortalActivation(reducedMotion, saveData)
  const committedGenerationRef = useRef<number | undefined>(undefined)

  const navigate = useCallback((target: ProductJourneyTarget) => {
    if (target.stage !== "account") {
      setActivation((current) => cancelPortalActivation(current, current.generation))
    }
    window.history.pushState(null, "", productJourneyUrl(target))
    setJourney(parseProductJourney(window.location.search))
  }, [])

  const activatePortal = useCallback(() => {
    setActivation((current) => startPortalActivation(current))
  }, [])

  useEffect(() => {
    const onPopState = () => {
      setActivation((current) => cancelPortalActivation(current, current.generation))
      setJourney(currentJourney())
    }
    window.addEventListener("popstate", onPopState)
    return () => window.removeEventListener("popstate", onPopState)
  }, [])

  useEffect(() => {
    if (!journey.canonical) {
      window.history.replaceState(null, "", productJourneyUrl({ stage: "portal" }))
      setActivation((current) => cancelPortalActivation(current, current.generation))
      setJourney({ stage: "portal", canonical: true })
    }
  }, [journey])

  useEffect(() => {
    if (activation.phase !== "activating") return
    const generation = activation.generation
    if (activationNoSpatialMotion) {
      setActivation((current) => commitPortalActivation(current, generation))
      return
    }
    const timer = setTimeout(() => {
      setActivation((current) => commitPortalActivation(current, generation))
    }, PORTAL_ACTIVATION_FULL_MOTION_MS)
    return () => clearTimeout(timer)
  }, [activation.generation, activation.phase, activationNoSpatialMotion])

  useEffect(() => {
    if (journey.stage !== "portal" || activation.phase !== "committed") return
    if (committedGenerationRef.current === activation.generation) return
    committedGenerationRef.current = activation.generation
    navigate({ stage: "account" })
  }, [activation.generation, activation.phase, journey.stage, navigate])

  useEffect(() => {
    if (journey.stage !== "account" || activation.phase !== "committed") return
    const generation = activation.generation
    const timer = setTimeout(() => {
      setActivation((current) => cancelPortalActivation(current, generation))
    }, activationNoSpatialMotion ? 0 : PORTAL_ACTIVATION_OVERLAY_EXIT_MS)
    return () => clearTimeout(timer)
  }, [activation.generation, activation.phase, journey.stage, activationNoSpatialMotion])

  const content = journey.stage === "portal" ? (
    <div className="awakening-preview-shell">
      <a className="skip-link" href="#awakening-title">{t("app.skip_identity")}</a>
      <AwakeningScene
        state={activationNoSpatialMotion ? { phase: "idle", motion: "reduced" } : createAwakeningState()}
        activationState={activation}
        onActivate={activatePortal}
        onEnter={() => navigate({ stage: "account" })}
      />
    </div>
  ) : (
    <AuthenticatedProduct
      journey={journey}
      accountFocusReady={activation.phase !== "committed"}
      createController={createLiveController ?? createDefaultLiveController}
      {...(createAuthSessionClient === undefined ? {} : { createAuthSessionClient })}
      {...(createPlayerAccessApi === undefined ? {} : { createPlayerAccessApi })}
      onNavigate={navigate}
    />
  )

  return (
    <>
      {content}
      <PortalActivationOverlay state={activation} reducedMotion={activationNoSpatialMotion} />
    </>
  )
}

function AppFrame({
  children,
  mode,
}: {
  readonly children: ReactNode
  readonly mode: "fixture" | "live"
}) {
  const { t } = useI18n()
  return (
    <MotionConfig reducedMotion="user">
      <LazyMotion features={domAnimation}>
        <div className="app-shell">
          <a className="skip-link" href="#review-workspace">{t("app.skip_workspace")}</a>
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
            <span>{t("app.footer_product")}</span>
            <span>{mode === "live" ? t("app.footer_live") : t("app.footer_fixture")}</span>
          </footer>
        </div>
      </LazyMotion>
    </MotionConfig>
  )
}

function AppSurface({ scenarioOverride, createLiveController, createAuthSessionClient, createPlayerAccessApi, surfaceOverride }: AppProps) {
  if (getWallpaperLabSurface()) return <RegionWallpaperLab />
  if (getAwakeningSurface(surfaceOverride)) return <AwakeningPreview />
  const fixtureState = getExplicitScenario(scenarioOverride)
  if (fixtureState !== undefined) {
    return <AppFrame mode="fixture"><FixtureWorkbench state={fixtureState} /></AppFrame>
  }
  return (
    <ProductJourney
      {...(createLiveController === undefined ? {} : { createLiveController })}
      {...(createAuthSessionClient === undefined ? {} : { createAuthSessionClient })}
      {...(createPlayerAccessApi === undefined ? {} : { createPlayerAccessApi })}
    />
  )
}

export function App(props: AppProps) {
  return <ProductLocaleProvider><AppSurface {...props} /></ProductLocaleProvider>
}

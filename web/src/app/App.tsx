import { useMemo, useState } from "react"
import { LazyMotion, MotionConfig, domAnimation, m } from "motion/react"

import type {
  PlayerProfileFixture,
  ReviewWorkbenchFixture,
  WorkbenchScreenState,
} from "../contracts/workbench"
import {
  resolveWorkbenchScenario,
} from "../fixtures/workbenchFixtures"
import { CoachBrief } from "../components/CoachBrief"
import { CommandRail } from "../components/CommandRail"
import { EvidenceDrawer } from "../components/EvidenceDrawer"
import { ProductStateBanner } from "../components/ProductStateBanner"
import { RecentFormPanel } from "../components/RecentFormPanel"
import { RiftAtmosphere } from "../components/RiftAtmosphere"
import { TrainingPanel } from "../components/TrainingPanel"
import { Glyph } from "../components/VisualGlyphs"

interface AppProps {
  readonly scenarioOverride?: string
}

function getInitialScenario(override?: string): WorkbenchScreenState {
  if (override !== undefined) {
    return resolveWorkbenchScenario(override)
  }
  if (typeof window === "undefined") {
    return resolveWorkbenchScenario()
  }
  return resolveWorkbenchScenario(new URLSearchParams(window.location.search).get("scenario"))
}

function ClientBoundary({ state }: { readonly state: Exclude<WorkbenchScreenState, { client: "ready" }> }) {
  if (state.client === "loading") {
    return (
      <div className="client-state client-state--loading" role="status" aria-busy="true">
        <div className="loading-core" aria-hidden="true"><span /><span /><span /></div>
        <p className="eyebrow">FIXTURE CHANNEL · CALIBRATING</p>
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
        <button type="button" disabled>{state.actionLabel}</button>
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
      <small>This is a client fixture error, not a rejected coaching result.</small>
    </div>
  )
}

function ProfileHeader({
  fixture,
  selectedProfile,
  onSelect,
}: {
  readonly fixture: ReviewWorkbenchFixture
  readonly selectedProfile: PlayerProfileFixture
  readonly onSelect: (profileId: string) => void
}) {
  return (
    <header className="workspace-header">
      <div className="workspace-header__intro">
        <p className="eyebrow"><span className="eyebrow__line" /> TACTICAL SURFACE / STATIC DATA</p>
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
            {fixture.profiles.map((profile) => (
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
      <div className="fixture-disclosure">
        <span className="fixture-disclosure__beacon" aria-hidden="true" />
        <div><strong>Fixture preview</strong><small>{fixture.disclosure}</small></div>
      </div>
    </header>
  )
}

function EventStrip({ fixture }: { readonly fixture: ReviewWorkbenchFixture }) {
  return (
    <section className="event-strip" aria-label="Safe task lifecycle">
      <span className="event-strip__title">LIFECYCLE</span>
      {fixture.events.map((event, index) => (
        <div className="event-strip__event" key={`${event.sequence}-${event.eventKind}`}>
          <span className={`event-node${index === fixture.events.length - 1 ? " event-node--active" : ""}`} />
          <span>{event.eventKind.replaceAll("_", " ")}</span>
          <small>{new Date(event.occurredAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC" })}Z</small>
        </div>
      ))}
    </section>
  )
}

function AlternateProfileView({
  profile,
  fixture,
}: {
  readonly profile: PlayerProfileFixture
  readonly fixture: ReviewWorkbenchFixture
}) {
  return (
    <div className="alternate-profile-view">
      <section className="profile-observation panel">
        <p className="eyebrow">RELATIONSHIP-SAFE PROFILE PREVIEW</p>
        <h2>Observation mode</h2>
        <p>This public-observed profile has no loaded review in the current fixture. Aggregate metrics and a published brief remain hidden instead of being rebound to the wrong player.</p>
        <dl>
          <div><dt>Routing</dt><dd>{profile.routingRegion}</dd></div>
          <div><dt>Relationship</dt><dd>public observed</dd></div>
          <div><dt>Access</dt><dd>read-only public study</dd></div>
        </dl>
      </section>
      <TrainingPanel profile={profile} training={fixture.trainingByProfile[profile.playerProfileId]} />
    </div>
  )
}

function ReadyWorkbench({ fixture }: { readonly fixture: ReviewWorkbenchFixture }) {
  const [selectedProfileId, setSelectedProfileId] = useState(fixture.selectedProfileId)
  const selectedProfile = useMemo(
    () => fixture.profiles.find((profile) => profile.playerProfileId === selectedProfileId) ?? fixture.profiles[0],
    [fixture.profiles, selectedProfileId],
  )

  if (selectedProfile === undefined) {
    return <ClientBoundary state={{ fixture_mode: true, client: "error", code: "fixture_load_failed", message: "No safe fixture profile was available." }} />
  }

  const viewingBoundProfile = selectedProfile.playerProfileId === fixture.selectedProfileId
  const training = fixture.trainingByProfile[selectedProfile.playerProfileId]

  return (
    <>
      <ProfileHeader fixture={fixture} selectedProfile={selectedProfile} onSelect={setSelectedProfileId} />
      <h2 className="profile-name-heading">{selectedProfile.riotId}</h2>
      {!viewingBoundProfile ? (
        <AlternateProfileView profile={selectedProfile} fixture={fixture} />
      ) : (
        <div className="command-layout">
          <div className="command-layout__primary">
            <ProductStateBanner state={fixture.productState} />
            <EventStrip fixture={fixture} />
            {fixture.summary !== undefined && <RecentFormPanel summary={fixture.summary} />}
            {fixture.summary === undefined && fixture.productState.state === "not_ready" && (
              <section className="analysis-pending panel" aria-labelledby="analysis-pending-title">
                <span className="analysis-pending__route" aria-hidden="true" />
                <p className="eyebrow">RUNNING · NO SYNTHETIC ETA</p>
                <h3 id="analysis-pending-title">Waiting for a terminal review</h3>
                <p>RiftCoach is waiting for a terminal, quality-gated result. The event rail above is the only progress signal.</p>
              </section>
            )}
            <CoachBrief productState={fixture.productState} report={fixture.report} />
          </div>
          <aside className="context-rail" aria-label="Review context">
            <div className="context-rail__header"><span>CONTEXT CHANNEL</span><small>SAFE PROJECTION</small></div>
            <TrainingPanel profile={selectedProfile} training={training} />
            <EvidenceDrawer evidence={fixture.evidence} events={fixture.events} run={fixture.run} />
            <section className="source-summary panel" aria-labelledby="source-summary-title">
              <p className="eyebrow">SOURCE POSTURE</p>
              <h3 id="source-summary-title">What the brief can claim</h3>
              <div className="source-summary__facts">
                <span><b>{fixture.evidence?.sources.length ?? 0}</b> typed sources</span>
                <span><b>{fixture.evidence?.joins.length ?? 0}</b> explicit joins</span>
                <span><b>{fixture.evidence?.gaps.length ?? 0}</b> known gaps</span>
              </div>
              <p>Evidence is visible. Hidden reasoning is not.</p>
            </section>
          </aside>
        </div>
      )}
    </>
  )
}

export function App({ scenarioOverride }: AppProps) {
  const state = useMemo(() => getInitialScenario(scenarioOverride), [scenarioOverride])

  return (
    <MotionConfig reducedMotion="user">
      <LazyMotion features={domAnimation}>
        <div className="app-shell">
          <a className="skip-link" href="#review-workspace">Skip to review workspace</a>
          <RiftAtmosphere />
          <CommandRail />
          <m.main
            id="review-workspace"
            className="review-workspace"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
          >
            {state.client === "ready" ? <ReadyWorkbench fixture={state.data} /> : <ClientBoundary state={state} />}
          </m.main>
          <footer className="app-footer">
            <span>RIFTCOACH / BATCH D</span>
            <span>STATIC CONTRACT SURFACE · EXTERNAL CALLS 0</span>
          </footer>
        </div>
      </LazyMotion>
    </MotionConfig>
  )
}

import { useState, type FormEvent } from "react"

import type { RoutingRegionWire } from "../api/wire"
import type {
  AwakeningPresentationState,
  AwakeningPhase,
} from "../awakening/model"

export interface AwakeningIdentityInput {
  readonly riotId: string
  readonly routingRegion: RoutingRegionWire
  readonly relationshipRole: "self" | "public_observed"
}

interface IdentityCalibrationProps {
  readonly state: AwakeningPresentationState
  readonly onSubmit: (input: AwakeningIdentityInput) => void
}

const routingRegions: readonly RoutingRegionWire[] = [
  "americas",
  "asia",
  "europe",
  "sea",
]

function phaseMessage(phase: AwakeningPhase): string {
  switch (phase) {
    case "idle":
      return "Start with a Riot ID and choose how this profile should be understood."
    case "editing":
      return "The route is ready. Nothing is looked up until you submit."
    case "calibrating":
      return "Calibrating the route. The server remains authoritative for identity and state."
    case "ready":
      return "The route is ready for a workbench handoff."
    case "degraded":
      return "The route is available with limits that remain visible in the workbench."
    case "rejected":
      return "The route was not published. No substitute analysis is shown."
    case "client-error":
      return "The browser could not continue. This is a client resource error, not a product rejection."
  }
}

function IdentityCalibration({ state, onSubmit }: IdentityCalibrationProps) {
  const [riotId, setRiotId] = useState("")
  const [routingRegion, setRoutingRegion] = useState<RoutingRegionWire>("asia")
  const [relationshipRole, setRelationshipRole] = useState<"self" | "public_observed">("self")

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit({ riotId: riotId.trim(), routingRegion, relationshipRole })
  }

  const calibrating = state.phase === "calibrating"

  return (
    <form className="awakening-calibration" onSubmit={handleSubmit} aria-labelledby="calibration-title">
      <div className="awakening-calibration__heading">
        <span className="awakening-shape awakening-shape--diamond" aria-hidden="true" />
        <div>
          <p className="eyebrow">IDENTITY CALIBRATION / PUBLIC ROUTING</p>
          <h2 id="calibration-title">Choose the profile lens</h2>
        </div>
      </div>
      <div className="awakening-calibration__fields">
        <label>
          <span>Riot ID</span>
          <input
            name="riotId"
            value={riotId}
            onChange={(event) => setRiotId(event.target.value)}
            autoComplete="off"
            placeholder="Name#Tag"
            required
          />
        </label>
        <label>
          <span>Routing region</span>
          <select
            name="routingRegion"
            value={routingRegion}
            onChange={(event) => setRoutingRegion(event.target.value as RoutingRegionWire)}
          >
            {routingRegions.map((region) => <option key={region} value={region}>{region}</option>)}
          </select>
        </label>
        <label>
          <span>Relationship</span>
          <select
            name="relationshipRole"
            value={relationshipRole}
            onChange={(event) => setRelationshipRole(event.target.value as "self" | "public_observed")}
          >
            <option value="self">My profile · unverified claim</option>
            <option value="public_observed">Public observed profile</option>
          </select>
        </label>
      </div>
      <div className="awakening-calibration__actions">
        <button type="submit" disabled={calibrating}>
          <span className="awakening-shape awakening-shape--circle" aria-hidden="true" />
          {calibrating ? "Calibrating route" : "Calibrate identity"}
        </button>
        <p aria-live="polite">{phaseMessage(state.phase)}</p>
      </div>
      {state.phase === "client-error" ? <p className="awakening-calibration__error" role="alert">{phaseMessage(state.phase)}</p> : null}
    </form>
  )
}

export function AwakeningScene({
  state,
  disclosure,
  onSubmit,
  onHandoff,
}: {
  readonly state: AwakeningPresentationState
  readonly disclosure: string
  readonly onSubmit: (input: AwakeningIdentityInput) => void
  readonly onHandoff?: () => void
}) {
  const handoffAvailable = (state.phase === "ready" || state.phase === "degraded") && onHandoff !== undefined

  return (
    <main
      className={`awakening-scene awakening-scene--${state.phase}`}
      data-testid="awakening-scene"
      data-phase={state.phase}
      data-motion={state.motion}
    >
      <div className="awakening-scene__field" aria-hidden="true">
        <svg viewBox="0 0 1200 760" preserveAspectRatio="xMidYMid slice">
          <path d="M-80 610C170 470 230 260 470 220s330 160 730-120" />
          <path d="M-30 710C210 520 310 450 520 430s350 80 730-290" />
          <path d="M80 780c230-210 330-270 540-260s320-60 570-270" />
          <path className="awakening-scene__route" d="M50 720 580 390 1160 60" />
          <circle cx="580" cy="390" r="18" />
          <circle cx="580" cy="390" r="52" />
        </svg>
      </div>
      <header className="awakening-scene__header">
        <p className="eyebrow"><span className="eyebrow__line" /> RIFT AWAKENING / COACH CORE</p>
        <p className="awakening-scene__status">{disclosure}</p>
      </header>
      <section className="awakening-scene__hero" aria-labelledby="awakening-title">
        <div className="awakening-scene__core" aria-hidden="true">
          <span className="awakening-scene__core-orbit" />
          <span className="awakening-scene__core-orbit awakening-scene__core-orbit--inner" />
          <span className="awakening-scene__core-point" />
        </div>
        <p className="eyebrow">CINEMATIC PORTAL → BROADCAST WORKBENCH</p>
        <h1 id="awakening-title">Calibrate your analysis field</h1>
        <p className="awakening-scene__lede">Bring a public profile into focus, keep its relationship honest, and let the evidence decide what the Coach can say.</p>
      </section>
      <IdentityCalibration state={state} onSubmit={onSubmit} />
      <aside className="awakening-scene__handoff" aria-label="Portal handoff boundary">
        <span className="awakening-shape awakening-shape--square" aria-hidden="true" />
        <div>
          <strong>Route to the workbench</strong>
          <p>Identity, product state, evidence, and training remain typed server projections after handoff.</p>
        </div>
        {handoffAvailable ? (
          <button className="awakening-scene__handoff-action" type="button" onClick={onHandoff}>
            {state.phase === "degraded" ? "Open limited workbench" : "Enter broadcast workbench"}
          </button>
        ) : null}
      </aside>
    </main>
  )
}

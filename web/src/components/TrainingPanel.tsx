import type { PlayerProfileFixture, ProfileTrainingFixture } from "../contracts/workbench"
import { Glyph } from "./VisualGlyphs"

interface TrainingPanelProps {
  readonly profile: PlayerProfileFixture
  readonly training: ProfileTrainingFixture | undefined
}

export function TrainingPanel({ profile, training }: TrainingPanelProps) {
  if (profile.relationshipRole === "public_observed" || training?.mode === "learning_observation") {
    const observation = training?.mode === "learning_observation" ? training : undefined
    return (
      <section className="training-panel panel" id="training" aria-labelledby="observation-title">
        <div className="context-heading">
          <span><Glyph name="training" /></span>
          <div><p className="eyebrow">PUBLIC OBSERVED</p><h3 id="observation-title">Learning observation</h3></div>
        </div>
        <p className="training-panel__note">
          {observation?.note ?? "This profile is read-only and has no personal completion state."}
        </p>
        <ul className="focus-list">
          {(observation?.focusPoints ?? ["Study repeatable public choices without inferring private intent."]).map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
        <span className="read-only-tag">READ-ONLY STUDY MODE</span>
      </section>
    )
  }

  if (training?.mode !== "personal") {
    return (
      <section className="training-panel panel" id="training" aria-labelledby="no-plan-title">
        <div className="context-heading"><span><Glyph name="training" /></span><h3 id="no-plan-title">No active training plan</h3></div>
        <p>Training begins after a publishable review creates an accepted plan.</p>
      </section>
    )
  }

  return (
    <section className="training-panel panel" id="training" aria-labelledby="training-title">
      <div className="context-heading">
        <span><Glyph name="training" /></span>
        <div><p className="eyebrow">ACTIVE PROGRAM</p><h3 id="training-title">Your training plan</h3></div>
      </div>
      <h4>{training.title}</h4>
      <p className="training-panel__focus">{training.focus}</p>
      <div className="training-progress">
        <div className="training-progress__copy">
          <span>SESSION PROGRESS</span>
          <b>{training.completedSessions} / {training.targetSessions}</b>
        </div>
        <div
          className="training-progress__track"
          role="progressbar"
          aria-label="Training session progress"
          aria-valuemin={0}
          aria-valuemax={training.targetSessions}
          aria-valuenow={training.completedSessions}
        >
          <span style={{ width: `${training.completionPercent}%` }} />
        </div>
      </div>
      <div className="training-metric">
        <span>{training.metricLabel}</span>
        <strong>{training.metricValue}</strong>
        <small>{training.trend.replace("_", " ")}</small>
      </div>
      <p className="training-panel__next"><span>NEXT</span>{training.nextAction}</p>
    </section>
  )
}

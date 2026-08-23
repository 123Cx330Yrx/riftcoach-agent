import type { WorkbenchPlayerProfile, WorkbenchTraining } from "../workbench/model"
import { Glyph } from "./VisualGlyphs"

interface TrainingPanelProps {
  readonly profile: WorkbenchPlayerProfile
  readonly training: WorkbenchTraining | undefined
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
        <ul className="focus-list"><li>Study repeatable public choices without inferring private intent.</li></ul>
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
      <p className="training-panel__focus">{training.objective}</p>
      {training.metric !== undefined ? (
        <dl className="training-metric" aria-label="Training metric evidence">
          <div><dt>Metric</dt><dd>{training.metric.metricKey.replaceAll("_", " ")}</dd></div>
          <div><dt>Baseline</dt><dd>{training.metric.baseline ?? "unknown"}</dd></div>
          <div><dt>Target</dt><dd>{training.metric.target ?? "unknown"}</dd></div>
          <div><dt>Current</dt><dd>{training.metric.current ?? "unknown"}</dd></div>
          <div><dt>Trend</dt><dd>{training.metric.trend.replaceAll("_", " ")}</dd></div>
          <div><dt>Samples</dt><dd>{training.metric.sampleCount}</dd></div>
        </dl>
      ) : <p className="training-panel__boundary">No verified progress metric is available yet.</p>}
    </section>
  )
}

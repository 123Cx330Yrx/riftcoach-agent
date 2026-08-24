import type { WorkbenchPlayerProfile, WorkbenchTraining } from "../workbench/model"
import { useI18n } from "../i18n/ProductLocaleProvider"
import type { MessageKey } from "../i18n/locale"
import { Glyph } from "./VisualGlyphs"

interface TrainingPanelProps {
  readonly profile: WorkbenchPlayerProfile
  readonly training: WorkbenchTraining | undefined
}

const trainingMetricKeys: Readonly<Record<string, MessageKey>> = {
  deaths_before_15: "training.metric.deaths_before_15",
  vision_score: "training.metric.vision_score",
}

export function TrainingPanel({ profile, training }: TrainingPanelProps) {
  const { formatNumber, t } = useI18n()
  if (profile.relationshipRole === "public_observed" || training?.mode === "learning_observation") {
    return (
      <section className="training-panel panel" id="training" aria-labelledby="observation-title">
        <div className="context-heading">
          <span><Glyph name="training" /></span>
          <div><p className="eyebrow">{t("training.observed_kicker")}</p><h3 id="observation-title">{t("training.observation_title")}</h3></div>
        </div>
        <p className="training-panel__note">{t("training.observed_note")}</p>
        <ul className="focus-list"><li>{t("training.observed_focus")}</li></ul>
        <span className="read-only-tag">{t("training.read_only")}</span>
      </section>
    )
  }

  if (training?.mode !== "personal") {
    return (
      <section className="training-panel panel" id="training" aria-labelledby="no-plan-title">
        <div className="context-heading"><span><Glyph name="training" /></span><h3 id="no-plan-title">{t("training.no_plan_title")}</h3></div>
        <p>{t("training.no_plan_body")}</p>
      </section>
    )
  }

  return (
    <section className="training-panel panel" id="training" aria-labelledby="training-title">
      <div className="context-heading">
        <span><Glyph name="training" /></span>
        <div><p className="eyebrow">{t("training.active_kicker")}</p><h3 id="training-title">{t("training.title")}</h3></div>
      </div>
      <p className="original-content-disclosure">{t("training.original_content")}</p>
      <h4 translate="no">{training.title}</h4>
      <p className="training-panel__focus" translate="no">{training.objective}</p>
      {training.metric !== undefined ? (
        <dl className="training-metric" aria-label={t("training.metric_aria")}>
          <div><dt>{t("training.metric")}</dt><dd>{t(trainingMetricKeys[training.metric.metricKey] ?? "training.metric.other")}</dd></div>
          <div><dt>{t("training.baseline")}</dt><dd>{training.metric.baseline === undefined ? t("common.unknown") : formatNumber(training.metric.baseline)}</dd></div>
          <div><dt>{t("training.target")}</dt><dd>{training.metric.target === undefined ? t("common.unknown") : formatNumber(training.metric.target)}</dd></div>
          <div><dt>{t("training.current")}</dt><dd>{training.metric.current === undefined ? t("common.unknown") : formatNumber(training.metric.current)}</dd></div>
          <div><dt>{t("training.trend")}</dt><dd>{t(`training.trend.${training.metric.trend}` as MessageKey)}</dd></div>
          <div><dt>{t("training.samples")}</dt><dd>{formatNumber(training.metric.sampleCount)}</dd></div>
        </dl>
      ) : <p className="training-panel__boundary">{t("training.no_metric")}</p>}
    </section>
  )
}

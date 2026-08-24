import type { WorkbenchRecentSummary } from "../workbench/model"
import { useI18n } from "../i18n/ProductLocaleProvider"
import type { MessageKey } from "../i18n/locale"

const metricDefinitions = [
  { key: "kda", label: "recent.metric.kda" as MessageKey, suffix: "", digits: 2 },
  { key: "csPerMinute", label: "recent.metric.cs_per_min" as MessageKey, suffix: "", digits: 1 },
  { key: "damagePerMinute", label: "recent.metric.damage_per_min" as MessageKey, suffix: "", digits: 0 },
  { key: "killParticipationPercent", label: "recent.metric.kill_participation" as MessageKey, suffix: "%", digits: 1 },
] as const

const roleMessageKeys: Readonly<Record<string, MessageKey>> = {
  top: "position.top",
  upper: "position.top",
  jungle: "position.jungle",
  mid: "position.mid",
  middle: "position.mid",
  adc: "position.adc",
  bottom: "position.adc",
  bot: "position.adc",
  utility: "position.support",
  support: "position.support",
}

function roleMessageKey(role: string): MessageKey {
  return roleMessageKeys[role.trim().toLowerCase()] ?? "position.unknown"
}

export function RecentFormPanel({ summary }: { readonly summary: WorkbenchRecentSummary }) {
  const { formatNumber, t } = useI18n()
  const winShare = `${summary.winRate}%`
  const decimal = (value: number, digits = 1) => formatNumber(value, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })

  return (
    <section className="recent-form panel" id="overview" aria-labelledby="recent-form-title">
      <div className="section-kicker"><span>01</span> {t("recent.section")}</div>
      <div className="recent-form__heading">
        <div>
          <p className="eyebrow">{t("recent.aggregate", { games: formatNumber(summary.gamesAnalyzed) })}</p>
          <h3 id="recent-form-title">{t("recent.title")}</h3>
        </div>
        <div className="role-cluster" aria-label={t("recent.role_aria")}>
          <span className="role-cluster__role">{t(roleMessageKey(summary.mainRole))}</span>
          {summary.mainChampions.map((champion) => <span key={champion} translate="no">{champion}</span>)}
        </div>
      </div>

      <div className="recent-form__body">
        <div className="winrate-orbit" aria-label={`${formatNumber(summary.winRate)}% ${t("recent.win_rate")}`}>
          <svg viewBox="0 0 180 180" aria-hidden="true">
            <circle className="winrate-orbit__track" cx="90" cy="90" r="72" />
            <circle
              className="winrate-orbit__value"
              cx="90"
              cy="90"
              r="72"
              pathLength="100"
              strokeDasharray={`${summary.winRate} ${100 - summary.winRate}`}
            />
          </svg>
          <div className="winrate-orbit__copy">
            <strong>{formatNumber(summary.winRate)}%</strong>
            <span>{t("recent.win_rate")}</span>
            <small>{t("recent.record", { wins: formatNumber(summary.wins), losses: formatNumber(summary.losses) })}</small>
          </div>
        </div>

        <div className="metric-grid">
          {metricDefinitions.map((metric) => (
            <article className="metric-tile" key={metric.key}>
              <span>{t(metric.label)}</span>
              <strong>
                {decimal(summary.averages[metric.key], metric.digits)}{metric.suffix}
              </strong>
              <small>{t("recent.average")}</small>
            </article>
          ))}
        </div>
      </div>

      <div className="outcome-comparison" aria-label={t("recent.comparison_aria")}>
        <div className="outcome-comparison__label">
          <span>{t("recent.wins_vs_losses")}</span>
          <small>{t("recent.aggregate_boundary")}</small>
        </div>
        <div className="outcome-comparison__bar" aria-hidden="true">
          <span className="outcome-comparison__wins" style={{ width: winShare }} />
          <span className="outcome-comparison__losses" style={{ width: `${100 - summary.winRate}%` }} />
        </div>
        <div className="outcome-comparison__facts">
          <span>{t("recent.gold_wins", { value: formatNumber(summary.winLossComparison.wins.goldPerMinute) })}</span>
          <span>{t("recent.gold_losses", { value: formatNumber(summary.winLossComparison.losses.goldPerMinute) })}</span>
          <span>{t("recent.early_deaths_wins", { value: decimal(summary.winLossComparison.wins.deathsBefore15) })}</span>
        </div>
      </div>
    </section>
  )
}

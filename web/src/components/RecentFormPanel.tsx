import type { WorkbenchRecentSummary } from "../workbench/model"

function formatDecimal(value: number, digits = 1) {
  return value.toFixed(digits)
}

const metricDefinitions = [
  { key: "kda", label: "KDA", suffix: "", digits: 2 },
  { key: "csPerMinute", label: "CS / MIN", suffix: "", digits: 1 },
  { key: "damagePerMinute", label: "DAMAGE / MIN", suffix: "", digits: 0 },
  { key: "killParticipationPercent", label: "KILL PARTICIPATION", suffix: "%", digits: 1 },
] as const

export function RecentFormPanel({ summary }: { readonly summary: WorkbenchRecentSummary }) {
  const winShare = `${summary.winRate}%`

  return (
    <section className="recent-form panel" id="overview" aria-labelledby="recent-form-title">
      <div className="section-kicker"><span>01</span> RECENT FORM</div>
      <div className="recent-form__heading">
        <div>
          <p className="eyebrow">AGGREGATE REVIEW · {summary.gamesAnalyzed} GAMES</p>
          <h3 id="recent-form-title">Recent performance snapshot</h3>
        </div>
        <div className="role-cluster" aria-label="Primary role and champions">
          <span className="role-cluster__role">{summary.mainRole}</span>
          {summary.mainChampions.map((champion) => <span key={champion}>{champion}</span>)}
        </div>
      </div>

      <div className="recent-form__body">
        <div className="winrate-orbit" aria-label={`${summary.winRate}% win rate`}>
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
            <strong>{winShare}</strong>
            <span>WIN RATE</span>
            <small>{summary.wins}W · {summary.losses}L</small>
          </div>
        </div>

        <div className="metric-grid">
          {metricDefinitions.map((metric) => (
            <article className="metric-tile" key={metric.key}>
              <span>{metric.label}</span>
              <strong>
                {formatDecimal(summary.averages[metric.key], metric.digits)}{metric.suffix}
              </strong>
              <small>RECENT AVERAGE</small>
            </article>
          ))}
        </div>
      </div>

      <div className="outcome-comparison" aria-label="Wins and losses aggregate comparison">
        <div className="outcome-comparison__label">
          <span>WINS VS LOSSES</span>
          <small>Aggregate segments · not a match history</small>
        </div>
        <div className="outcome-comparison__bar" aria-hidden="true">
          <span className="outcome-comparison__wins" style={{ width: winShare }} />
          <span className="outcome-comparison__losses" style={{ width: `${100 - summary.winRate}%` }} />
        </div>
        <div className="outcome-comparison__facts">
          <span><b>{summary.winLossComparison.wins.goldPerMinute}</b> gold/min in wins</span>
          <span><b>{summary.winLossComparison.losses.goldPerMinute}</b> gold/min in losses</span>
          <span><b>{formatDecimal(summary.winLossComparison.wins.deathsBefore15)}</b> early deaths in wins</span>
        </div>
      </div>
    </section>
  )
}

import { useState } from "react"

import type {
  WorkbenchTimeline,
  WorkbenchTimelineEvent,
  WorkbenchTimelineMatch,
} from "../workbench/model"
import { useI18n } from "../i18n/ProductLocaleProvider"
import type { MessageKey } from "../i18n/locale"

function formatClock(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return `${minutes.toString().padStart(2, "0")}:${remainder.toString().padStart(2, "0")}`
}

const eventKindKeys: Readonly<Record<WorkbenchTimelineEvent["eventKind"], MessageKey>> = {
  item_purchase: "timeline.event.purchase",
  objective: "timeline.event.objective",
  death: "timeline.event.death",
}

const phaseKeys: Readonly<Record<WorkbenchTimelineEvent["phase"], MessageKey>> = {
  early: "timeline.phase.early",
  mid: "timeline.phase.mid",
  late: "timeline.phase.late",
}

const timelineStatusKeys: Readonly<Record<WorkbenchTimeline["timelineStatus"], MessageKey>> = {
  available: "timeline.status.available",
  partial: "timeline.status.partial",
  unavailable: "timeline.status.unavailable",
}

function PhaseRail({
  match,
  selectedEvent,
  onSelectEvent,
}: {
  readonly match: WorkbenchTimelineMatch
  readonly selectedEvent: number
  readonly onSelectEvent: (index: number) => void
}) {
  const { t } = useI18n()
  const early = Math.min(900 / match.gameDurationSeconds, 1) * 100
  const mid = Math.max(Math.min(1500, match.gameDurationSeconds) - 900, 0)
    / match.gameDurationSeconds * 100
  const late = Math.max(100 - early - mid, 0)
  const phaseStyle = {
    gridTemplateColumns: `${early}% ${mid}% ${late}%`,
  }

  return (
    <div className="timeline-focus">
      <div className="timeline-phase-key" style={phaseStyle} aria-hidden="true">
        <span>{t("timeline.phase_key.early")}</span>
        <span>{t("timeline.phase_key.mid")}</span>
        <span>{t("timeline.phase_key.late")}</span>
      </div>
      <div
        className="timeline-rail"
        aria-label={t("timeline.phase_rail_aria", { champion: match.championName })}
      >
        <span className="timeline-rail__base" aria-hidden="true" />
        {match.events.map((event, index) => {
          const left = Math.min(event.atSeconds / match.gameDurationSeconds * 100, 100)
          return (
            <button
              className={`timeline-marker timeline-marker--${event.eventKind}${selectedEvent === index ? " timeline-marker--selected" : ""}`}
              key={`${event.eventKind}-${event.atSeconds}-${index}`}
              type="button"
              style={{ left: `${left}%` }}
              aria-label={t("timeline.event_at", { label: event.label, time: formatClock(event.atSeconds) })}
              aria-pressed={selectedEvent === index}
              onClick={() => onSelectEvent(index)}
            >
              <span aria-hidden="true" />
            </button>
          )
        })}
      </div>
      {match.events[selectedEvent] === undefined ? null : (
        <div className="timeline-callout" aria-live="polite">
          <span>{formatClock(match.events[selectedEvent].atSeconds)}</span>
          <strong translate="no">{match.events[selectedEvent].label}</strong>
          <small>{t("timeline.callout", {
            phase: t(phaseKeys[match.events[selectedEvent].phase]),
            eventKind: t(eventKindKeys[match.events[selectedEvent].eventKind]),
          })}</small>
        </div>
      )}
    </div>
  )
}

export function TimelinePanel({ timeline }: { readonly timeline: WorkbenchTimeline }) {
  const { formatNumber, t } = useI18n()
  const [selectedMatchId, setSelectedMatchId] = useState(timeline.matches[0]?.matchId ?? "")
  const [selectedEvent, setSelectedEvent] = useState(0)
  const selectedMatch = timeline.matches.find((match) => match.matchId === selectedMatchId)
    ?? timeline.matches[0]
  const unavailableCount = timeline.matches.filter(
    (match) => match.timelineStatus === "unavailable",
  ).length

  if (selectedMatch === undefined) return null

  const selectMatch = (matchId: string) => {
    setSelectedMatchId(matchId)
    setSelectedEvent(0)
  }

  return (
    <section className="timeline-panel panel" id="timeline" aria-labelledby="timeline-title">
      <div className="section-kicker"><span>02</span> {t("timeline.section")}</div>
      <div className="timeline-heading">
        <div>
          <p className="eyebrow">{t("timeline.kicker")}</p>
          <h3 id="timeline-title">{t("timeline.title")}</h3>
          <p>{t("timeline.lede")}</p>
        </div>
        <span className={`timeline-posture timeline-posture--${timeline.timelineStatus}`}>
          {t(timelineStatusKeys[timeline.timelineStatus])}
        </span>
      </div>

      {timeline.timelineStatus === "partial" ? (
        <p className="timeline-notice">
          {t("timeline.partial_notice", { unavailable: formatNumber(unavailableCount), total: formatNumber(timeline.totalMatches) })}
        </p>
      ) : null}
      {timeline.matchesTruncated ? (
        <p className="timeline-notice">{t("timeline.showing_matches", {
          projected: formatNumber(timeline.projectedMatches),
          total: formatNumber(timeline.totalMatches),
        })}</p>
      ) : null}

      <div className="timeline-match-strip" aria-label={t("timeline.reviewed_matches")}>
        {timeline.matches.map((match, index) => (
          <button
            className={`timeline-match${match.matchId === selectedMatch.matchId ? " timeline-match--selected" : ""}`}
            key={match.matchId}
            type="button"
            aria-pressed={match.matchId === selectedMatch.matchId}
            onClick={() => selectMatch(match.matchId)}
          >
            <small>{t("timeline.game", { number: formatNumber(index + 1) })}</small>
            <strong translate="no">{match.championName}</strong>
            <span className={match.win ? "timeline-win" : "timeline-loss"}>{match.win ? t("timeline.win") : t("timeline.loss")}</span>
            <em>{formatClock(match.gameDurationSeconds)}</em>
            {match.timelineStatus === "unavailable" ? <i>{t("timeline.no_timeline")}</i> : null}
          </button>
        ))}
      </div>

      {selectedMatch.timelineStatus === "unavailable" ? (
        <div className="timeline-unavailable" role="status">
          <span aria-hidden="true">◇</span>
          <div>
            <strong>{t("timeline.unavailable_title")}</strong>
            <p>{t("timeline.unavailable_body")}</p>
          </div>
        </div>
      ) : selectedMatch.events.length === 0 ? (
        <div className="timeline-unavailable" role="status">
          <span aria-hidden="true">·</span>
          <div>
            <strong>{t("timeline.no_events_title")}</strong>
            <p>{t("timeline.no_events_body")}</p>
          </div>
        </div>
      ) : (
        <div className="timeline-detail-grid">
          <PhaseRail
            match={selectedMatch}
            selectedEvent={Math.min(selectedEvent, selectedMatch.events.length - 1)}
            onSelectEvent={setSelectedEvent}
          />
          <ol className="timeline-event-list" aria-label={t("timeline.chronological_events")}>
            {selectedMatch.events.map((event, index) => (
              <li key={`${event.eventKind}-${event.atSeconds}-${index}`}>
                <button
                  className={selectedEvent === index ? "timeline-event--selected" : ""}
                  type="button"
                  onClick={() => setSelectedEvent(index)}
                >
                  <time>{formatClock(event.atSeconds)}</time>
                  <span className={`timeline-event-icon timeline-event-icon--${event.eventKind}`} aria-hidden="true" />
                  <span><strong translate="no">{event.label}</strong><small>{t(eventKindKeys[event.eventKind])} · {t(phaseKeys[event.phase])}</small></span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}

      {selectedMatch.eventsTruncated ? (
        <p className="timeline-boundary">{t("timeline.showing_events", {
          projected: formatNumber(selectedMatch.projectedEvents),
          total: formatNumber(selectedMatch.totalEvents),
        })}</p>
      ) : null}
      <p className="timeline-source">{t("timeline.source_boundary", { source: t("timeline.source.riot_match_v5_timeline") })}</p>
    </section>
  )
}

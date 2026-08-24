import { useState } from "react"

import type {
  WorkbenchTimeline,
  WorkbenchTimelineEvent,
  WorkbenchTimelineMatch,
} from "../workbench/model"

function formatClock(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return `${minutes.toString().padStart(2, "0")}:${remainder.toString().padStart(2, "0")}`
}

function resultLabel(match: WorkbenchTimelineMatch): string {
  return match.win ? "Win" : "Loss"
}

function eventKindLabel(event: WorkbenchTimelineEvent): string {
  if (event.eventKind === "item_purchase") return "Purchase"
  if (event.eventKind === "objective") return "Objective"
  return "Death"
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
        <span>EARLY · 0–15</span>
        <span>MID · 15–25</span>
        <span>LATE · 25+</span>
      </div>
      <div
        className="timeline-rail"
        aria-label={`Event phase timeline for ${match.championName}`}
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
              aria-label={`${event.label} at ${formatClock(event.atSeconds)}`}
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
          <strong>{match.events[selectedEvent].label}</strong>
          <small>{match.events[selectedEvent].phase} phase · {eventKindLabel(match.events[selectedEvent])}</small>
        </div>
      )}
    </div>
  )
}

export function TimelinePanel({ timeline }: { readonly timeline: WorkbenchTimeline }) {
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
      <div className="section-kicker"><span>02</span> MATCH TIMELINE</div>
      <div className="timeline-heading">
        <div>
          <p className="eyebrow">RIOT MATCH-V5 · VERIFIED EVENT FACTS</p>
          <h3 id="timeline-title">Match phase review</h3>
          <p>See when deaths, purchases and elite objectives landed—without inferred economy curves.</p>
        </div>
        <span className={`timeline-posture timeline-posture--${timeline.timelineStatus}`}>
          {timeline.timelineStatus}
        </span>
      </div>

      {timeline.timelineStatus === "partial" ? (
        <p className="timeline-notice">
          {unavailableCount} of {timeline.totalMatches} timelines unavailable. Available matches remain factual.
        </p>
      ) : null}
      {timeline.matchesTruncated ? (
        <p className="timeline-notice">Showing {timeline.projectedMatches} of {timeline.totalMatches} verified matches.</p>
      ) : null}

      <div className="timeline-match-strip" aria-label="Reviewed matches">
        {timeline.matches.map((match, index) => (
          <button
            className={`timeline-match${match.matchId === selectedMatch.matchId ? " timeline-match--selected" : ""}`}
            key={match.matchId}
            type="button"
            aria-pressed={match.matchId === selectedMatch.matchId}
            onClick={() => selectMatch(match.matchId)}
          >
            <small>GAME {index + 1}</small>
            <strong>{match.championName}</strong>
            <span className={match.win ? "timeline-win" : "timeline-loss"}>{resultLabel(match)}</span>
            <em>{formatClock(match.gameDurationSeconds)}</em>
            {match.timelineStatus === "unavailable" ? <i>NO TIMELINE</i> : null}
          </button>
        ))}
      </div>

      {selectedMatch.timelineStatus === "unavailable" ? (
        <div className="timeline-unavailable" role="status">
          <span aria-hidden="true">◇</span>
          <div>
            <strong>Timeline source was unavailable</strong>
            <p>The match result remains visible, but missing Riot Timeline events stay missing rather than becoming zero.</p>
          </div>
        </div>
      ) : selectedMatch.events.length === 0 ? (
        <div className="timeline-unavailable" role="status">
          <span aria-hidden="true">·</span>
          <div>
            <strong>No projected events in this bounded view</strong>
            <p>This does not imply that nothing happened in the match.</p>
          </div>
        </div>
      ) : (
        <div className="timeline-detail-grid">
          <PhaseRail
            match={selectedMatch}
            selectedEvent={Math.min(selectedEvent, selectedMatch.events.length - 1)}
            onSelectEvent={setSelectedEvent}
          />
          <ol className="timeline-event-list" aria-label="Chronological events">
            {selectedMatch.events.map((event, index) => (
              <li key={`${event.eventKind}-${event.atSeconds}-${index}`}>
                <button
                  className={selectedEvent === index ? "timeline-event--selected" : ""}
                  type="button"
                  onClick={() => setSelectedEvent(index)}
                >
                  <time>{formatClock(event.atSeconds)}</time>
                  <span className={`timeline-event-icon timeline-event-icon--${event.eventKind}`} aria-hidden="true" />
                  <span><strong>{event.label}</strong><small>{eventKindLabel(event)} · {event.phase}</small></span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}

      {selectedMatch.eventsTruncated ? (
        <p className="timeline-boundary">Showing {selectedMatch.projectedEvents} of {selectedMatch.totalEvents} events for this match.</p>
      ) : null}
      <p className="timeline-source">SOURCE · {timeline.source.replaceAll("_", " ")} · EVENT FACTS, NOT CAUSAL INFERENCE</p>
    </section>
  )
}

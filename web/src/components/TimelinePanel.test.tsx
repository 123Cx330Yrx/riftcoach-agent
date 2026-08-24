import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import type { WorkbenchTimeline } from "../workbench/model"
import { TimelinePanel } from "./TimelinePanel"

const timeline: WorkbenchTimeline = {
  source: "riot_match_v5_timeline",
  timelineStatus: "partial",
  totalMatches: 2,
  projectedMatches: 2,
  matchesTruncated: false,
  matches: [
    {
      matchId: "EUW1_123",
      championName: "Ahri",
      role: "MIDDLE",
      win: true,
      gameDurationSeconds: 1800,
      includedInAggregate: true,
      timelineStatus: "available",
      totalEvents: 3,
      projectedEvents: 3,
      eventsTruncated: false,
      events: [
        { eventKind: "death", atSeconds: 270, phase: "early", label: "Death" },
        { eventKind: "item_purchase", atSeconds: 780, phase: "early", label: "Luden's Companion", itemId: 6655 },
        { eventKind: "objective", atSeconds: 1200, phase: "mid", label: "Dragon secured" },
      ],
    },
    {
      matchId: "EUW1_124",
      championName: "Akali",
      role: "MIDDLE",
      win: false,
      gameDurationSeconds: 1600,
      includedInAggregate: true,
      timelineStatus: "unavailable",
      unavailableReason: "source_unavailable",
      totalEvents: 0,
      projectedEvents: 0,
      eventsTruncated: false,
      events: [],
    },
  ],
}

describe("TimelinePanel", () => {
  it("renders real event geometry with a visible chronological list", () => {
    render(<TimelinePanel timeline={timeline} />)

    expect(screen.getByRole("heading", { name: /match phase review/i })).toBeInTheDocument()
    expect(screen.getByText(/1 of 2 timelines unavailable/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /death at 04:30/i })).toHaveStyle({ left: "15%" })
    const list = screen.getByRole("list", { name: /chronological events/i })
    expect(within(list).getAllByRole("listitem")).toHaveLength(3)
    expect(within(list).getByText("13:00")).toBeInTheDocument()
    expect(within(list).getByText(/dragon secured/i)).toBeInTheDocument()
  })

  it("keeps unavailable missing instead of turning it into zero events", () => {
    render(<TimelinePanel timeline={timeline} />)

    fireEvent.click(screen.getByRole("button", { name: /game 2.*akali/i }))

    expect(screen.getByRole("status")).toHaveTextContent(/timeline source was unavailable/i)
    expect(screen.queryByRole("list", { name: /chronological events/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/0 events/i)).not.toBeInTheDocument()
  })
})

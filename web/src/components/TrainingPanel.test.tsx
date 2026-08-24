import { screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { translate } from "../i18n/locale"
import { renderWithLocale as render } from "../test/renderWithLocale"
import type { WorkbenchPlayerProfile, WorkbenchTraining } from "../workbench/model"
import { TrainingPanel } from "./TrainingPanel"

const profile: WorkbenchPlayerProfile = {
  playerProfileId: "95000000-0000-4000-8000-000000000001",
  riotId: "Riverline#EUW",
  routingRegion: "europe",
  relationshipRole: "self",
  verificationStatus: "unverified_claim",
  lastResolvedAt: "2026-08-24T02:00:00Z",
}

function training(metricKey: string): WorkbenchTraining {
  return {
    mode: "personal",
    title: "Early death control",
    objective: "Reduce deaths before 15 minutes",
    metric: {
      metricKey,
      baseline: 1.2,
      target: 0.7,
      current: 0.8,
      unit: "count",
      trend: "improving",
      sampleCount: 2,
    },
  }
}

describe("TrainingPanel product copy", () => {
  it("maps a canonical metric key to product copy instead of exposing the wire value", () => {
    render(<TrainingPanel profile={profile} training={training("deaths_before_15")} />)

    expect(screen.getByText("Deaths before 15 minutes", { exact: true })).toBeInTheDocument()
    expect(screen.queryByText("deaths_before_15", { exact: true })).not.toBeInTheDocument()
    expect(translate("zh-CN", "training.metric.deaths_before_15")).toBe("15 分钟前死亡次数")
  })

  it("uses a bounded generic label for an unknown future metric", () => {
    render(<TrainingPanel profile={profile} training={training("future_private_metric")} />)

    expect(screen.getByText("Tracked metric", { exact: true })).toBeInTheDocument()
    expect(screen.queryByText("future_private_metric", { exact: true })).not.toBeInTheDocument()
  })
})

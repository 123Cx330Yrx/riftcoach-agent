import { screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { publishedWorkbenchFixture } from "../fixtures/workbenchFixtures"
import { renderWithLocale as render } from "../test/renderWithLocale"
import { adaptFixtureWorkbench } from "../workbench/adapters"
import { RecentFormPanel } from "./RecentFormPanel"

describe("early-death evidence in the recent summary", () => {
  it.each(["en", "zh-CN"] as const)("shows missing evidence without formatting it as zero in %s", (locale) => {
    const original = adaptFixtureWorkbench(publishedWorkbenchFixture).summary!
    const summary = {
      ...original,
      winLossComparison: {
        ...original.winLossComparison,
        wins: { ...original.winLossComparison.wins, deathsBefore15: null },
      },
    }
    render(<RecentFormPanel summary={summary} />, locale)
    expect(screen.getByText(locale === "en"
      ? "Early-death data in wins is incomplete"
      : "胜局：前期死亡数据不完整")).toBeInTheDocument()
    expect(screen.queryByText(/0[.,]0 early deaths|前期死亡 0[.,]0 次/)).not.toBeInTheDocument()
  })

  it("still displays a measured zero", () => {
    const original = adaptFixtureWorkbench(publishedWorkbenchFixture).summary!
    render(<RecentFormPanel summary={{
      ...original,
      winLossComparison: {
        ...original.winLossComparison,
        wins: { ...original.winLossComparison.wins, deathsBefore15: 0 },
      },
    }} />)
    expect(screen.getByText("0.0 early deaths in wins")).toBeInTheDocument()
  })
})

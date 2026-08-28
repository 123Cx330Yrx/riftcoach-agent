import { describe, expect, it } from "vitest"

import { regionIconCatalog } from "./regionIconCatalog"

describe("official region icon catalog", () => {
  it("keeps a stable Runeterra region order and Riot source label", () => {
    expect(regionIconCatalog.map((item) => item.id)).toEqual([
      "ixtal", "mount-targon", "freljord", "demacia", "shurima", "shadow-isles",
      "bilgewater", "bandle-city", "piltover", "zaun", "ionia", "void", "noxus",
    ])
    expect(regionIconCatalog.every((item) => item.source === "riot-universe-region-crest")).toBe(true)
  })

  it("uses local assets instead of hotlinking a third-party URL", () => {
    for (const item of regionIconCatalog) {
      expect(item.asset).toMatch(/^\/assets\/wallpapers\/regions\/universe\/[a-z_-]+\.png$/)
    }
  })
})

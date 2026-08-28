import { describe, expect, it } from "vitest"

import { decodeRegionWallpaperCatalog, regionWallpaperCatalog } from "./regionWallpaperCatalog"

describe("region wallpaper catalog", () => {
  it("exposes the local Demacia and Bandle City candidates without claiming adoption", () => {
    expect(regionWallpaperCatalog.candidates).toHaveLength(2)
    expect(regionWallpaperCatalog.candidates[0]).toMatchObject({ id: "demacia-v1", region: "demacia", status: "research-candidate", rights: "unverified" })
    expect(regionWallpaperCatalog.candidates[1]).toMatchObject({ id: "bandle-city-v1", region: "bandle-city", status: "research-candidate", rights: "unverified" })
  })

  it.each([
    ["remote", "https://cdn.example/demacia.webm"],
    ["path traversal", "/assets/wallpapers/candidates/../demacia.webm"],
    ["wrong extension", "/assets/wallpapers/candidates/demacia.mov"],
  ])("rejects %s media URLs", (_name, webm) => {
    expect(() => decodeRegionWallpaperCatalog({
      schemaVersion: "1.0",
      candidates: [{ ...regionWallpaperCatalog.candidates[0], webm }],
    })).toThrow(/local wallpaper asset/i)
  })

  it("requires explicit rights and bilingual metadata", () => {
    const candidate = { ...regionWallpaperCatalog.candidates[0], rights: "verified" }
    expect(() => decodeRegionWallpaperCatalog({ schemaVersion: "1.0", candidates: [candidate] })).toThrow(/rights/i)
  })
})

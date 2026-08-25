import { describe, expect, it } from "vitest"

import {
  CINEMATIC_MOBILE_MAX_WIDTH_PX,
  resolveCinematicMediaPolicy,
  resolveCinematicViewport,
} from "./mediaPolicy"

describe("resolveCinematicViewport", () => {
  it("treats the exact 760px breakpoint as mobile", () => {
    expect(CINEMATIC_MOBILE_MAX_WIDTH_PX).toBe(760)
    expect(resolveCinematicViewport(759)).toBe("mobile")
    expect(resolveCinematicViewport(760)).toBe("mobile")
    expect(resolveCinematicViewport(761)).toBe("desktop")
  })

  it.each([Number.NaN, Number.POSITIVE_INFINITY, -1])(
    "rejects an invalid viewport width: %s",
    (viewportWidth) => {
      expect(() => resolveCinematicViewport(viewportWidth)).toThrow(
        "viewportWidth must be a finite non-negative number",
      )
    },
  )
})

describe("resolveCinematicMediaPolicy", () => {
  it.each(["desktop", "mobile"] as const)(
    "keeps the %s rendition identity in the motion branch",
    (viewport) => {
      expect(resolveCinematicMediaPolicy({
        reducedMotion: false,
        saveData: false,
        viewport,
      })).toEqual({ mode: "motion", viewport })
    },
  )

  it.each(["desktop", "mobile"] as const)(
    "keeps the %s rendition identity in the save-data poster branch",
    (viewport) => {
      expect(resolveCinematicMediaPolicy({
        reducedMotion: false,
        saveData: true,
        viewport,
      })).toEqual({ mode: "poster", viewport, reason: "save-data" })
    },
  )

  it("gives reduced motion priority when both poster reasons apply", () => {
    expect(resolveCinematicMediaPolicy({
      reducedMotion: true,
      saveData: true,
      viewport: "mobile",
    })).toEqual({
      mode: "poster",
      viewport: "mobile",
      reason: "reduced-motion",
    })
  })
})

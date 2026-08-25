import { describe, expect, it } from "vitest"

import {
  resolveCoverGeometry,
  type CoverGeometry,
  type CoverGeometrySource,
  type ViewportDimensions,
} from "./mediaGeometry"

const SOURCE_16_BY_9: CoverGeometrySource = {
  intrinsicWidth: 1600,
  intrinsicHeight: 900,
  focalPoint: { x: 0.5, y: 0.45 },
  objectPosition: { x: 0.5, y: 0.5 },
  hitBox: { x: 0.45, y: 0.35, width: 0.1, height: 0.2 },
}

const expectAlignedWithinHalfPercent = (
  actual: NonNullable<CoverGeometry["hitBox"]>,
  expected: NonNullable<CoverGeometry["hitBox"]>,
  viewport: ViewportDimensions,
) => {
  const horizontalTolerance = viewport.width * 0.005
  const verticalTolerance = viewport.height * 0.005

  expect(Math.abs(actual.left - expected.left)).toBeLessThan(horizontalTolerance)
  expect(Math.abs(actual.width - expected.width)).toBeLessThan(horizontalTolerance)
  expect(Math.abs(actual.top - expected.top)).toBeLessThan(verticalTolerance)
  expect(Math.abs(actual.height - expected.height)).toBeLessThan(verticalTolerance)
}

describe("resolveCoverGeometry", () => {
  it.each([
    {
      name: "1440 desktop",
      viewport: { width: 1440, height: 900 },
      expectedMedia: { left: -80, top: 0, width: 1600, height: 900 },
      expectedFocalPoint: { x: 720, y: 405 },
      expectedHitBox: { left: 640, top: 315, width: 160, height: 180 },
    },
    {
      name: "1024 tablet",
      viewport: { width: 1024, height: 768 },
      expectedMedia: {
        left: -170.6666666667,
        top: 0,
        width: 1365.3333333333,
        height: 768,
      },
      expectedHitBox: {
        left: 443.7333333333,
        top: 268.8,
        width: 136.5333333333,
        height: 153.6,
      },
      expectedFocalPoint: { x: 512, y: 345.6 },
    },
    {
      name: "390 mobile",
      viewport: { width: 390, height: 844 },
      expectedMedia: {
        left: -555.2222222222,
        top: 0,
        width: 1500.4444444444,
        height: 844,
      },
      expectedHitBox: {
        left: 119.9777777778,
        top: 295.4,
        width: 150.0444444444,
        height: 168.8,
      },
      expectedFocalPoint: { x: 195, y: 379.8 },
    },
    {
      name: "320 compact mobile",
      viewport: { width: 320, height: 568 },
      expectedMedia: {
        left: -344.8888888889,
        top: 0,
        width: 1009.7777777778,
        height: 568,
      },
      expectedHitBox: {
        left: 109.5111111111,
        top: 198.8,
        width: 100.9777777778,
        height: 113.6,
      },
      expectedFocalPoint: { x: 160, y: 255.6 },
    },
  ])("projects the normalized hit box at $name with less than 0.5% error", ({
    viewport,
    expectedMedia,
    expectedFocalPoint,
    expectedHitBox,
  }) => {
    const geometry = resolveCoverGeometry(SOURCE_16_BY_9, viewport)

    expect(geometry.mediaBox.left).toBeCloseTo(expectedMedia.left, 8)
    expect(geometry.mediaBox.top).toBeCloseTo(expectedMedia.top, 8)
    expect(geometry.mediaBox.width).toBeCloseTo(expectedMedia.width, 8)
    expect(geometry.mediaBox.height).toBeCloseTo(expectedMedia.height, 8)
    expect(Math.abs(geometry.focalPoint.x - expectedFocalPoint.x)).toBeLessThan(
      viewport.width * 0.005,
    )
    expect(Math.abs(geometry.focalPoint.y - expectedFocalPoint.y)).toBeLessThan(
      viewport.height * 0.005,
    )
    expect(geometry.hitBox).toBeDefined()
    expectAlignedWithinHalfPercent(geometry.hitBox!, expectedHitBox, viewport)
  })

  it("uses CSS object-position percentage semantics instead of always centering", () => {
    const geometry = resolveCoverGeometry(
      {
        intrinsicWidth: 1000,
        intrinsicHeight: 500,
        focalPoint: { x: 0.3, y: 0.4 },
        objectPosition: { x: 0.25, y: 0.9 },
        hitBox: { x: 0.2, y: 0.1, width: 0.1, height: 0.2 },
      },
      { width: 500, height: 500 },
    )

    expect(geometry.scale).toBe(1)
    expect(geometry.mediaBox).toEqual({ left: -125, top: 0, width: 1000, height: 500 })
    expect(geometry.focalPoint).toEqual({ x: 175, y: 200 })
    expect(geometry.hitBox).toEqual({ left: 75, top: 50, width: 100, height: 100 })
  })

  it("keeps projection stable for extremely wide and tall containers", () => {
    const wide = resolveCoverGeometry(
      {
        intrinsicWidth: 1000,
        intrinsicHeight: 1000,
        focalPoint: { x: 0.5, y: 0.5 },
        objectPosition: { x: 0.5, y: 0.8 },
        hitBox: { x: 0.1, y: 0.75, width: 0.2, height: 0.1 },
      },
      { width: 2000, height: 200 },
    )
    const tall = resolveCoverGeometry(
      {
        intrinsicWidth: 1000,
        intrinsicHeight: 500,
        focalPoint: { x: 0.5, y: 0.5 },
        objectPosition: { x: 0.1, y: 0.5 },
        hitBox: { x: 0.1, y: 0.2, width: 0.05, height: 0.2 },
      },
      { width: 200, height: 2000 },
    )

    expect(wide.mediaBox).toEqual({ left: 0, top: -1440, width: 2000, height: 2000 })
    expect(wide.hitBox).toEqual({ left: 200, top: 60, width: 400, height: 200 })
    expect(tall.mediaBox).toEqual({ left: -380, top: 0, width: 4000, height: 2000 })
    expect(tall.hitBox).toEqual({ left: 20, top: 400, width: 200, height: 400 })
  })

  it("returns one pure shared projection for the button and activation overlay", () => {
    const source = {
      intrinsicWidth: 1672,
      intrinsicHeight: 941,
      focalPoint: { x: 0.51, y: 0.43 },
      objectPosition: { x: 0.48, y: 0.52 },
      hitBox: { x: 0.47, y: 0.33, width: 0.08, height: 0.19 },
    } as const
    const viewport = { width: 1440, height: 900 } as const
    const sourceSnapshot = structuredClone(source)

    const buttonGeometry = resolveCoverGeometry(source, viewport)
    const overlayGeometry = resolveCoverGeometry(source, viewport)

    expect(buttonGeometry).toEqual(overlayGeometry)
    expect(source).toEqual(sourceSnapshot)
  })

  it("keeps the media geometry usable when a scene has no interactive hit box", () => {
    const geometry = resolveCoverGeometry(
      {
        intrinsicWidth: 1920,
        intrinsicHeight: 1080,
        focalPoint: { x: 0.5, y: 0.5 },
        objectPosition: { x: 0.5, y: 0.5 },
      },
      { width: 1440, height: 900 },
    )

    expect(geometry.mediaBox).toEqual({ left: -80, top: 0, width: 1600, height: 900 })
    expect(geometry.focalPoint).toEqual({ x: 720, y: 450 })
    expect(geometry.hitBox).toBeUndefined()
  })

  it.each([
    ["intrinsic width", { intrinsicWidth: 0 }],
    ["intrinsic height", { intrinsicHeight: -1 }],
    ["non-finite intrinsic width", { intrinsicWidth: Number.NaN }],
    ["viewport width", { viewportWidth: 0 }],
    ["viewport height", { viewportHeight: Number.POSITIVE_INFINITY }],
  ])("rejects invalid %s", (_name, override) => {
    const source = { ...SOURCE_16_BY_9 }
    const viewport = { width: 1440, height: 900 }

    if ("intrinsicWidth" in override) source.intrinsicWidth = override.intrinsicWidth!
    if ("intrinsicHeight" in override) source.intrinsicHeight = override.intrinsicHeight!
    if ("viewportWidth" in override) viewport.width = override.viewportWidth!
    if ("viewportHeight" in override) viewport.height = override.viewportHeight!

    expect(() => resolveCoverGeometry(source, viewport)).toThrow(/finite positive/i)
  })

  it.each([
    ["non-finite object position", { x: Number.NaN, y: 0.5 }],
    ["negative object position", { x: -0.01, y: 0.5 }],
    ["object position above one", { x: 0.5, y: 1.01 }],
  ])("rejects %s", (_name, objectPosition) => {
    expect(() =>
      resolveCoverGeometry(
        { ...SOURCE_16_BY_9, objectPosition },
        { width: 1440, height: 900 },
      ),
    ).toThrow(/objectPosition.*normalized/i)
  })

  it.each([
    ["non-finite focal point", { x: Number.POSITIVE_INFINITY, y: 0.5 }],
    ["negative focal point", { x: 0.5, y: -0.01 }],
    ["focal point above one", { x: 1.01, y: 0.5 }],
  ])("rejects %s", (_name, focalPoint) => {
    expect(() =>
      resolveCoverGeometry(
        { ...SOURCE_16_BY_9, focalPoint },
        { width: 1440, height: 900 },
      ),
    ).toThrow(/focalPoint.*normalized/i)
  })

  it.each([
    ["non-finite coordinate", { x: Number.NaN, y: 0.2, width: 0.1, height: 0.1 }],
    ["negative coordinate", { x: -0.01, y: 0.2, width: 0.1, height: 0.1 }],
    ["zero width", { x: 0.2, y: 0.2, width: 0, height: 0.1 }],
    ["negative height", { x: 0.2, y: 0.2, width: 0.1, height: -0.1 }],
    ["right overflow", { x: 0.95, y: 0.2, width: 0.1, height: 0.1 }],
    ["bottom overflow", { x: 0.2, y: 0.95, width: 0.1, height: 0.1 }],
  ])("rejects hit boxes with %s", (_name, hitBox) => {
    expect(() =>
      resolveCoverGeometry(
        { ...SOURCE_16_BY_9, hitBox },
        { width: 1440, height: 900 },
      ),
    ).toThrow(/hitBox.*normalized/i)
  })

  it("rejects finite inputs whose derived cover geometry overflows", () => {
    expect(() =>
      resolveCoverGeometry(
        {
          ...SOURCE_16_BY_9,
          intrinsicWidth: Number.MIN_VALUE,
        },
        { width: 1440, height: 900 },
      ),
    ).toThrow(/cover geometry.*finite/i)
  })
})

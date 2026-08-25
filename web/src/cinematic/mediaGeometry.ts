import type { CinematicMediaRendition } from "./mediaManifest"

export type CoverGeometrySource = Pick<
  CinematicMediaRendition,
  "intrinsicWidth" | "intrinsicHeight" | "focalPoint" | "objectPosition" | "hitBox"
>

export interface ViewportDimensions {
  readonly width: number
  readonly height: number
}

export interface CssBox {
  readonly left: number
  readonly top: number
  readonly width: number
  readonly height: number
}

export interface CssPoint {
  readonly x: number
  readonly y: number
}

export interface CoverGeometry {
  readonly scale: number
  readonly mediaBox: CssBox
  readonly focalPoint: CssPoint
  readonly hitBox?: CssBox
}

const assertFinitePositive = (value: number, path: string): void => {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${path} must be a finite positive number`)
  }
}

const assertNormalizedPoint = (
  point: CoverGeometrySource["objectPosition"] | CoverGeometrySource["focalPoint"],
  path: "focalPoint" | "objectPosition",
): void => {
  if (
    point === null ||
    typeof point !== "object" ||
    !Number.isFinite(point.x) ||
    !Number.isFinite(point.y) ||
    point.x < 0 ||
    point.x > 1 ||
    point.y < 0 ||
    point.y > 1
  ) {
    throw new RangeError(`${path} must contain normalized finite coordinates`)
  }
}

const assertNormalizedHitBox = (
  hitBox: NonNullable<CoverGeometrySource["hitBox"]>,
): void => {
  if (
    hitBox === null ||
    typeof hitBox !== "object" ||
    !Number.isFinite(hitBox.x) ||
    !Number.isFinite(hitBox.y) ||
    !Number.isFinite(hitBox.width) ||
    !Number.isFinite(hitBox.height) ||
    hitBox.x < 0 ||
    hitBox.y < 0 ||
    hitBox.width <= 0 ||
    hitBox.height <= 0 ||
    hitBox.x + hitBox.width > 1 ||
    hitBox.y + hitBox.height > 1
  ) {
    throw new RangeError("hitBox must be a normalized finite box with positive size")
  }
}

const assertFiniteGeometry = (values: readonly number[]): void => {
  if (values.some((value) => !Number.isFinite(value))) {
    throw new RangeError("derived cover geometry must remain finite")
  }
}

/**
 * Projects intrinsic-image coordinates into a CSS container using the same
 * percentage positioning rule as `object-fit: cover` + `object-position`.
 * The hit box is intentionally not clipped: a partially cropped source box
 * remains aligned with the pixels that are still visible in the container.
 */
export const resolveCoverGeometry = (
  source: CoverGeometrySource,
  viewport: ViewportDimensions,
): CoverGeometry => {
  assertFinitePositive(source.intrinsicWidth, "intrinsicWidth")
  assertFinitePositive(source.intrinsicHeight, "intrinsicHeight")
  assertFinitePositive(viewport.width, "viewport.width")
  assertFinitePositive(viewport.height, "viewport.height")
  assertNormalizedPoint(source.focalPoint, "focalPoint")
  assertNormalizedPoint(source.objectPosition, "objectPosition")
  if (source.hitBox !== undefined) assertNormalizedHitBox(source.hitBox)

  const scale = Math.max(
    viewport.width / source.intrinsicWidth,
    viewport.height / source.intrinsicHeight,
  )
  const mediaWidth = source.intrinsicWidth * scale
  const mediaHeight = source.intrinsicHeight * scale

  // CSS percentages position the remaining free space, which is negative on
  // whichever axis `cover` crops. This differs from positioning the source's
  // own percentage point directly at the viewport's percentage point.
  const mediaLeft = (viewport.width - mediaWidth) * source.objectPosition.x
  const mediaTop = (viewport.height - mediaHeight) * source.objectPosition.y

  assertFiniteGeometry([scale, mediaWidth, mediaHeight, mediaLeft, mediaTop])

  const mediaBox: CssBox = {
    left: mediaLeft,
    top: mediaTop,
    width: mediaWidth,
    height: mediaHeight,
  }
  const focalPoint: CssPoint = {
    x: mediaLeft + source.focalPoint.x * mediaWidth,
    y: mediaTop + source.focalPoint.y * mediaHeight,
  }
  assertFiniteGeometry([focalPoint.x, focalPoint.y])

  if (source.hitBox === undefined) return { scale, mediaBox, focalPoint }

  const hitBox: CssBox = {
    left: mediaLeft + source.hitBox.x * mediaWidth,
    top: mediaTop + source.hitBox.y * mediaHeight,
    width: source.hitBox.width * mediaWidth,
    height: source.hitBox.height * mediaHeight,
  }
  assertFiniteGeometry([hitBox.left, hitBox.top, hitBox.width, hitBox.height])

  return { scale, mediaBox, focalPoint, hitBox }
}

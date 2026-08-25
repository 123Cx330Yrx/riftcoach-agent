export type CinematicScene = "portal" | "account"
export type CinematicViewport = "desktop" | "mobile"

export interface CinematicNormalizedPoint {
  readonly x: number
  readonly y: number
}

export interface CinematicNormalizedHitBox extends CinematicNormalizedPoint {
  readonly width: number
  readonly height: number
}

export interface CinematicMediaRendition {
  readonly intrinsicWidth: number
  readonly intrinsicHeight: number
  readonly posterAvif: string
  readonly posterWebp: string
  readonly vp9Webm: string
  readonly h264Mp4: string
  readonly focalPoint: CinematicNormalizedPoint
  readonly hitBox?: CinematicNormalizedHitBox
  readonly objectPosition: CinematicNormalizedPoint
}

export interface CinematicMediaManifestEntry {
  readonly scene: CinematicScene
  readonly viewport: CinematicViewport
  readonly rendition: CinematicMediaRendition
}

export interface CinematicMediaManifest {
  readonly schemaVersion: "1.0"
  readonly renditions: readonly CinematicMediaManifestEntry[]
}

type UnknownRecord = Record<string, unknown>

const SCENES = ["portal", "account"] as const satisfies readonly CinematicScene[]
const VIEWPORTS = ["desktop", "mobile"] as const satisfies readonly CinematicViewport[]
const REQUIRED_RENDITION_KEYS = [
  "intrinsicWidth",
  "intrinsicHeight",
  "posterAvif",
  "posterWebp",
  "vp9Webm",
  "h264Mp4",
  "focalPoint",
  "objectPosition",
] as const
const MAX_INTRINSIC_DIMENSION = 16_384
const MAX_LOCAL_ASSET_URL_LENGTH = 1_024
const CONTROL_CHARACTER = /[\u0000-\u001F\u007F]/

function record(value: unknown, path: string): UnknownRecord {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${path} must be an object`)
  }
  const prototype = Object.getPrototypeOf(value)
  if (prototype !== Object.prototype && prototype !== null) {
    throw new Error(`${path} must be a plain object`)
  }
  return value as UnknownRecord
}

function exact(
  value: UnknownRecord,
  requiredKeys: readonly string[],
  optionalKeys: readonly string[],
  path: string,
): void {
  const allowed = new Set([...requiredKeys, ...optionalKeys])
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) throw new Error(`${path} has unexpected key ${key}`)
  }
  for (const key of requiredKeys) {
    if (!Object.prototype.hasOwnProperty.call(value, key)) {
      throw new Error(`${path} is missing key ${key}`)
    }
  }
}

function enumeration<T extends string>(value: unknown, allowed: readonly T[], path: string): T {
  if (typeof value !== "string" || !allowed.includes(value as T)) {
    throw new Error(`${path} has an unsupported identity`)
  }
  return value as T
}

function dimension(value: unknown, path: string): number {
  if (
    typeof value !== "number"
    || !Number.isInteger(value)
    || value < 1
    || value > MAX_INTRINSIC_DIMENSION
  ) {
    throw new Error(`${path} must be a positive bounded pixel dimension`)
  }
  return value
}

function normalizedNumber(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error(`${path} must be a normalized number from 0 through 1`)
  }
  return value
}

function normalizedPoint(value: unknown, path: string): CinematicNormalizedPoint {
  const row = record(value, path)
  exact(row, ["x", "y"], [], path)
  return {
    x: normalizedNumber(row.x, `${path}.x`),
    y: normalizedNumber(row.y, `${path}.y`),
  }
}

function normalizedHitBox(value: unknown, path: string): CinematicNormalizedHitBox {
  const row = record(value, path)
  exact(row, ["x", "y", "width", "height"], [], path)
  const hitBox = {
    x: normalizedNumber(row.x, `${path}.x`),
    y: normalizedNumber(row.y, `${path}.y`),
    width: normalizedNumber(row.width, `${path}.width`),
    height: normalizedNumber(row.height, `${path}.height`),
  }
  if (hitBox.width === 0 || hitBox.height === 0) {
    throw new Error(`${path} width and height must be non-zero normalized values`)
  }
  if (hitBox.x + hitBox.width > 1 + Number.EPSILON || hitBox.y + hitBox.height > 1 + Number.EPSILON) {
    throw new Error(`${path} must remain inside normalized source bounds`)
  }
  return hitBox
}

function localAssetUrl(
  value: unknown,
  scene: CinematicScene,
  viewport: CinematicViewport,
  kind: "poster" | "loop",
  extension: "avif" | "webp" | "webm" | "mp4",
  path: string,
): string {
  if (
    typeof value !== "string"
    || value.length < 1
    || value.length > MAX_LOCAL_ASSET_URL_LENGTH
    || value.trim() !== value
    || CONTROL_CHARACTER.test(value)
    || !value.startsWith("/")
    || value.startsWith("//")
    || value.includes("\\")
    || value.includes("?")
    || value.includes("#")
  ) {
    throw new Error(`${path} must be a bounded local asset URL`)
  }

  let decodedPath: string
  try {
    decodedPath = decodeURIComponent(value)
  } catch {
    throw new Error(`${path} must be a valid local asset URL`)
  }
  if (
    CONTROL_CHARACTER.test(decodedPath)
    || decodedPath.includes("\\")
    || decodedPath.split("/").some((segment) => segment === "." || segment === "..")
  ) {
    throw new Error(`${path} local asset URL cannot traverse directories`)
  }

  const fileName = decodedPath.slice(decodedPath.lastIndexOf("/") + 1)
  const identityPrefix = `${scene}-${viewport}-${kind}`
  if (
    !(fileName === `${identityPrefix}.${extension}` || fileName.startsWith(`${identityPrefix}-`))
    || !fileName.endsWith(`.${extension}`)
  ) {
    throw new Error(`${path} must preserve ${scene}/${viewport}/${extension} asset identity`)
  }
  return value
}

function decodeRendition(
  value: unknown,
  scene: CinematicScene,
  viewport: CinematicViewport,
  path: string,
): CinematicMediaRendition {
  const row = record(value, path)
  exact(row, REQUIRED_RENDITION_KEYS, ["hitBox"], path)

  const base: CinematicMediaRendition = {
    intrinsicWidth: dimension(row.intrinsicWidth, `${path}.intrinsicWidth`),
    intrinsicHeight: dimension(row.intrinsicHeight, `${path}.intrinsicHeight`),
    posterAvif: localAssetUrl(row.posterAvif, scene, viewport, "poster", "avif", `${path}.posterAvif`),
    posterWebp: localAssetUrl(row.posterWebp, scene, viewport, "poster", "webp", `${path}.posterWebp`),
    vp9Webm: localAssetUrl(row.vp9Webm, scene, viewport, "loop", "webm", `${path}.vp9Webm`),
    h264Mp4: localAssetUrl(row.h264Mp4, scene, viewport, "loop", "mp4", `${path}.h264Mp4`),
    focalPoint: normalizedPoint(row.focalPoint, `${path}.focalPoint`),
    objectPosition: normalizedPoint(row.objectPosition, `${path}.objectPosition`),
  }
  const hasHitBox = Object.prototype.hasOwnProperty.call(row, "hitBox")

  if (scene === "portal") {
    if (!hasHitBox) throw new Error(`${path} portal identity requires a crystal hitBox`)
    return { ...base, hitBox: normalizedHitBox(row.hitBox, `${path}.hitBox`) }
  }
  if (hasHitBox) throw new Error(`${path} account identity cannot define a portal hitBox`)
  return base
}

function decodeEntry(value: unknown, index: number): CinematicMediaManifestEntry {
  const path = `cinematicMediaManifest.renditions[${index}]`
  const row = record(value, path)
  exact(row, ["scene", "viewport", "rendition"], [], path)
  const scene = enumeration(row.scene, SCENES, `${path}.scene`)
  const viewport = enumeration(row.viewport, VIEWPORTS, `${path}.viewport`)
  return {
    scene,
    viewport,
    rendition: decodeRendition(row.rendition, scene, viewport, `${path}.rendition`),
  }
}

function entryIdentity(entry: Pick<CinematicMediaManifestEntry, "scene" | "viewport">): string {
  return `${entry.scene}:${entry.viewport}`
}

export function decodeCinematicMediaManifest(value: unknown): CinematicMediaManifest {
  const row = record(value, "cinematicMediaManifest")
  exact(row, ["schemaVersion", "renditions"], [], "cinematicMediaManifest")
  if (row.schemaVersion !== "1.0") {
    throw new Error("cinematicMediaManifest.schemaVersion must be 1.0")
  }
  if (!Array.isArray(row.renditions)) {
    throw new Error("cinematicMediaManifest.renditions must be an array")
  }

  const renditions = row.renditions.map(decodeEntry)
  const seenIdentities = new Set<string>()
  const seenUrls = new Set<string>()
  for (const entry of renditions) {
    const identity = entryIdentity(entry)
    if (seenIdentities.has(identity)) {
      throw new Error(`cinematicMediaManifest has duplicate ${entry.scene}/${entry.viewport} identity`)
    }
    seenIdentities.add(identity)
    for (const url of [
      entry.rendition.posterAvif,
      entry.rendition.posterWebp,
      entry.rendition.vp9Webm,
      entry.rendition.h264Mp4,
    ]) {
      if (seenUrls.has(url)) throw new Error(`cinematicMediaManifest has duplicate asset URL identity: ${url}`)
      seenUrls.add(url)
    }
  }

  for (const scene of SCENES) {
    for (const viewport of VIEWPORTS) {
      if (!seenIdentities.has(`${scene}:${viewport}`)) {
        throw new Error(`cinematicMediaManifest is missing ${scene}/${viewport} rendition`)
      }
    }
  }
  if (renditions.length !== SCENES.length * VIEWPORTS.length) {
    throw new Error("cinematicMediaManifest must contain the exact scene/viewport matrix")
  }

  const sceneOrder = new Map<CinematicScene, number>(SCENES.map((scene, index) => [scene, index]))
  const viewportOrder = new Map<CinematicViewport, number>(VIEWPORTS.map((viewport, index) => [viewport, index]))
  renditions.sort((left, right) => (
    (sceneOrder.get(left.scene) ?? 0) - (sceneOrder.get(right.scene) ?? 0)
    || (viewportOrder.get(left.viewport) ?? 0) - (viewportOrder.get(right.viewport) ?? 0)
  ))
  return { schemaVersion: "1.0", renditions }
}

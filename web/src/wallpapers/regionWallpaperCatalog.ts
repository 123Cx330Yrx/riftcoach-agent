export type WallpaperRegion = "demacia"
export type WallpaperStatus = "research-candidate"

export interface RegionWallpaperCandidate {
  readonly id: string
  readonly region: WallpaperRegion
  readonly status: WallpaperStatus
  readonly label: Readonly<{ "zh-CN": string; en: string }>
  readonly description: Readonly<{ "zh-CN": string; en: string }>
  readonly poster: string
  readonly webm: string
  readonly mp4: string
  readonly intrinsicWidth: number
  readonly intrinsicHeight: number
  readonly fps: number
  readonly durationSeconds: number
  readonly focalPoint: Readonly<{ x: number; y: number }>
  readonly sourceDigest: string
  readonly rights: "unverified"
}

export interface RegionWallpaperCatalog {
  readonly schemaVersion: "1.0"
  readonly candidates: readonly RegionWallpaperCandidate[]
}

const LOCAL_ASSET = /^\/assets\/wallpapers\/candidates\/[a-z0-9-]+\.(webp|webm|mp4)$/
const SHA256 = /^[a-f0-9]{64}$/

function assertLocalAsset(value: unknown, path: string): string {
  if (typeof value !== "string" || !LOCAL_ASSET.test(value)) throw new Error(`${path} must be a local wallpaper asset`)
  return value
}

function assertText(value: unknown, path: string): Readonly<{ "zh-CN": string; en: string }> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path} must be bilingual text`)
  const row = value as Record<string, unknown>
  if (Object.keys(row).sort().join(",") !== "en,zh-CN" || typeof row.en !== "string" || typeof row["zh-CN"] !== "string") {
    throw new Error(`${path} must contain exactly zh-CN and en`)
  }
  return { "zh-CN": row["zh-CN"], en: row.en }
}

export function decodeRegionWallpaperCatalog(value: unknown): RegionWallpaperCatalog {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error("wallpaper catalog must be an object")
  const row = value as Record<string, unknown>
  if (row.schemaVersion !== "1.0" || !Array.isArray(row.candidates)) throw new Error("wallpaper catalog schema mismatch")
  const candidates = row.candidates.map((candidate, index) => {
    if (candidate === null || typeof candidate !== "object" || Array.isArray(candidate)) throw new Error(`candidate[${index}] must be an object`)
    const item = candidate as Record<string, unknown>
    if (item.region !== "demacia" || item.status !== "research-candidate" || typeof item.id !== "string") throw new Error(`candidate[${index}] identity is invalid`)
    const focal = item.focalPoint as Record<string, unknown> | null
    if (focal === null || typeof focal !== "object" || typeof focal.x !== "number" || typeof focal.y !== "number" || focal.x < 0 || focal.x > 1 || focal.y < 0 || focal.y > 1) throw new Error(`candidate[${index}].focalPoint is invalid`)
    if (typeof item.intrinsicWidth !== "number" || typeof item.intrinsicHeight !== "number" || typeof item.fps !== "number" || typeof item.durationSeconds !== "number") throw new Error(`candidate[${index}] dimensions are invalid`)
    if (typeof item.sourceDigest !== "string" || !SHA256.test(item.sourceDigest)) throw new Error(`candidate[${index}].sourceDigest is invalid`)
    if (item.rights !== "unverified") throw new Error(`candidate[${index}].rights must be unverified before adoption`)
    return {
      id: item.id,
      region: "demacia" as const,
      status: "research-candidate" as const,
      label: assertText(item.label, `candidate[${index}].label`),
      description: assertText(item.description, `candidate[${index}].description`),
      poster: assertLocalAsset(item.poster, `candidate[${index}].poster`),
      webm: assertLocalAsset(item.webm, `candidate[${index}].webm`),
      mp4: assertLocalAsset(item.mp4, `candidate[${index}].mp4`),
      intrinsicWidth: item.intrinsicWidth,
      intrinsicHeight: item.intrinsicHeight,
      fps: item.fps,
      durationSeconds: item.durationSeconds,
      focalPoint: { x: focal.x, y: focal.y },
      sourceDigest: item.sourceDigest,
      rights: "unverified" as const,
    }
  })
  const ids = new Set<string>()
  for (const candidate of candidates) {
    if (ids.has(candidate.id)) throw new Error(`duplicate wallpaper id ${candidate.id}`)
    ids.add(candidate.id)
  }
  return { schemaVersion: "1.0", candidates }
}

export const regionWallpaperCatalog = decodeRegionWallpaperCatalog({
  schemaVersion: "1.0",
  candidates: [{
    id: "demacia-v1",
    region: "demacia",
    status: "research-candidate",
    label: { "zh-CN": "德玛西亚", en: "Demacia" },
    description: { "zh-CN": "官方动态壁纸候选 · 本地预览", en: "Official wallpaper candidate · local preview" },
    poster: "/assets/wallpapers/candidates/demacia-poster.webp",
    webm: "/assets/wallpapers/candidates/demacia.webm",
    mp4: "/assets/wallpapers/candidates/demacia.mp4",
    intrinsicWidth: 1920,
    intrinsicHeight: 1080,
    fps: 25,
    durationSeconds: 15.04,
    focalPoint: { x: 0.5, y: 0.5 },
    sourceDigest: "e57f1f1c470f3e1a2499e8622b30f61cabafc2c775d3c54f39dcdcbd31c13507",
    rights: "unverified",
  }],
})

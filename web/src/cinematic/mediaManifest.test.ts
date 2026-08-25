import { describe, expect, it } from "vitest"

import {
  decodeCinematicMediaManifest,
  type CinematicMediaManifest,
  type CinematicScene,
  type CinematicViewport,
} from "./mediaManifest"

type MutableRecord = Record<string, unknown>

function localAsset(
  scene: CinematicScene,
  viewport: CinematicViewport,
  kind: "poster" | "loop",
  extension: "avif" | "webp" | "webm" | "mp4",
): string {
  return `/__cinematic-test-fixtures__/${scene}-${viewport}-${kind}.${extension}`
}

function rendition(scene: CinematicScene, viewport: CinematicViewport): MutableRecord {
  const value: MutableRecord = {
    intrinsicWidth: viewport === "desktop" ? 1672 : 900,
    intrinsicHeight: viewport === "desktop" ? 941 : 1600,
    posterAvif: localAsset(scene, viewport, "poster", "avif"),
    posterWebp: localAsset(scene, viewport, "poster", "webp"),
    vp9Webm: localAsset(scene, viewport, "loop", "webm"),
    h264Mp4: localAsset(scene, viewport, "loop", "mp4"),
    focalPoint: { x: 0.5, y: 0.48 },
    objectPosition: { x: 0.5, y: 0.5 },
  }
  if (scene === "portal") {
    value.hitBox = { x: 0.45, y: 0.25, width: 0.1, height: 0.32 }
  }
  return value
}

function manifest(): MutableRecord {
  return {
    schemaVersion: "1.0",
    renditions: [
      { scene: "portal", viewport: "desktop", rendition: rendition("portal", "desktop") },
      { scene: "portal", viewport: "mobile", rendition: rendition("portal", "mobile") },
      { scene: "account", viewport: "desktop", rendition: rendition("account", "desktop") },
      { scene: "account", viewport: "mobile", rendition: rendition("account", "mobile") },
    ],
  }
}

function entries(value: MutableRecord): MutableRecord[] {
  return value.renditions as MutableRecord[]
}

function media(value: MutableRecord, index = 0): MutableRecord {
  return entries(value)[index]!.rendition as MutableRecord
}

describe("decodeCinematicMediaManifest", () => {
  it("decodes one exact local rendition for every scene and viewport", () => {
    const decoded: CinematicMediaManifest = decodeCinematicMediaManifest(manifest())

    expect(decoded.schemaVersion).toBe("1.0")
    expect(decoded.renditions.map(({ scene, viewport }) => `${scene}:${viewport}`)).toEqual([
      "portal:desktop",
      "portal:mobile",
      "account:desktop",
      "account:mobile",
    ])
    expect(decoded.renditions[0]?.rendition.hitBox).toEqual({
      x: 0.45,
      y: 0.25,
      width: 0.1,
      height: 0.32,
    })
    expect(decoded.renditions[2]?.rendition.hitBox).toBeUndefined()
  })

  it.each([
    ["root", (value: MutableRecord) => Object.assign(value, { productionUrl: "/secret.mp4" })],
    ["entry", (value: MutableRecord) => Object.assign(entries(value)[0]!, { identity: "portal" })],
    ["rendition", (value: MutableRecord) => Object.assign(media(value), { sourceSha: "not-runtime-data" })],
    ["point", (value: MutableRecord) => Object.assign(media(value).focalPoint as MutableRecord, { z: 0 })],
    ["hit box", (value: MutableRecord) => Object.assign(media(value).hitBox as MutableRecord, { radius: 1 })],
  ])("rejects unknown keys at the %s boundary", (_label, mutate) => {
    const value = manifest()
    mutate(value)

    expect(() => decodeCinematicMediaManifest(value)).toThrow(/unexpected key/i)
  })

  it.each(["scene", "viewport"])("rejects a missing %s identity", (key) => {
    const value = manifest()
    delete entries(value)[0]![key]

    expect(() => decodeCinematicMediaManifest(value)).toThrow(new RegExp(`missing key ${key}`, "i"))
  })

  it("rejects schema, scene and viewport enum drift", () => {
    const badSchema = manifest()
    badSchema.schemaVersion = "2.0"
    const badScene = manifest()
    entries(badScene)[0]!.scene = "landing"
    const badViewport = manifest()
    entries(badViewport)[0]!.viewport = "tablet"

    expect(() => decodeCinematicMediaManifest(badSchema)).toThrow(/schemaVersion.*1\.0/i)
    expect(() => decodeCinematicMediaManifest(badScene)).toThrow(/scene.*identity/i)
    expect(() => decodeCinematicMediaManifest(badViewport)).toThrow(/viewport.*identity/i)
  })

  it("rejects non-plain objects instead of accepting inherited manifest fields", () => {
    const inherited = Object.create(manifest()) as unknown

    expect(() => decodeCinematicMediaManifest(inherited)).toThrow(/plain object/i)
  })

  it("rejects duplicate and incomplete scene/viewport matrices", () => {
    const duplicate = manifest()
    entries(duplicate)[1] = {
      scene: "portal",
      viewport: "desktop",
      rendition: rendition("portal", "desktop"),
    }
    const incomplete = manifest()
    entries(incomplete).pop()

    expect(() => decodeCinematicMediaManifest(duplicate)).toThrow(/duplicate.*portal.*desktop/i)
    expect(() => decodeCinematicMediaManifest(incomplete)).toThrow(/missing.*account.*mobile/i)
  })

  it.each([
    ["zero width", (value: MutableRecord) => Object.assign(media(value), { intrinsicWidth: 0 })],
    ["fractional height", (value: MutableRecord) => Object.assign(media(value), { intrinsicHeight: 941.5 })],
    ["focal point", (value: MutableRecord) => Object.assign(media(value).focalPoint as MutableRecord, { x: 1.01 })],
    [
      "object position",
      (value: MutableRecord) => Object.assign(media(value).objectPosition as MutableRecord, { y: -0.01 }),
    ],
    ["empty hit box", (value: MutableRecord) => Object.assign(media(value).hitBox as MutableRecord, { width: 0 })],
    ["overflowing hit box", (value: MutableRecord) => Object.assign(media(value).hitBox as MutableRecord, { x: 0.95 })],
  ])("rejects invalid normalized geometry: %s", (_label, mutate) => {
    const value = manifest()
    mutate(value)

    expect(() => decodeCinematicMediaManifest(value)).toThrow(/dimension|normalized|hitbox/i)
  })

  it.each([
    ["empty", ""],
    ["remote https", "https://cdn.example/portal-desktop-poster.avif"],
    ["protocol relative", "//cdn.example/portal-desktop-poster.avif"],
    ["data", "data:image/avif;base64,AAAA"],
    ["path traversal", "/assets/../portal-desktop-poster.avif"],
    ["encoded path traversal", "/assets/%2e%2e/portal-desktop-poster.avif"],
    ["wrong format", "/assets/portal-desktop-poster.webp"],
  ])("rejects %s media URLs", (_label, url) => {
    const value = manifest()
    media(value).posterAvif = url

    expect(() => decodeCinematicMediaManifest(value)).toThrow(/local|url|avif/i)
  })

  it("rejects scene/viewport identity interchange instead of trusting array position", () => {
    const swappedScene = manifest()
    entries(swappedScene)[0]!.rendition = rendition("account", "desktop")
    const swappedViewport = manifest()
    entries(swappedViewport)[0]!.rendition = rendition("portal", "mobile")

    expect(() => decodeCinematicMediaManifest(swappedScene)).toThrow(/portal|hitbox|identity/i)
    expect(() => decodeCinematicMediaManifest(swappedViewport)).toThrow(/desktop|identity/i)
  })

  it("rejects duplicate asset URLs across otherwise distinct entries", () => {
    const value = manifest()
    media(value, 1).posterAvif = media(value, 0).posterAvif

    expect(() => decodeCinematicMediaManifest(value)).toThrow(/identity|duplicate/i)
  })
})

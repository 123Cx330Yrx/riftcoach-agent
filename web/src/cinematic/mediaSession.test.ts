import { describe, expect, it } from "vitest"

import {
  createCinematicMediaSession,
  createCinematicMediaSessions,
  reduceCinematicMediaSession,
  reduceCinematicMediaSessions,
  shouldMountCinematicVideo,
  type CinematicMediaSessionEvent,
} from "./mediaSession"

describe("reduceCinematicMediaSession", () => {
  it("starts with a visible poster and motion unpaused", () => {
    expect(createCinematicMediaSession()).toEqual({
      playbackState: "poster",
      userPaused: false,
    })
  })

  it("moves through one poster-first playback attempt", () => {
    const poster = createCinematicMediaSession()
    const loading = reduceCinematicMediaSession(poster, { type: "attempt-started" })
    const playing = reduceCinematicMediaSession(loading, { type: "play-confirmed" })

    expect(loading).toEqual({ playbackState: "loading", userPaused: false })
    expect(playing).toEqual({ playbackState: "playing", userPaused: false })
  })

  it.each([
    "loading",
    "playing",
  ] as const)("makes a current %s playback failure sticky", (playbackState) => {
    const failed = reduceCinematicMediaSession(
      { playbackState, userPaused: false },
      { type: "play-failed" },
    )

    expect(failed).toEqual({ playbackState: "failed-sticky", userPaused: false })
  })

  it("ignores a stale failure while no playback attempt is active", () => {
    const poster = createCinematicMediaSession()

    expect(reduceCinematicMediaSession(poster, { type: "play-failed" })).toBe(poster)
  })

  it("never revives a failed-sticky session", () => {
    const failed = { playbackState: "failed-sticky", userPaused: false } as const
    const events: readonly CinematicMediaSessionEvent[] = [
      { type: "poster-required" },
      { type: "attempt-started" },
      { type: "play-confirmed" },
      { type: "play-failed" },
    ]

    for (const event of events) {
      expect(reduceCinematicMediaSession(failed, event)).toBe(failed)
    }
  })

  it("returns non-failed playback to poster when policy no longer permits video", () => {
    expect(reduceCinematicMediaSession(
      { playbackState: "loading", userPaused: false },
      { type: "poster-required" },
    )).toEqual({ playbackState: "poster", userPaused: false })
    expect(reduceCinematicMediaSession(
      { playbackState: "playing", userPaused: true },
      { type: "poster-required" },
    )).toEqual({ playbackState: "poster", userPaused: true })
  })

  it("keeps user pause orthogonal to playback state and idempotent", () => {
    const playing = { playbackState: "playing", userPaused: false } as const
    const paused = reduceCinematicMediaSession(playing, {
      type: "user-paused-changed",
      paused: true,
    })

    expect(paused).toEqual({ playbackState: "playing", userPaused: true })
    expect(reduceCinematicMediaSession(paused, {
      type: "user-paused-changed",
      paused: true,
    })).toBe(paused)
    expect(reduceCinematicMediaSession(paused, {
      type: "user-paused-changed",
      paused: false,
    })).toEqual({ playbackState: "playing", userPaused: false })
  })

  it("preserves failure while changing the independent pause choice", () => {
    expect(reduceCinematicMediaSession(
      { playbackState: "failed-sticky", userPaused: false },
      { type: "user-paused-changed", paused: true },
    )).toEqual({ playbackState: "failed-sticky", userPaused: true })
  })

  it("returns the original object for duplicate or out-of-order success events", () => {
    const loading = { playbackState: "loading", userPaused: false } as const
    const playing = { playbackState: "playing", userPaused: false } as const

    expect(reduceCinematicMediaSession(loading, { type: "attempt-started" })).toBe(loading)
    expect(reduceCinematicMediaSession(playing, { type: "play-confirmed" })).toBe(playing)
    expect(reduceCinematicMediaSession(createCinematicMediaSession(), {
      type: "play-confirmed",
    }).playbackState).toBe("poster")
  })
})

describe("page-session scene isolation", () => {
  it("creates independent Portal and Account sessions", () => {
    expect(createCinematicMediaSessions()).toEqual({
      portal: { playbackState: "poster", userPaused: false },
      account: { playbackState: "poster", userPaused: false },
    })
  })

  it("updates one scene without replacing the other", () => {
    const initial = createCinematicMediaSessions()
    const next = reduceCinematicMediaSessions(initial, {
      scene: "portal",
      event: { type: "attempt-started" },
    })

    expect(next).not.toBe(initial)
    expect(next.portal.playbackState).toBe("loading")
    expect(next.account).toBe(initial.account)
    expect(reduceCinematicMediaSessions(next, {
      scene: "account",
      event: { type: "play-confirmed" },
    })).toBe(next)
  })
})

describe("shouldMountCinematicVideo", () => {
  it("mounts only for an eligible non-failed motion session", () => {
    expect(shouldMountCinematicVideo(
      { mode: "motion", viewport: "desktop" },
      createCinematicMediaSession(),
    )).toBe(true)
    expect(shouldMountCinematicVideo(
      { mode: "motion", viewport: "mobile" },
      { playbackState: "failed-sticky", userPaused: false },
    )).toBe(false)
  })

  it.each([
    { mode: "poster", viewport: "desktop", reason: "preflight" },
    { mode: "poster", viewport: "mobile", reason: "reduced-motion" },
    { mode: "poster", viewport: "mobile", reason: "save-data" },
  ] as const)("keeps video/source out of the $reason poster branch", (policy) => {
    expect(shouldMountCinematicVideo(policy, createCinematicMediaSession())).toBe(false)
  })

  it("keeps a user-paused eligible video mounted without changing failure semantics", () => {
    expect(shouldMountCinematicVideo(
      { mode: "motion", viewport: "desktop" },
      { playbackState: "playing", userPaused: true },
    )).toBe(true)
  })
})

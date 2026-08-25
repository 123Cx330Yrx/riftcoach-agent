import type { CinematicScene } from "./mediaManifest"
import type { CinematicMediaPolicy } from "./mediaPolicy"

export type CinematicPlaybackState =
  | "poster"
  | "loading"
  | "playing"
  | "failed-sticky"

export interface CinematicMediaSession {
  readonly playbackState: CinematicPlaybackState
  readonly userPaused: boolean
}

export type CinematicMediaSessionEvent =
  | { readonly type: "poster-required" }
  | { readonly type: "attempt-started" }
  | { readonly type: "play-confirmed" }
  | { readonly type: "play-failed" }
  | { readonly type: "user-paused-changed"; readonly paused: boolean }

export type CinematicMediaSessions = Readonly<
  Record<CinematicScene, CinematicMediaSession>
>

export function createCinematicMediaSession(): CinematicMediaSession {
  return { playbackState: "poster", userPaused: false }
}

export function createCinematicMediaSessions(): CinematicMediaSessions {
  return {
    portal: createCinematicMediaSession(),
    account: createCinematicMediaSession(),
  }
}

export function reduceCinematicMediaSession(
  state: CinematicMediaSession,
  event: CinematicMediaSessionEvent,
): CinematicMediaSession {
  if (event.type === "user-paused-changed") {
    return state.userPaused === event.paused
      ? state
      : { ...state, userPaused: event.paused }
  }

  if (state.playbackState === "failed-sticky") return state

  switch (event.type) {
    case "poster-required":
      return state.playbackState === "poster"
        ? state
        : { ...state, playbackState: "poster" }
    case "attempt-started":
      return state.playbackState === "loading"
        ? state
        : { ...state, playbackState: "loading" }
    case "play-confirmed":
      return state.playbackState === "loading"
        ? { ...state, playbackState: "playing" }
        : state
    case "play-failed":
      return state.playbackState === "loading" || state.playbackState === "playing"
        ? { ...state, playbackState: "failed-sticky" }
        : state
  }
}

export function reduceCinematicMediaSessions(
  state: CinematicMediaSessions,
  action: {
    readonly scene: CinematicScene
    readonly event: CinematicMediaSessionEvent
  },
): CinematicMediaSessions {
  const current = state[action.scene]
  const next = reduceCinematicMediaSession(current, action.event)
  return next === current ? state : { ...state, [action.scene]: next }
}

export function shouldMountCinematicVideo(
  policy: CinematicMediaPolicy,
  session: CinematicMediaSession,
): boolean {
  return policy.mode === "motion" && session.playbackState !== "failed-sticky"
}

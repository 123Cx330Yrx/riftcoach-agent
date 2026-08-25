import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type SyntheticEvent,
} from "react"

import type {
  CinematicMediaManifest,
  CinematicMediaRendition,
  CinematicScene,
  CinematicViewport,
} from "../cinematic/mediaManifest"
import type { CinematicMediaPolicy } from "../cinematic/mediaPolicy"
import {
  shouldMountCinematicVideo,
  type CinematicMediaSession,
  type CinematicMediaSessionEvent,
} from "../cinematic/mediaSession"

export interface CinematicPosterSettledEvent {
  readonly scene: CinematicScene
  readonly viewport: CinematicViewport
  readonly status: "loaded" | "failed"
}

export interface CinematicSceneMediaProps {
  readonly scene: CinematicScene
  readonly manifest: CinematicMediaManifest
  readonly policy: CinematicMediaPolicy
  readonly session: CinematicMediaSession
  readonly onSessionEvent: (event: CinematicMediaSessionEvent) => void
  readonly onPosterSettled?: (event: CinematicPosterSettledEvent) => void
}

interface PosterSettlement {
  readonly identity: string
  readonly status: CinematicPosterSettledEvent["status"] | undefined
}

function selectRendition(
  manifest: CinematicMediaManifest,
  scene: CinematicScene,
  viewport: CinematicViewport,
): CinematicMediaRendition {
  const entry = manifest.renditions.find(
    (candidate) => candidate.scene === scene && candidate.viewport === viewport,
  )
  if (entry === undefined) {
    throw new Error(`cinematic media manifest is missing ${scene}/${viewport}`)
  }
  return entry.rendition
}

function renditionIdentity(
  scene: CinematicScene,
  viewport: CinematicViewport,
  rendition: CinematicMediaRendition,
): string {
  return JSON.stringify([
    scene,
    viewport,
    rendition.posterAvif,
    rendition.posterWebp,
    rendition.vp9Webm,
    rendition.h264Mp4,
  ])
}

export function CinematicSceneMedia({
  scene,
  manifest,
  policy,
  session,
  onSessionEvent,
  onPosterSettled,
}: CinematicSceneMediaProps) {
  const rendition = selectRendition(manifest, scene, policy.viewport)
  const identity = renditionIdentity(scene, policy.viewport, rendition)
  const mountVideo = shouldMountCinematicVideo(policy, session)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const mountedRef = useRef(false)
  const sessionRef = useRef(session)
  const mountVideoRef = useRef(mountVideo)
  const identityRef = useRef(identity)
  const onSessionEventRef = useRef(onSessionEvent)
  const onPosterSettledRef = useRef(onPosterSettled)
  const attemptSequenceRef = useRef(0)
  const activeAttemptRef = useRef(0)
  const playRequestSequenceRef = useRef(0)
  const pendingPlayRequestRef = useRef(0)
  const readyRef = useRef(false)
  const posterSettlementRef = useRef<PosterSettlement>({
    identity,
    status: undefined,
  })
  const [confirmedVideoIdentity, setConfirmedVideoIdentity] = useState<string>()
  const [posterSettlement, setPosterSettlement] = useState<PosterSettlement>({
    identity,
    status: undefined,
  })

  sessionRef.current = session
  mountVideoRef.current = mountVideo
  identityRef.current = identity
  onSessionEventRef.current = onSessionEvent
  onPosterSettledRef.current = onPosterSettled
  if (posterSettlementRef.current.identity !== identity) {
    posterSettlementRef.current = { identity, status: undefined }
  }

  const emitSessionEvent = useCallback((event: CinematicMediaSessionEvent): void => {
    onSessionEventRef.current(event)
  }, [])

  const invalidatePlayRequest = useCallback((): void => {
    playRequestSequenceRef.current += 1
    pendingPlayRequestRef.current = 0
  }, [])

  const requestPlay = useCallback((
    video: HTMLVideoElement,
    attempt: number,
    expectedIdentity: string,
  ): void => {
    if (
      activeAttemptRef.current !== attempt
      || identityRef.current !== expectedIdentity
      || videoRef.current !== video
      || !mountedRef.current
      || attempt <= 0
      || !mountVideoRef.current
      || (sessionRef.current.playbackState !== "loading"
        && sessionRef.current.playbackState !== "playing")
      || sessionRef.current.userPaused
      || document.hidden
      || !readyRef.current
      || pendingPlayRequestRef.current !== 0
    ) {
      return
    }

    const request = ++playRequestSequenceRef.current
    pendingPlayRequestRef.current = request
    let playResult: Promise<void> | undefined
    try {
      playResult = video.play()
    } catch {
      if (
        pendingPlayRequestRef.current === request
        && activeAttemptRef.current === attempt
        && identityRef.current === expectedIdentity
      ) {
        pendingPlayRequestRef.current = 0
        setConfirmedVideoIdentity(undefined)
        emitSessionEvent({ type: "play-failed" })
      }
      return
    }

    void Promise.resolve(playResult).then(
      () => {
        if (
          pendingPlayRequestRef.current !== request
          || activeAttemptRef.current !== attempt
          || identityRef.current !== expectedIdentity
          || videoRef.current !== video
          || !mountedRef.current
          || !mountVideoRef.current
          || sessionRef.current.playbackState === "failed-sticky"
          || sessionRef.current.userPaused
          || document.hidden
        ) {
          return
        }
        pendingPlayRequestRef.current = 0
        setConfirmedVideoIdentity(expectedIdentity)
        emitSessionEvent({ type: "play-confirmed" })
      },
      () => {
        if (
          pendingPlayRequestRef.current !== request
          || activeAttemptRef.current !== attempt
          || identityRef.current !== expectedIdentity
          || videoRef.current !== video
          || !mountedRef.current
          || !mountVideoRef.current
          || sessionRef.current.userPaused
          || document.hidden
        ) {
          return
        }
        pendingPlayRequestRef.current = 0
        setConfirmedVideoIdentity(undefined)
        emitSessionEvent({ type: "play-failed" })
      },
    )
  }, [emitSessionEvent])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      activeAttemptRef.current = 0
      invalidatePlayRequest()
    }
  }, [invalidatePlayRequest])

  useEffect(() => {
    if (!mountVideo) {
      invalidatePlayRequest()
      readyRef.current = false
      setConfirmedVideoIdentity(undefined)
      emitSessionEvent({ type: "poster-required" })
      return
    }

    const video = videoRef.current
    if (video === null) return
    const attempt = ++attemptSequenceRef.current
    activeAttemptRef.current = attempt
    readyRef.current = video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA
    invalidatePlayRequest()
    setConfirmedVideoIdentity(undefined)
    emitSessionEvent({ type: "attempt-started" })

    return () => {
      if (activeAttemptRef.current === attempt) activeAttemptRef.current = 0
      invalidatePlayRequest()
      readyRef.current = false
      setConfirmedVideoIdentity(undefined)
      if (videoRef.current === video) videoRef.current = null
      video.pause()
    }
  }, [emitSessionEvent, identity, invalidatePlayRequest, mountVideo, requestPlay])

  useEffect(() => {
    if (!mountVideo || session.playbackState !== "loading") return
    const video = videoRef.current
    if (video === null || !readyRef.current) return
    requestPlay(video, activeAttemptRef.current, identity)
  }, [identity, mountVideo, requestPlay, session.playbackState])

  useEffect(() => {
    const onVisibilityChange = (): void => {
      const video = videoRef.current
      if (video === null || !mountedRef.current) return
      if (document.hidden) {
        invalidatePlayRequest()
        setConfirmedVideoIdentity(undefined)
        video.pause()
        return
      }
      requestPlay(video, activeAttemptRef.current, identityRef.current)
    }
    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => document.removeEventListener("visibilitychange", onVisibilityChange)
  }, [invalidatePlayRequest, requestPlay])

  useEffect(() => {
    const video = videoRef.current
    if (video === null || !mountVideo || !mountedRef.current) return
    if (session.userPaused) {
      invalidatePlayRequest()
      setConfirmedVideoIdentity(undefined)
      video.pause()
      return
    }
    requestPlay(video, activeAttemptRef.current, identity)
  }, [identity, invalidatePlayRequest, mountVideo, requestPlay, session.userPaused])

  const settlePoster = useCallback((
    expectedIdentity: string,
    status: CinematicPosterSettledEvent["status"],
  ): void => {
    if (
      identityRef.current !== expectedIdentity
      || !mountedRef.current
      || posterSettlementRef.current.identity !== expectedIdentity
      || posterSettlementRef.current.status !== undefined
    ) {
      return
    }
    const settlement = { identity: expectedIdentity, status }
    posterSettlementRef.current = settlement
    setPosterSettlement(settlement)
    onPosterSettledRef.current?.({ scene, viewport: policy.viewport, status })
  }, [policy.viewport, scene])

  const onPosterLoad = useCallback((): void => {
    settlePoster(identity, "loaded")
  }, [identity, settlePoster])

  const onPosterError = useCallback((): void => {
    settlePoster(identity, "failed")
  }, [identity, settlePoster])

  const onCanPlay = useCallback((event: SyntheticEvent<HTMLVideoElement>): void => {
    const video = event.currentTarget
    if (
      identityRef.current !== identity
      || videoRef.current !== video
      || !mountedRef.current
      || activeAttemptRef.current === 0
    ) return
    readyRef.current = true
    requestPlay(video, activeAttemptRef.current, identity)
  }, [identity, requestPlay])

  const onVideoError = useCallback((event: SyntheticEvent<HTMLVideoElement>): void => {
    if (
      identityRef.current !== identity
      || videoRef.current !== event.currentTarget
      || activeAttemptRef.current === 0
      || !mountedRef.current
      || !mountVideoRef.current
      || (sessionRef.current.playbackState !== "loading"
        && sessionRef.current.playbackState !== "playing")
    ) {
      return
    }
    invalidatePlayRequest()
    setConfirmedVideoIdentity(undefined)
    emitSessionEvent({ type: "play-failed" })
  }, [emitSessionEvent, identity, invalidatePlayRequest])

  const videoVisible = mountVideo
    && confirmedVideoIdentity === identity
    && !session.userPaused
  const posterFailed = posterSettlement.identity === identity
    && posterSettlementRef.current.identity === identity
    && posterSettlementRef.current.status === "failed"
  const objectPosition = `${rendition.objectPosition.x * 100}% ${rendition.objectPosition.y * 100}%`

  return (
    <div
      className="cinematic-scene-media"
      data-testid={`cinematic-scene-media-${scene}`}
      data-scene={scene}
      data-viewport={policy.viewport}
      data-playback-state={session.playbackState}
      data-user-paused={session.userPaused ? "true" : "false"}
      data-video-visible={videoVisible ? "true" : "false"}
      data-poster-failed={posterFailed ? "true" : "false"}
      style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden" }}
    >
      <picture
        key={`poster:${identity}`}
        className="cinematic-scene-media__poster"
        aria-hidden="true"
        style={{ position: "absolute", inset: 0, display: "block" }}
      >
        <source srcSet={rendition.posterAvif} type="image/avif" />
        <img
          className="cinematic-scene-media__poster-image"
          src={rendition.posterWebp}
          alt=""
          draggable={false}
          style={{ display: "block", width: "100%", height: "100%", objectFit: "cover", objectPosition }}
          onLoad={onPosterLoad}
          onError={onPosterError}
        />
      </picture>
      {mountVideo ? (
        <video
          key={`video:${identity}`}
          ref={videoRef}
          className="cinematic-scene-media__video"
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          aria-hidden="true"
          controls={false}
          disablePictureInPicture
          disableRemotePlayback
          style={{
            position: "absolute",
            inset: 0,
            display: "block",
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition,
            opacity: videoVisible ? 1 : 0,
            transition: "opacity 180ms ease-out",
            pointerEvents: "none",
          }}
          onCanPlay={onCanPlay}
          onError={onVideoError}
        >
          <source src={rendition.vp9Webm} type="video/webm" />
          <source src={rendition.h264Mp4} type="video/mp4" />
        </video>
      ) : null}
    </div>
  )
}

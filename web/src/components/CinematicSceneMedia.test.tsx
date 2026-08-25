import { StrictMode, useCallback, useState } from "react"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  decodeCinematicMediaManifest,
  type CinematicMediaManifest,
  type CinematicScene,
  type CinematicViewport,
} from "../cinematic/mediaManifest"
import type { CinematicMediaPolicy } from "../cinematic/mediaPolicy"
import {
  createCinematicMediaSessions,
  reduceCinematicMediaSessions,
  type CinematicMediaSessionEvent,
  type CinematicMediaSessions,
} from "../cinematic/mediaSession"
import { CinematicSceneMedia } from "./CinematicSceneMedia"

function localAsset(
  scene: CinematicScene,
  viewport: CinematicViewport,
  kind: "poster" | "loop",
  extension: "avif" | "webp" | "webm" | "mp4",
): string {
  return `/__cinematic-test-fixtures__/${scene}-${viewport}-${kind}.${extension}`
}

function fixtureManifest(): CinematicMediaManifest {
  const rendition = (scene: CinematicScene, viewport: CinematicViewport) => ({
    intrinsicWidth: viewport === "desktop" ? 1672 : 900,
    intrinsicHeight: viewport === "desktop" ? 941 : 1600,
    posterAvif: localAsset(scene, viewport, "poster", "avif"),
    posterWebp: localAsset(scene, viewport, "poster", "webp"),
    vp9Webm: localAsset(scene, viewport, "loop", "webm"),
    h264Mp4: localAsset(scene, viewport, "loop", "mp4"),
    focalPoint: { x: 0.5, y: 0.45 },
    objectPosition: { x: 0.5, y: 0.5 },
    ...(scene === "portal"
      ? { hitBox: { x: 0.45, y: 0.3, width: 0.1, height: 0.28 } }
      : {}),
  })
  return decodeCinematicMediaManifest({
    schemaVersion: "1.0",
    renditions: [
      { scene: "portal", viewport: "desktop", rendition: rendition("portal", "desktop") },
      { scene: "portal", viewport: "mobile", rendition: rendition("portal", "mobile") },
      { scene: "account", viewport: "desktop", rendition: rendition("account", "desktop") },
      { scene: "account", viewport: "mobile", rendition: rendition("account", "mobile") },
    ],
  })
}

const MANIFEST = fixtureManifest()
const DESKTOP_MOTION = { mode: "motion", viewport: "desktop" } as const
const MOBILE_MOTION = { mode: "motion", viewport: "mobile" } as const
const MOBILE_REDUCED = {
  mode: "poster",
  viewport: "mobile",
  reason: "reduced-motion",
} as const

interface ControlledSceneProps {
  readonly scene?: CinematicScene
  readonly policy: CinematicMediaPolicy
  readonly initialSessions?: CinematicMediaSessions
  readonly onEvent?: (event: CinematicMediaSessionEvent) => void
  readonly onPosterSettled?: (event: {
    readonly scene: CinematicScene
    readonly viewport: CinematicViewport
    readonly status: "loaded" | "failed"
  }) => void
}

function ControlledScene({
  scene = "portal",
  policy,
  initialSessions,
  onEvent,
  onPosterSettled,
}: ControlledSceneProps) {
  const [sessions, setSessions] = useState(
    () => initialSessions ?? createCinematicMediaSessions(),
  )
  const handleEvent = useCallback((event: CinematicMediaSessionEvent) => {
    onEvent?.(event)
    setSessions((current) => reduceCinematicMediaSessions(current, { scene, event }))
  }, [onEvent, scene])
  const session = sessions[scene]

  return (
    <>
      <CinematicSceneMedia
        scene={scene}
        manifest={MANIFEST}
        policy={policy}
        session={session}
        onSessionEvent={handleEvent}
        {...(onPosterSettled === undefined ? {} : { onPosterSettled })}
      />
      <output data-testid="session-state">{JSON.stringify(session)}</output>
      <button
        type="button"
        onClick={() => handleEvent({
          type: "user-paused-changed",
          paused: !session.userPaused,
        })}
      >toggle pause</button>
    </>
  )
}

interface Deferred<T> {
  readonly promise: Promise<T>
  readonly resolve: (value: T) => void
  readonly reject: (reason?: unknown) => void
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((onResolve, onReject) => {
    resolve = onResolve
    reject = onReject
  })
  return { promise, resolve, reject }
}

const originalPlay = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, "play")
const originalPause = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, "pause")
const originalHidden = Object.getOwnPropertyDescriptor(document, "hidden")
let playMock = vi.fn<() => Promise<void>>()
let pauseMock = vi.fn<() => void>()

function restoreProperty(
  target: object,
  key: PropertyKey,
  descriptor: PropertyDescriptor | undefined,
): void {
  if (descriptor === undefined) Reflect.deleteProperty(target, key)
  else Object.defineProperty(target, key, descriptor)
}

function setDocumentHidden(hidden: boolean): void {
  Object.defineProperty(document, "hidden", { configurable: true, value: hidden })
}

function currentVideo(): HTMLVideoElement {
  const video = document.querySelector("video")
  if (!(video instanceof HTMLVideoElement)) throw new Error("expected a cinematic video")
  return video
}

function currentPoster(): HTMLImageElement {
  const poster = document.querySelector(".cinematic-scene-media__poster-image")
  if (!(poster instanceof HTMLImageElement)) throw new Error("expected a cinematic poster")
  return poster
}

function setReady(video: HTMLVideoElement): void {
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 })
}

beforeEach(() => {
  playMock = vi.fn<() => Promise<void>>().mockResolvedValue(undefined)
  pauseMock = vi.fn<() => void>()
  Object.defineProperty(HTMLMediaElement.prototype, "play", {
    configurable: true,
    value: playMock,
  })
  Object.defineProperty(HTMLMediaElement.prototype, "pause", {
    configurable: true,
    value: pauseMock,
  })
  setDocumentHidden(false)
})

afterEach(() => {
  cleanup()
  restoreProperty(HTMLMediaElement.prototype, "play", originalPlay)
  restoreProperty(HTMLMediaElement.prototype, "pause", originalPause)
  restoreProperty(document, "hidden", originalHidden)
})

describe("CinematicSceneMedia DOM contract", () => {
  it("always renders the selected poster and omits video/source for a poster policy", () => {
    render(<ControlledScene policy={MOBILE_REDUCED} />)

    const root = screen.getByTestId("cinematic-scene-media-portal")
    const poster = currentPoster()
    expect(root).toHaveAttribute("data-viewport", "mobile")
    expect(poster).toHaveAttribute("src", localAsset("portal", "mobile", "poster", "webp"))
    expect(document.querySelector("video")).toBeNull()
    expect(document.querySelector("video source")).toBeNull()
    expect(root.innerHTML).not.toContain("account-")
  })

  it("renders WebM before MP4 with the bounded autoplay media attributes", async () => {
    render(<ControlledScene policy={DESKTOP_MOTION} />)

    const video = currentVideo()
    const sources = [...video.querySelectorAll("source")]
    expect(sources.map((source) => source.getAttribute("src"))).toEqual([
      localAsset("portal", "desktop", "loop", "webm"),
      localAsset("portal", "desktop", "loop", "mp4"),
    ])
    expect(sources.map((source) => source.getAttribute("type"))).toEqual([
      "video/webm",
      "video/mp4",
    ])
    expect(video.autoplay).toBe(true)
    expect(video.muted).toBe(true)
    expect(video.loop).toBe(true)
    expect(video.playsInline).toBe(true)
    expect(video.preload).toBe("metadata")
    expect(video.controls).toBe(false)
    expect(video).toHaveAttribute("disablepictureinpicture")
    expect(video).toHaveAttribute("disableremoteplayback")
    expect(video).toHaveAttribute("aria-hidden", "true")
    expect(video).toHaveStyle({ opacity: "0" })
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("loading"))
  })

  it("keeps the poster visible until the current canplay request actually resolves", async () => {
    const pending = deferred<void>()
    playMock.mockReturnValueOnce(pending.promise)
    render(<ControlledScene policy={DESKTOP_MOTION} />)
    const root = screen.getByTestId("cinematic-scene-media-portal")
    const video = currentVideo()

    fireEvent.canPlay(video)
    expect(playMock).toHaveBeenCalledTimes(1)
    expect(root).toHaveAttribute("data-video-visible", "false")

    await act(async () => pending.resolve(undefined))
    await waitFor(() => {
      expect(screen.getByTestId("session-state")).toHaveTextContent("playing")
      expect(root).toHaveAttribute("data-video-visible", "true")
      expect(video).toHaveStyle({ opacity: "1" })
    })
  })

  it("never starts two concurrent play requests for repeated canplay events", async () => {
    const pending = deferred<void>()
    playMock.mockReturnValueOnce(pending.promise)
    render(<ControlledScene policy={DESKTOP_MOTION} />)
    const video = currentVideo()

    fireEvent.canPlay(video)
    fireEvent.canPlay(video)
    fireEvent.canPlay(video)
    expect(playMock).toHaveBeenCalledTimes(1)

    await act(async () => pending.resolve(undefined))
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("playing"))
  })

  it("turns a current play rejection into a sticky poster with no video node", async () => {
    playMock.mockRejectedValueOnce(new DOMException("autoplay blocked", "NotAllowedError"))
    render(<ControlledScene policy={DESKTOP_MOTION} />)

    fireEvent.canPlay(currentVideo())
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("failed-sticky"))
    expect(document.querySelector("video")).toBeNull()
    expect(currentPoster()).toBeInTheDocument()
  })

  it("turns a current media error into the same sticky terminal", async () => {
    render(<ControlledScene policy={DESKTOP_MOTION} />)

    fireEvent.error(currentVideo())
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("failed-sticky"))
    expect(document.querySelector("video")).toBeNull()
  })

  it("handles a synchronous play throw as a current sticky failure", async () => {
    playMock.mockImplementationOnce(() => {
      throw new Error("play threw synchronously")
    })
    render(<ControlledScene policy={DESKTOP_MOTION} />)

    fireEvent.canPlay(currentVideo())
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("failed-sticky"))
    expect(document.querySelector("video")).toBeNull()
  })
})

describe("CinematicSceneMedia race and lifecycle isolation", () => {
  it("ignores an old play rejection after policy changes to poster", async () => {
    const oldPlay = deferred<void>()
    playMock.mockReturnValueOnce(oldPlay.promise)
    const view = render(<ControlledScene policy={DESKTOP_MOTION} />)
    fireEvent.canPlay(currentVideo())

    view.rerender(<ControlledScene policy={MOBILE_REDUCED} />)
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent('"poster"'))
    expect(document.querySelector("video")).toBeNull()

    await act(async () => oldPlay.reject(new DOMException("aborted", "AbortError")))
    expect(screen.getByTestId("session-state")).not.toHaveTextContent("failed-sticky")
  })

  it("replaces the media attempt on viewport change and ignores the old promise", async () => {
    const oldPlay = deferred<void>()
    playMock
      .mockReturnValueOnce(oldPlay.promise)
      .mockResolvedValueOnce(undefined)
    const view = render(<ControlledScene policy={DESKTOP_MOTION} />)
    const desktopVideo = currentVideo()
    fireEvent.canPlay(desktopVideo)

    view.rerender(<ControlledScene policy={MOBILE_MOTION} />)
    const mobileVideo = currentVideo()
    expect(mobileVideo).not.toBe(desktopVideo)
    expect(mobileVideo.querySelector("source")).toHaveAttribute(
      "src",
      localAsset("portal", "mobile", "loop", "webm"),
    )

    await act(async () => oldPlay.reject(new Error("stale desktop failure")))
    expect(screen.getByTestId("session-state")).not.toHaveTextContent("failed-sticky")

    fireEvent.canPlay(mobileVideo)
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("playing"))
  })

  it("ignores a late success after a current failure has already become sticky", async () => {
    const pending = deferred<void>()
    playMock.mockReturnValueOnce(pending.promise)
    render(<ControlledScene policy={DESKTOP_MOTION} />)
    const video = currentVideo()
    fireEvent.canPlay(video)
    fireEvent.error(video)

    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("failed-sticky"))
    await act(async () => pending.resolve(undefined))
    expect(screen.getByTestId("session-state")).toHaveTextContent("failed-sticky")
    expect(document.querySelector("video")).toBeNull()
  })

  it("pauses while hidden and resumes only when visible and eligible", async () => {
    render(<ControlledScene policy={DESKTOP_MOTION} />)
    const root = screen.getByTestId("cinematic-scene-media-portal")
    const video = currentVideo()
    setReady(video)
    fireEvent.canPlay(video)
    await waitFor(() => expect(root).toHaveAttribute("data-video-visible", "true"))

    setDocumentHidden(true)
    fireEvent(document, new Event("visibilitychange"))
    expect(pauseMock).toHaveBeenCalled()
    expect(root).toHaveAttribute("data-video-visible", "false")
    expect(screen.getByTestId("session-state")).toHaveTextContent("playing")

    setDocumentHidden(false)
    fireEvent(document, new Event("visibilitychange"))
    await waitFor(() => expect(playMock).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(root).toHaveAttribute("data-video-visible", "true"))
  })

  it("makes a current visible-resume rejection sticky", async () => {
    playMock
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error("resume decode failed"))
    render(<ControlledScene policy={DESKTOP_MOTION} />)
    const video = currentVideo()
    setReady(video)
    fireEvent.canPlay(video)
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("playing"))

    setDocumentHidden(true)
    fireEvent(document, new Event("visibilitychange"))
    setDocumentHidden(false)
    fireEvent(document, new Event("visibilitychange"))

    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("failed-sticky"))
    expect(document.querySelector("video")).toBeNull()
  })

  it("keeps pause orthogonal and conditionally resumes the same attempt", async () => {
    render(<ControlledScene policy={DESKTOP_MOTION} />)
    const video = currentVideo()
    setReady(video)
    fireEvent.canPlay(video)
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("playing"))

    fireEvent.click(screen.getByRole("button", { name: "toggle pause" }))
    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent('"userPaused":true'))
    expect(screen.getByTestId("session-state")).toHaveTextContent("playing")
    expect(pauseMock).toHaveBeenCalled()

    fireEvent.click(screen.getByRole("button", { name: "toggle pause" }))
    await waitFor(() => expect(playMock).toHaveBeenCalledTimes(2))
    expect(screen.getByTestId("session-state")).toHaveTextContent('"userPaused":false')
  })

  it("invalidates a pending play request before user pause can abort it", async () => {
    const pending = deferred<void>()
    playMock.mockReturnValueOnce(pending.promise)
    render(<ControlledScene policy={DESKTOP_MOTION} />)
    fireEvent.canPlay(currentVideo())

    fireEvent.click(screen.getByRole("button", { name: "toggle pause" }))
    await act(async () => pending.reject(new DOMException("pause aborted play", "AbortError")))

    expect(screen.getByTestId("session-state")).toHaveTextContent('"userPaused":true')
    expect(screen.getByTestId("session-state")).not.toHaveTextContent("failed-sticky")
  })

  it("ignores a pending play rejection after unmount and removes visibility listeners", async () => {
    const pending = deferred<void>()
    const onEvent = vi.fn()
    const addListener = vi.spyOn(document, "addEventListener")
    const removeListener = vi.spyOn(document, "removeEventListener")
    playMock.mockReturnValueOnce(pending.promise)
    const view = render(
      <CinematicSceneMedia
        scene="portal"
        manifest={MANIFEST}
        policy={DESKTOP_MOTION}
        session={{ playbackState: "loading", userPaused: false }}
        onSessionEvent={onEvent}
      />,
    )
    fireEvent.canPlay(currentVideo())
    const visibilityAdds = addListener.mock.calls.filter(([type]) => type === "visibilitychange")

    view.unmount()
    await act(async () => pending.reject(new Error("late after unmount")))

    expect(onEvent).not.toHaveBeenCalledWith({ type: "play-failed" })
    expect(removeListener).toHaveBeenCalledWith("visibilitychange", visibilityAdds[0]?.[1])
  })

  it("ignores a detached canplay after unmount", () => {
    const onEvent = vi.fn()
    const view = render(
      <CinematicSceneMedia
        scene="portal"
        manifest={MANIFEST}
        policy={DESKTOP_MOTION}
        session={{ playbackState: "loading", userPaused: false }}
        onSessionEvent={onEvent}
      />,
    )
    const video = currentVideo()
    view.unmount()
    fireEvent.canPlay(video)

    expect(playMock).not.toHaveBeenCalled()
    expect(onEvent).not.toHaveBeenCalledWith({ type: "play-confirmed" })
  })

  it("survives StrictMode setup-cleanup-setup without manufacturing failure", async () => {
    const onEvent = vi.fn()
    const addListener = vi.spyOn(document, "addEventListener")
    const removeListener = vi.spyOn(document, "removeEventListener")
    const view = render(
      <StrictMode>
        <ControlledScene policy={DESKTOP_MOTION} onEvent={onEvent} />
      </StrictMode>,
    )

    expect(document.querySelectorAll("video")).toHaveLength(1)
    expect(onEvent).not.toHaveBeenCalledWith({ type: "play-failed" })
    const visibilityAdds = addListener.mock.calls.filter(([type]) => type === "visibilitychange").length
    const visibilityRemovesBeforeUnmount = removeListener.mock.calls
      .filter(([type]) => type === "visibilitychange").length
    expect(visibilityAdds - visibilityRemovesBeforeUnmount).toBe(1)

    view.unmount()
    const visibilityRemovesAfterUnmount = removeListener.mock.calls
      .filter(([type]) => type === "visibilitychange").length
    expect(visibilityAdds - visibilityRemovesAfterUnmount).toBe(0)
  })
})

describe("poster failure and page-session persistence", () => {
  it("reports poster failure without poisoning video playback state", async () => {
    const onPosterSettled = vi.fn()
    render(<ControlledScene policy={MOBILE_REDUCED} onPosterSettled={onPosterSettled} />)
    const root = screen.getByTestId("cinematic-scene-media-portal")

    fireEvent.error(currentPoster())

    expect(root).toHaveAttribute("data-poster-failed", "true")
    expect(onPosterSettled).toHaveBeenCalledWith({
      scene: "portal",
      viewport: "mobile",
      status: "failed",
    })
    expect(screen.getByTestId("session-state")).toHaveTextContent('"playbackState":"poster"')
    expect(document.querySelector("video")).toBeNull()
  })

  it("ignores a detached poster error after unmount", () => {
    const onPosterSettled = vi.fn()
    const view = render(
      <ControlledScene policy={MOBILE_REDUCED} onPosterSettled={onPosterSettled} />,
    )
    const poster = currentPoster()
    view.unmount()
    fireEvent.error(poster)

    expect(onPosterSettled).not.toHaveBeenCalled()
  })

  it("reports poster load once and ignores an old rendition event", () => {
    const onPosterSettled = vi.fn()
    const view = render(
      <ControlledScene policy={{ mode: "poster", viewport: "desktop", reason: "preflight" }} onPosterSettled={onPosterSettled} />,
    )
    const desktopPoster = currentPoster()
    fireEvent.load(desktopPoster)
    fireEvent.load(desktopPoster)
    expect(onPosterSettled).toHaveBeenCalledTimes(1)

    view.rerender(<ControlledScene policy={MOBILE_REDUCED} onPosterSettled={onPosterSettled} />)
    fireEvent.error(desktopPoster)
    expect(screen.getByTestId("cinematic-scene-media-portal")).toHaveAttribute(
      "data-poster-failed",
      "false",
    )
    expect(onPosterSettled).toHaveBeenCalledTimes(1)
  })

  it("clears a stale poster failure when returning to a prior rendition identity", () => {
    const view = render(
      <ControlledScene policy={{ mode: "poster", viewport: "desktop", reason: "preflight" }} />,
    )
    fireEvent.error(currentPoster())
    expect(screen.getByTestId("cinematic-scene-media-portal")).toHaveAttribute(
      "data-poster-failed",
      "true",
    )

    view.rerender(<ControlledScene policy={MOBILE_REDUCED} />)
    view.rerender(<ControlledScene policy={{ mode: "poster", viewport: "desktop", reason: "preflight" }} />)

    expect(screen.getByTestId("cinematic-scene-media-portal")).toHaveAttribute(
      "data-poster-failed",
      "false",
    )
  })

  it("keeps failed and paused state across remounts but resets in a fresh page harness", () => {
    const persisted: CinematicMediaSessions = {
      portal: { playbackState: "failed-sticky", userPaused: true },
      account: { playbackState: "poster", userPaused: false },
    }
    const first = render(
      <ControlledScene policy={DESKTOP_MOTION} initialSessions={persisted} />,
    )
    expect(document.querySelector("video")).toBeNull()
    expect(screen.getByTestId("session-state")).toHaveTextContent("failed-sticky")
    expect(screen.getByTestId("session-state")).toHaveTextContent('"userPaused":true')

    first.unmount()
    const remount = render(
      <ControlledScene policy={DESKTOP_MOTION} initialSessions={persisted} />,
    )
    expect(document.querySelector("video")).toBeNull()
    remount.unmount()

    render(<ControlledScene policy={DESKTOP_MOTION} />)
    expect(currentVideo()).toBeInTheDocument()
  })
})

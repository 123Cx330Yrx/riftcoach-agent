import { StrictMode, useLayoutEffect } from "react"
import { renderToString } from "react-dom/server"
import { act, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import {
  CINEMATIC_MOBILE_MEDIA_QUERY,
  CINEMATIC_REDUCED_MOTION_MEDIA_QUERY,
  type CinematicMediaPolicy,
} from "./mediaPolicy"
import { useCinematicMediaPolicy } from "./useCinematicMediaPolicy"

type ChangeListener = EventListenerOrEventListenerObject

function notify(listener: ChangeListener, event: Event): void {
  if (typeof listener === "function") listener(event)
  else listener.handleEvent(event)
}

class FakeMediaQueryList {
  matches: boolean
  readonly media: string
  readonly listeners = new Set<ChangeListener>()
  readonly addEventListener = vi.fn((type: string, listener: ChangeListener) => {
    if (type === "change") this.listeners.add(listener)
  })
  readonly removeEventListener = vi.fn((type: string, listener: ChangeListener) => {
    if (type === "change") this.listeners.delete(listener)
  })

  constructor(media: string, matches: boolean) {
    this.media = media
    this.matches = matches
  }

  setMatches(matches: boolean): void {
    this.matches = matches
    const event = new Event("change")
    for (const listener of [...this.listeners]) notify(listener, event)
  }

  asMediaQueryList(): MediaQueryList {
    return this as unknown as MediaQueryList
  }
}

class FakeLegacyMediaQueryList {
  matches: boolean
  readonly media: string
  readonly listeners = new Set<ChangeListener>()
  readonly addListener = vi.fn((listener: ChangeListener) => {
    this.listeners.add(listener)
  })
  readonly removeListener = vi.fn((listener: ChangeListener) => {
    this.listeners.delete(listener)
  })

  constructor(media: string, matches: boolean) {
    this.media = media
    this.matches = matches
  }

  setMatches(matches: boolean): void {
    this.matches = matches
    const event = new Event("change")
    for (const listener of [...this.listeners]) notify(listener, event)
  }

  asMediaQueryList(): MediaQueryList {
    return this as unknown as MediaQueryList
  }
}

class FakeNetworkConnection {
  saveData: boolean
  readonly listeners = new Set<ChangeListener>()
  readonly addEventListener = vi.fn((type: string, listener: ChangeListener) => {
    if (type === "change") this.listeners.add(listener)
  })
  readonly removeEventListener = vi.fn((type: string, listener: ChangeListener) => {
    if (type === "change") this.listeners.delete(listener)
  })

  constructor(saveData: boolean) {
    this.saveData = saveData
  }

  setSaveData(saveData: boolean): void {
    this.saveData = saveData
    const event = new Event("change")
    for (const listener of [...this.listeners]) notify(listener, event)
  }
}

const originalMatchMediaDescriptor = Object.getOwnPropertyDescriptor(window, "matchMedia")
const originalInnerWidthDescriptor = Object.getOwnPropertyDescriptor(window, "innerWidth")
const originalConnectionDescriptor = Object.getOwnPropertyDescriptor(navigator, "connection")

afterEach(() => {
  restoreProperty(window, "matchMedia", originalMatchMediaDescriptor)
  restoreProperty(window, "innerWidth", originalInnerWidthDescriptor)
  restoreProperty(navigator, "connection", originalConnectionDescriptor)
})

function restoreProperty(
  target: object,
  key: PropertyKey,
  descriptor: PropertyDescriptor | undefined,
): void {
  if (descriptor === undefined) Reflect.deleteProperty(target, key)
  else Object.defineProperty(target, key, descriptor)
}

interface FakeEnvironment {
  readonly reducedMotion: FakeMediaQueryList
  readonly mobileViewport: FakeMediaQueryList
  readonly connection?: FakeNetworkConnection
}

interface FakeLegacyEnvironment {
  readonly reducedMotion: FakeLegacyMediaQueryList
  readonly mobileViewport: FakeLegacyMediaQueryList
}

function installEnvironment(options: {
  readonly reducedMotion?: boolean
  readonly mobileViewport?: boolean
  readonly saveData?: boolean
  readonly withConnection?: boolean
} = {}): FakeEnvironment {
  const reducedMotion = new FakeMediaQueryList(
    CINEMATIC_REDUCED_MOTION_MEDIA_QUERY,
    options.reducedMotion ?? false,
  )
  const mobileViewport = new FakeMediaQueryList(
    CINEMATIC_MOBILE_MEDIA_QUERY,
    options.mobileViewport ?? false,
  )
  const queries = new Map([
    [CINEMATIC_REDUCED_MOTION_MEDIA_QUERY, reducedMotion],
    [CINEMATIC_MOBILE_MEDIA_QUERY, mobileViewport],
  ])
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => {
      const result = queries.get(query)
      if (result === undefined) throw new Error(`unexpected media query: ${query}`)
      return result.asMediaQueryList()
    }),
  })

  const withConnection = options.withConnection ?? options.saveData !== undefined
  if (!withConnection) {
    Reflect.deleteProperty(navigator, "connection")
    return { reducedMotion, mobileViewport }
  }

  const connection = new FakeNetworkConnection(options.saveData ?? false)
  Object.defineProperty(navigator, "connection", {
    configurable: true,
    value: connection,
  })
  return { reducedMotion, mobileViewport, connection }
}

function installLegacyEnvironment(): FakeLegacyEnvironment {
  const reducedMotion = new FakeLegacyMediaQueryList(
    CINEMATIC_REDUCED_MOTION_MEDIA_QUERY,
    false,
  )
  const mobileViewport = new FakeLegacyMediaQueryList(CINEMATIC_MOBILE_MEDIA_QUERY, false)
  const queries = new Map([
    [CINEMATIC_REDUCED_MOTION_MEDIA_QUERY, reducedMotion],
    [CINEMATIC_MOBILE_MEDIA_QUERY, mobileViewport],
  ])
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => {
      const result = queries.get(query)
      if (result === undefined) throw new Error(`unexpected media query: ${query}`)
      return result.asMediaQueryList()
    }),
  })
  Reflect.deleteProperty(navigator, "connection")
  return { reducedMotion, mobileViewport }
}

function Probe({
  onCommit,
  onRender,
}: {
  readonly onCommit?: (policy: CinematicMediaPolicy) => void
  readonly onRender?: (policy: CinematicMediaPolicy) => void
}) {
  const policy = useCinematicMediaPolicy()
  onRender?.(policy)
  useLayoutEffect(() => {
    onCommit?.(policy)
  }, [onCommit, policy])
  return <output data-testid="policy">{JSON.stringify(policy)}</output>
}

function FlipSignalDuringRender({ flip }: { readonly flip: () => void }) {
  flip()
  return null
}

function expectPolicy(policy: CinematicMediaPolicy): void {
  expect(screen.getByTestId("policy")).toHaveTextContent(JSON.stringify(policy))
}

describe("useCinematicMediaPolicy", () => {
  it("uses a conservative poster policy for server rendering", () => {
    installEnvironment()

    const markup = renderToString(<Probe />)

    expect(markup).toContain("poster")
    expect(markup).toContain("preflight")
    expect(markup).not.toContain("&quot;mode&quot;:&quot;motion&quot;")
  })

  it("treats a missing Network Information API as Save-Data off", () => {
    installEnvironment()

    render(<Probe />)

    expectPolicy({ mode: "motion", viewport: "desktop" })
  })

  it("returns the mobile reduced-motion poster policy on the first render", () => {
    installEnvironment({
      reducedMotion: true,
      mobileViewport: true,
      withConnection: true,
    })

    render(<Probe />)

    expectPolicy({ mode: "poster", viewport: "mobile", reason: "reduced-motion" })
  })

  it("returns the mobile Save-Data poster policy on the first render", () => {
    installEnvironment({
      mobileViewport: true,
      saveData: true,
    })

    render(<Probe />)

    expectPolicy({ mode: "poster", viewport: "mobile", reason: "save-data" })
  })

  it("reacts to viewport, Save-Data, and reduced-motion changes with stable priority", () => {
    const environment = installEnvironment({ withConnection: true })
    const connection = environment.connection
    if (connection === undefined) throw new Error("test connection was not installed")
    render(<Probe />)

    act(() => environment.mobileViewport.setMatches(true))
    expectPolicy({ mode: "motion", viewport: "mobile" })

    act(() => connection.setSaveData(true))
    expectPolicy({ mode: "poster", viewport: "mobile", reason: "save-data" })

    act(() => environment.reducedMotion.setMatches(true))
    expectPolicy({ mode: "poster", viewport: "mobile", reason: "reduced-motion" })

    act(() => environment.reducedMotion.setMatches(false))
    expectPolicy({ mode: "poster", viewport: "mobile", reason: "save-data" })

    act(() => connection.setSaveData(false))
    expectPolicy({ mode: "motion", viewport: "mobile" })
  })

  it("does not commit stale motion when reduced motion changes before commit", () => {
    const environment = installEnvironment()
    const onCommit = vi.fn()

    render(
      <>
        <Probe onCommit={onCommit} />
        <FlipSignalDuringRender flip={() => {
          environment.reducedMotion.matches = true
        }} />
      </>,
    )

    expectPolicy({ mode: "poster", viewport: "desktop", reason: "reduced-motion" })
    expect(onCommit.mock.calls.map(([policy]) => policy)).toEqual([
      { mode: "poster", viewport: "desktop", reason: "preflight" },
      { mode: "poster", viewport: "desktop", reason: "reduced-motion" },
    ])
    expect(onCommit).not.toHaveBeenCalledWith({ mode: "motion", viewport: "desktop" })
  })

  it("supports legacy MediaQueryList listeners and cleans them up symmetrically", () => {
    const environment = installLegacyEnvironment()
    const view = render(<Probe />)

    act(() => environment.mobileViewport.setMatches(true))
    expectPolicy({ mode: "motion", viewport: "mobile" })
    act(() => environment.reducedMotion.setMatches(true))
    expectPolicy({ mode: "poster", viewport: "mobile", reason: "reduced-motion" })

    view.unmount()

    expect(environment.reducedMotion.removeListener).toHaveBeenCalledWith(
      environment.reducedMotion.addListener.mock.calls[0]?.[0],
    )
    expect(environment.mobileViewport.removeListener).toHaveBeenCalledWith(
      environment.mobileViewport.addListener.mock.calls[0]?.[0],
    )
    expect(environment.reducedMotion.listeners).toHaveLength(0)
    expect(environment.mobileViewport.listeners).toHaveLength(0)
  })

  it("leaves one live subscription in StrictMode and none after unmount", () => {
    const environment = installEnvironment({ withConnection: true })
    const connection = environment.connection
    if (connection === undefined) throw new Error("test connection was not installed")
    const view = render(<StrictMode><Probe /></StrictMode>)

    expect(environment.reducedMotion.listeners).toHaveLength(1)
    expect(environment.mobileViewport.listeners).toHaveLength(1)
    expect(connection.listeners).toHaveLength(1)

    view.unmount()

    expect(environment.reducedMotion.listeners).toHaveLength(0)
    expect(environment.mobileViewport.listeners).toHaveLength(0)
    expect(connection.listeners).toHaveLength(0)
  })

  it("uses resize as a viewport fallback when matchMedia is unavailable", () => {
    Object.defineProperty(window, "matchMedia", { configurable: true, value: undefined })
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 760, writable: true })
    Reflect.deleteProperty(navigator, "connection")
    render(<Probe />)

    expectPolicy({ mode: "motion", viewport: "mobile" })

    act(() => {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        value: 761,
        writable: true,
      })
      window.dispatchEvent(new Event("resize"))
    })
    expectPolicy({ mode: "motion", viewport: "desktop" })
  })

  it("cleans up every subscribed listener and skips unchanged rerenders", () => {
    const environment = installEnvironment({ withConnection: true })
    const connection = environment.connection
    if (connection === undefined) throw new Error("test connection was not installed")
    const addWindowListener = vi.spyOn(window, "addEventListener")
    const removeWindowListener = vi.spyOn(window, "removeEventListener")
    const onRender = vi.fn()
    const view = render(<Probe onRender={onRender} />)

    const resizeSubscription = addWindowListener.mock.calls.find(([type]) => type === "resize")
    expect(resizeSubscription).toBeDefined()
    expect(environment.reducedMotion.addEventListener).toHaveBeenCalledTimes(1)
    expect(environment.mobileViewport.addEventListener).toHaveBeenCalledTimes(1)
    expect(connection.addEventListener).toHaveBeenCalledTimes(1)

    const renderCount = onRender.mock.calls.length
    act(() => window.dispatchEvent(new Event("resize")))
    act(() => environment.reducedMotion.setMatches(false))
    act(() => connection.setSaveData(false))
    expect(onRender).toHaveBeenCalledTimes(renderCount)

    view.unmount()

    expect(environment.reducedMotion.removeEventListener).toHaveBeenCalledWith(
      "change",
      environment.reducedMotion.addEventListener.mock.calls[0]?.[1],
    )
    expect(environment.mobileViewport.removeEventListener).toHaveBeenCalledWith(
      "change",
      environment.mobileViewport.addEventListener.mock.calls[0]?.[1],
    )
    expect(connection.removeEventListener).toHaveBeenCalledWith(
      "change",
      connection.addEventListener.mock.calls[0]?.[1],
    )
    expect(removeWindowListener).toHaveBeenCalledWith("resize", resizeSubscription?.[1])
  })
})

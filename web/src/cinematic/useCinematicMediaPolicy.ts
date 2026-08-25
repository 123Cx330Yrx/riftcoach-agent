import { useRef, useSyncExternalStore } from "react"

import {
  CINEMATIC_MOBILE_MAX_WIDTH_PX,
  CINEMATIC_MOBILE_MEDIA_QUERY,
  CINEMATIC_REDUCED_MOTION_MEDIA_QUERY,
  type CinematicMediaPolicy,
  resolveCinematicMediaPolicy,
  resolveCinematicViewport,
} from "./mediaPolicy"

interface CinematicNetworkInformation {
  readonly saveData?: boolean
  readonly addEventListener?: (type: "change", listener: EventListener) => void
  readonly removeEventListener?: (type: "change", listener: EventListener) => void
}

interface CinematicMediaQueryList {
  readonly matches: boolean
  readonly addEventListener?: (type: "change", listener: EventListener) => void
  readonly removeEventListener?: (type: "change", listener: EventListener) => void
  readonly addListener?: (listener: EventListener) => void
  readonly removeListener?: (listener: EventListener) => void
}

interface NavigatorWithConnection extends Navigator {
  readonly connection?: CinematicNetworkInformation
}

interface CinematicMediaRuntime {
  readonly browserWindow: Window | undefined
  readonly reducedMotionQuery: CinematicMediaQueryList | undefined
  readonly mobileViewportQuery: CinematicMediaQueryList | undefined
  readonly connection: CinematicNetworkInformation | undefined
}

interface CinematicMediaPolicyStore {
  readonly getSnapshot: () => CinematicMediaPolicy
  readonly getServerSnapshot: () => CinematicMediaPolicy
  readonly subscribe: (listener: () => void) => () => void
}

const CINEMATIC_SERVER_POSTER_POLICY: CinematicMediaPolicy = Object.freeze({
  mode: "poster",
  viewport: "desktop",
  reason: "preflight",
})

function optionalMediaQuery(
  browserWindow: Window,
  query: string,
): CinematicMediaQueryList | undefined {
  if (typeof browserWindow.matchMedia !== "function") return undefined
  try {
    return browserWindow.matchMedia(query) as unknown as CinematicMediaQueryList
  } catch {
    return undefined
  }
}

function optionalConnection(): CinematicNetworkInformation | undefined {
  if (typeof navigator === "undefined") return undefined
  try {
    return (navigator as NavigatorWithConnection).connection
  } catch {
    return undefined
  }
}

function createRuntime(): CinematicMediaRuntime {
  if (typeof window === "undefined") {
    return {
      browserWindow: undefined,
      reducedMotionQuery: undefined,
      mobileViewportQuery: undefined,
      connection: undefined,
    }
  }
  return {
    browserWindow: window,
    reducedMotionQuery: optionalMediaQuery(window, CINEMATIC_REDUCED_MOTION_MEDIA_QUERY),
    mobileViewportQuery: optionalMediaQuery(window, CINEMATIC_MOBILE_MEDIA_QUERY),
    connection: optionalConnection(),
  }
}

function fallbackViewportWidth(browserWindow: Window | undefined): number {
  const width = browserWindow?.innerWidth
  return typeof width === "number" && Number.isFinite(width) && width >= 0
    ? width
    : CINEMATIC_MOBILE_MAX_WIDTH_PX + 1
}

function readViewport(runtime: CinematicMediaRuntime): CinematicMediaPolicy["viewport"] {
  return runtime.mobileViewportQuery === undefined
    ? resolveCinematicViewport(fallbackViewportWidth(runtime.browserWindow))
    : runtime.mobileViewportQuery.matches ? "mobile" : "desktop"
}

function readPolicy(runtime: CinematicMediaRuntime): CinematicMediaPolicy {
  return resolveCinematicMediaPolicy({
    reducedMotion: runtime.reducedMotionQuery?.matches === true,
    saveData: runtime.connection?.saveData === true,
    viewport: readViewport(runtime),
  })
}

function policiesEqual(left: CinematicMediaPolicy, right: CinematicMediaPolicy): boolean {
  if (left.mode !== right.mode || left.viewport !== right.viewport) return false
  return left.mode === "motion" || (right.mode === "poster" && left.reason === right.reason)
}

function subscribeToMediaQuery(
  query: CinematicMediaQueryList | undefined,
  listener: EventListener,
): (() => void) | undefined {
  if (query === undefined) return undefined
  if (
    typeof query.addEventListener === "function"
    && typeof query.removeEventListener === "function"
  ) {
    const addEventListener = query.addEventListener
    const removeEventListener = query.removeEventListener
    addEventListener.call(query, "change", listener)
    return () => removeEventListener.call(query, "change", listener)
  }
  if (typeof query.addListener === "function" && typeof query.removeListener === "function") {
    const addListener = query.addListener
    const removeListener = query.removeListener
    addListener.call(query, listener)
    return () => removeListener.call(query, listener)
  }
  return undefined
}

function subscribeToConnection(
  connection: CinematicNetworkInformation | undefined,
  listener: EventListener,
): (() => void) | undefined {
  if (
    connection === undefined
    || typeof connection.addEventListener !== "function"
    || typeof connection.removeEventListener !== "function"
  ) {
    return undefined
  }
  const removeEventListener = connection.removeEventListener
  connection.addEventListener("change", listener)
  return () => removeEventListener.call(connection, "change", listener)
}

function createMediaPolicyStore(): CinematicMediaPolicyStore {
  const runtime = createRuntime()
  let snapshot: CinematicMediaPolicy = {
    mode: "poster",
    viewport: readViewport(runtime),
    reason: "preflight",
  }

  const readLatestSnapshot = (): CinematicMediaPolicy => {
    const next = readPolicy(runtime)
    if (!policiesEqual(snapshot, next)) snapshot = next
    return snapshot
  }

  const getSnapshot = (): CinematicMediaPolicy => snapshot

  const subscribe = (listener: () => void): (() => void) => {
    const update = (): void => {
      const previous = snapshot
      const next = readLatestSnapshot()
      if (next !== previous) listener()
    }
    const cleanups = [
      subscribeToMediaQuery(runtime.reducedMotionQuery, update),
      subscribeToMediaQuery(runtime.mobileViewportQuery, update),
      subscribeToConnection(runtime.connection, update),
    ].filter((cleanup): cleanup is () => void => cleanup !== undefined)

    runtime.browserWindow?.addEventListener("resize", update)
    update()

    return () => {
      for (const cleanup of cleanups) cleanup()
      runtime.browserWindow?.removeEventListener("resize", update)
    }
  }

  return {
    getSnapshot,
    getServerSnapshot: () => CINEMATIC_SERVER_POSTER_POLICY,
    subscribe,
  }
}

export function useCinematicMediaPolicy(): CinematicMediaPolicy {
  const storeRef = useRef<CinematicMediaPolicyStore | undefined>(undefined)
  if (storeRef.current === undefined) storeRef.current = createMediaPolicyStore()
  const store = storeRef.current

  return useSyncExternalStore(store.subscribe, store.getSnapshot, store.getServerSnapshot)
}

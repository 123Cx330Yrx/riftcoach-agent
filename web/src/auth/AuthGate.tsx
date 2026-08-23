import { useCallback, useEffect, useState, type ReactNode } from "react"

import type { AuthSessionWire } from "../api/wire"
import { AuthSessionError, type AuthSessionClient } from "./session"

export type AuthGateState =
  | { readonly status: "checking" }
  | { readonly status: "authenticated"; readonly session: AuthSessionWire }
  | { readonly status: "unavailable"; readonly code: string }
  | { readonly status: "expired"; readonly code: string }

function failureStatus(code: string): "unavailable" | "expired" {
  return code === "auth_session_expired" || code === "auth_session_revoked" || code === "authentication_required"
    ? "expired"
    : "unavailable"
}

export function AuthGate({
  client,
  children,
  failureCode,
  onRetry,
}: {
  readonly client: AuthSessionClient
  readonly children: (session: AuthSessionWire) => ReactNode
  readonly failureCode?: string
  readonly onRetry?: () => void
}) {
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<AuthGateState>({ status: "checking" })
  const retry = useCallback(() => {
    onRetry?.()
    setAttempt((value) => value + 1)
  }, [onRetry])

  useEffect(() => {
    const controller = new AbortController()
    setState({ status: "checking" })
    if (failureCode !== undefined) {
      setState({ status: failureStatus(failureCode), code: failureCode })
      return () => controller.abort()
    }
    void client.issue(controller.signal).then(
      (session) => setState({ status: "authenticated", session }),
      (error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return
        const code = error instanceof AuthSessionError ? error.code : "auth_unavailable"
        setState({ status: failureStatus(code), code })
      },
    )
    return () => controller.abort()
  }, [attempt, client, failureCode])

  if (state.status === "authenticated") return <>{children(state.session)}</>
  if (state.status === "checking") {
    return <AuthBoundary state="checking" onRetry={retry} />
  }
  return <AuthBoundary state={state.status} code={state.code} onRetry={retry} />
}

function AuthBoundary({
  state,
  code,
  onRetry,
}: {
  readonly state: AuthGateState["status"]
  readonly code?: string
  readonly onRetry: () => void
}) {
  const checking = state === "checking"
  const expired = state === "expired"
  return (
    <section className={`auth-boundary auth-boundary--${state}`} aria-labelledby="auth-boundary-title" aria-live="polite">
      <div className="auth-boundary__signal" aria-hidden="true"><span /><span /><span /></div>
      <p className="eyebrow">RIFTCOACH / SECURE PRODUCT SHELL</p>
      <h1 id="auth-boundary-title">
        {checking ? "Checking your session" : expired ? "Your session needs attention" : "Sign-in is not ready"}
      </h1>
      <p>
        {checking
          ? "The workbench is waiting for an opaque server session before loading owner-scoped data."
          : expired
            ? "The previous session is no longer valid. Re-establish it before requesting a review."
            : "This deployment has not configured its authentication provider. No profile or Riot ID is loaded as a substitute."}
      </p>
      {code !== undefined ? <code>{code}</code> : null}
      <button type="button" onClick={onRetry} disabled={checking}>
        {checking ? "Checking session" : expired ? "Try session again" : "Retry secure session"}
      </button>
      <small>Riot ID identifies a subject for analysis; it is never an authentication credential.</small>
    </section>
  )
}

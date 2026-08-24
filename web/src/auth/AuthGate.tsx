import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"

import type { AuthSessionWire } from "../api/wire"
import { useI18n } from "../i18n/ProductLocaleProvider"
import { AuthSessionError, type AuthSessionClient } from "./session"
import { LocaleSwitch } from "../components/LocaleSwitch"

export type AuthGateState =
  | { readonly status: "checking" }
  | { readonly status: "authenticated"; readonly session: AuthSessionWire }
  | { readonly status: "unavailable"; readonly code: string }
  | { readonly status: "signed_out"; readonly code: string }
  | { readonly status: "expired"; readonly code: string }

function failureStatus(code: string): "unavailable" | "signed_out" | "expired" {
  if (code === "authentication_required") return "signed_out"
  return code === "auth_session_expired" || code === "auth_session_revoked" ? "expired" : "unavailable"
}

export function AuthGate({
  client,
  children,
  failureCode,
  onBack,
  onRetry,
}: {
  readonly client: AuthSessionClient
  readonly children: (session: AuthSessionWire) => ReactNode
  readonly failureCode?: string
  readonly onBack?: () => void
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
    return <AuthBoundary state="checking" {...(onBack === undefined ? {} : { onBack })} onRetry={retry} />
  }
  return <AuthBoundary state={state.status} {...(onBack === undefined ? {} : { onBack })} onRetry={retry} />
}

function AuthBoundary({
  state,
  onBack,
  onRetry,
}: {
  readonly state: AuthGateState["status"]
  readonly onBack?: () => void
  readonly onRetry: () => void
}) {
  const { t } = useI18n()
  const checking = state === "checking"
  const signedOut = state === "signed_out"
  const expired = state === "expired"
  const titleRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (!checking) titleRef.current?.focus()
  }, [checking, state])
  return (
    <section className={`auth-boundary auth-boundary--${state}`} aria-labelledby="auth-boundary-title" aria-live="polite">
      <div className="auth-boundary__topbar">
        {onBack === undefined ? <span /> : <button type="button" onClick={onBack}>{t("account.back")}</button>}
        <LocaleSwitch />
      </div>
      <div className="auth-boundary__signal" aria-hidden="true"><span /><span /><span /></div>
      <p className="eyebrow">{t("auth.kicker")}</p>
      <h1 id="auth-boundary-title" ref={titleRef} tabIndex={-1}>
        {checking
          ? t("auth.checking_title")
          : signedOut
            ? t("auth.signed_out_title")
            : expired
              ? t("auth.expired_title")
              : t("auth.unavailable_title")}
      </h1>
      <p>
        {checking
          ? t("auth.checking_body")
          : signedOut
            ? t("auth.signed_out_body")
            : expired
              ? t("auth.expired_body")
              : t("auth.unavailable_body")}
      </p>
      <button type="button" onClick={onRetry} disabled={checking}>
        {checking
          ? t("auth.checking_button")
          : signedOut
            ? t("auth.signed_out_button")
            : expired
              ? t("auth.expired_button")
              : t("auth.unavailable_button")}
      </button>
      <small>{t("auth.identity_boundary")}</small>
    </section>
  )
}

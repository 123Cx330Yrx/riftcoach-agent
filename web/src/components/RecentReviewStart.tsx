import { useEffect, useRef, useState } from "react"
import { ApiClientError } from "../api/client"
import { RecentReviewApi } from "../api/recentReviewApi"
import { useI18n } from "../i18n/ProductLocaleProvider"

export function RecentReviewStart({ profileId, role, previousTask, csrfToken, onChanged, onAuthFailure, api: suppliedApi }: {
  readonly profileId: string; readonly role: "self" | "public_observed"; readonly previousTask?: string | undefined
  readonly csrfToken: string; readonly onChanged: () => void; readonly onAuthFailure: (code: string) => void
  readonly api?: RecentReviewApi
}) {
  const { t } = useI18n()
  const [api] = useState(() => suppliedApi ?? new RecentReviewApi())
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState(false)
  const inFlight = useRef(false)
  const active = useRef<AbortController | undefined>(undefined)
  useEffect(() => {
    active.current = new AbortController()
    return () => active.current?.abort()
  }, [])

  async function start() {
    const signal = active.current?.signal
    if (!signal || signal.aborted || inFlight.current || done) return
    inFlight.current = true; setBusy(true); setError(false)
    try {
      // Store only a random operation identity. Refresh never sends a POST;
      // an explicit retry of an uncertain response reuses both server keys.
      const storageKey = `riftcoach.review-start.v1:${profileId}`
      const text = sessionStorage.getItem(storageKey)
      let pending: { operation?: unknown; previousTask?: unknown } = {}
      try { pending = text ? JSON.parse(text) ?? {} : {} } catch { /* replace invalid local state */ }
      const operation = pending.previousTask === (previousTask ?? null)
        && typeof pending.operation === "string" && /^review-[0-9a-f-]{36}$/.test(pending.operation)
        ? pending.operation : `review-${crypto.randomUUID()}`
      sessionStorage.setItem(storageKey, JSON.stringify({ operation, previousTask: previousTask ?? null }))
      await api.start(profileId, role, operation, csrfToken, signal)
      if (!signal.aborted) { setDone(true); onChanged() }
    } catch (failure) {
      if (signal.aborted) return
      if (failure instanceof ApiClientError && [401, 403].includes(failure.status)) onAuthFailure(failure.code)
      setError(true)
    } finally {
      inFlight.current = false
      if (!signal.aborted) setBusy(false)
    }
  }

  return <section className="source-summary panel review-start" aria-labelledby="review-start-title" aria-busy={busy}>
    <h3 id="review-start-title">{t("reviewStart.title")}</h3>
    <p>{t(role === "public_observed" ? "reviewStart.observed" : "reviewStart.self")}</p>
    <div className="task-recovery-actions"><button type="button" disabled={busy || done} onClick={() => void start()}>{t(busy ? "reviewStart.busy" : error ? "reviewStart.retry" : "reviewStart.start")}</button></div>
    {error && <p role="alert">{t("reviewStart.uncertain")}</p>}
    {done && <p role="status">{t("reviewStart.accepted")}</p>}
  </section>
}

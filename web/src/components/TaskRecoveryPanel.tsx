import { useEffect, useRef, useState } from "react"
import { ApiClientError } from "../api/client"
import { TaskContinuationApi, type TaskContinuation } from "../api/taskContinuationApi"
import { useI18n } from "../i18n/ProductLocaleProvider"
import { RunUsagePanel } from "./RunUsagePanel"

type Action = "resume" | "retry" | "cancel"
const MANUAL_REASONS = new Set(["session_timeout_awaiting_manual_retry", "session_format_awaiting_manual_retry"])

export function TaskRecoveryPanel({ taskId, runId, csrfToken, onChanged, onAuthFailure, api: suppliedApi }: {
  readonly taskId: string; readonly runId: string; readonly csrfToken: string
  readonly onChanged: () => void; readonly onAuthFailure: (code: string) => void
  readonly api?: TaskContinuationApi
}) {
  const { t } = useI18n()
  const [api] = useState(() => suppliedApi ?? new TaskContinuationApi())
  const [detail, setDetail] = useState<TaskContinuation>()
  const [error, setError] = useState<"load" | "uncertain" | "stale" | "legacy">()
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [refresh, setRefresh] = useState(0)
  const active = useRef<AbortController | undefined>(undefined)
  const inFlight = useRef(false)
  // Keep the operation identity across a lost HTTP response. No automatic POST.
  const operations = useRef(new Map<string, string>())
  const authFailure = useRef(onAuthFailure)
  authFailure.current = onAuthFailure
  useEffect(() => {
    const controller = new AbortController()
    active.current = controller
    setDetail(undefined); setError(undefined)
    void api.get(taskId, runId, controller.signal).then(value => {
      if (!controller.signal.aborted) setDetail(value)
    }).catch((failure: unknown) => {
      if (controller.signal.aborted) return
      if (failure instanceof ApiClientError && [401, 403].includes(failure.status)) authFailure.current(failure.code)
      setError(failure instanceof ApiClientError && failure.code === "continuation_not_found" ? "legacy" : "load")
    })
    return () => { controller.abort(); active.current = undefined }
  }, [api, taskId, runId, refresh])

  async function act(action: Action) {
    const signal = active.current?.signal
    if (!detail || !signal || signal.aborted || inFlight.current || done || error === "stale") return
    if (action === "retry" && !MANUAL_REASONS.has(detail.reason ?? "")) return
    inFlight.current = true; setBusy(true); setError(undefined)
    const identity = `${detail.checkpoint}:${action}`
    const key = operations.current.get(identity) ?? `recovery-${crypto.randomUUID()}`
    operations.current.set(identity, key)
    try {
      if (action === "cancel") await api.cancel(taskId, key, csrfToken, signal)
      else await api.resume(taskId, runId, detail.checkpoint, action === "retry", key, csrfToken, signal)
      if (!signal.aborted) { setDone(true); onChanged() }
    } catch (failure) {
      if (signal.aborted) return
      if (failure instanceof ApiClientError && [401, 403].includes(failure.status)) authFailure.current(failure.code)
      setError(failure instanceof ApiClientError && [404, 409].includes(failure.status) ? "stale" : "uncertain")
    } finally {
      inFlight.current = false
      if (!signal.aborted) setBusy(false)
    }
  }
  const manual = MANUAL_REASONS.has(detail?.reason ?? "")
  const unresolved = (detail?.accounting.unresolved_intents ?? 0) > 0
  return <>
    <section className="source-summary panel" aria-labelledby="task-recovery-title" aria-busy={busy}>
      <h3 id="task-recovery-title">{t("recovery.title")}</h3>
      <p>{t("recovery.preserved")}</p>
      {!detail && !error && <p role="status">{t("recovery.loading")}</p>}
      {detail && <>
        <p>{t(unresolved ? "recovery.unresolved" : manual ? "recovery.manual" : "recovery.repair")}</p>
        <div className="task-recovery-actions">
          {!unresolved && <button type="button" disabled={busy || done || error === "stale"} onClick={() => void act(manual ? "retry" : "resume")}>
            {t(manual ? "recovery.retry" : "recovery.resume")}
          </button>}
          <button type="button" disabled={busy || done || error === "stale"} onClick={() => void act("cancel")}>{t("recovery.cancel")}</button>
        </div>
      </>}
      {done && <p role="status">{t("recovery.accepted")}</p>}
      {error && <p role="alert">{t(`recovery.${error}`)}</p>}
      {(error === "load" || error === "stale") && <button type="button" onClick={() => { onChanged(); setRefresh(value => value + 1) }}>{t("recovery.refresh")}</button>}
    </section>
    {detail && <RunUsagePanel usage={null} sessionAccounting={detail.accounting} />}
  </>
}

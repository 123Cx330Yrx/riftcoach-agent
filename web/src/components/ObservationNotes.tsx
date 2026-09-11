import { useEffect, useRef, useState } from "react"
import { ApiClient } from "../api/client"
import { ObservationNotesApi, archiveReference, type NoteSaveOperation, type ObservationNote } from "../api/observationNotesApi"
import { PlayerLinkHttpApi } from "../api/playerLinkApi"
import { BrowserAuthSessionClient } from "../auth/session"
import type { ObservationArchive } from "../workbench/observationArchive"

export function ObservationNotes({ archive }: { readonly archive: ObservationArchive }) {
  const [connected, setConnected] = useState<{ profileId: string; csrf: string }>()
  const [notes, setNotes] = useState<ObservationNote[]>([])
  const [draft, setDraft] = useState("")
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState("")
  const [failed, setFailed] = useState(false)
  const abort = useRef<AbortController | undefined>(undefined)
  const operation = useRef<NoteSaveOperation | undefined>(undefined)
  const [api] = useState(() => new ObservationNotesApi(new ApiClient()))
  useEffect(() => () => abort.current?.abort(), [])
  async function connect() {
    if (busy) return
    abort.current?.abort()
    const controller = new AbortController(); abort.current = controller
    setBusy(true); setFailed(false); setMessage(""); setConnected(undefined); setNotes([])
    try {
      const session = await new BrowserAuthSessionClient().issue(controller.signal)
      const page = await new PlayerLinkHttpApi(new ApiClient()).listProfiles(controller.signal)
      if (controller.signal.aborted) return
      const profiles = page.profiles.filter(p => p.riot_id === archive.riot_id && p.routing_region === archive.region && p.relationship_role === "observed")
      if (profiles.length !== 1) {
        setMessage("请先在账号页选择或添加 ShowMaker 观摩档案，再返回连接。无需你的外服账号。")
        return
      }
      const profileId = profiles[0]!.player_profile_id
      const saved = await api.list(profileId, controller.signal)
      if (controller.signal.aborted) return
      if (operation.current && operation.current.profileId !== profileId) { operation.current = undefined; setDraft("") }
      setConnected({ profileId, csrf: session.csrf_token }); setNotes(saved)
      setMessage("已连接你的观摩档案。")
    } catch {
      if (!controller.signal.aborted) { setFailed(true); setMessage("暂时无法连接，请确认已登录 RiftCoach 并稍后重试。") }
    } finally { if (!controller.signal.aborted) setBusy(false) }
  }
  async function save() {
    if (!connected || busy || !draft.trim()) return
    if (!operation.current && new TextEncoder().encode(JSON.stringify({ text: draft.trim(), archive_reference: archiveReference(archive) })).byteLength > 4096) {
      setFailed(true); setMessage("笔记内容过长，请缩短后再保存。"); return
    }
    const controller = new AbortController(); abort.current = controller
    setBusy(true); setFailed(false); setMessage("")
    const op = operation.current ?? { key: crypto.randomUUID(), text: draft.trim(), reference: archiveReference(archive), profileId: connected.profileId }
    operation.current = op
    try {
      await api.save(op, connected.csrf, controller.signal)
      if (controller.signal.aborted) return
      // Read back from the server before claiming success. Retry keeps the same
      // candidate if acceptance succeeded but its response/readback was lost.
      const saved = await api.list(connected.profileId, controller.signal)
      if (controller.signal.aborted) return
      if (!saved.some(n => n.text === op.text && n.reference?.report_sha256 === op.reference.report_sha256 && n.reference?.source_run_id === op.reference.source_run_id && n.reference?.bundle_digest === op.reference.bundle_digest)) throw new Error("note_not_read_back")
      setNotes(saved); setDraft(""); operation.current = undefined
      setMessage("笔记已保存并重新读取。")
    } catch {
      if (!controller.signal.aborted) { setFailed(true); setMessage("保存结果尚未确认。重试会继续同一次保存；请保留本页。") }
    } finally { if (!controller.signal.aborted) setBusy(false) }
  }
  const currentNotes = notes.filter(n => n.reference?.source_run_id === archive.source_run_id && n.reference?.report_sha256 === archive.report.sha256 && n.reference?.bundle_digest === archive.evidence.bundle_digest)
  return <section className="panel observation-section observation-notes" aria-labelledby="observation-notes-title">
    <h2 id="observation-notes-title">我的观摩笔记</h2>
    <p className="observation-note">连接后，笔记保存到你的 RiftCoach 观摩档案。附带资料来源标识，归档报告本身仍保留在本地文件中。</p>
    {!connected && <><button type="button" disabled={busy} onClick={() => { void connect() }}>{busy ? "正在连接…" : "连接观摩档案"}</button><a className="observation-account-link" href="/?stage=account">前往账号页</a></>}
    {connected && <form onSubmit={e => { e.preventDefault(); void save() }}>
      <label htmlFor="observation-note-text">这次观察到了什么？</label>
      <textarea id="observation-note-text" value={draft} maxLength={1000} disabled={busy || operation.current !== undefined} onChange={e => setDraft(e.target.value)} placeholder="记录一个发现、疑问，或下次想验证的细节。" />
      <button type="submit" disabled={busy || !draft.trim()}>{busy ? "正在保存…" : operation.current ? "重试本次保存" : "保存观摩笔记"}</button>
    </form>}
    {connected && <button className="observation-reconnect" type="button" disabled={busy} onClick={() => { void connect() }}>重新连接并读取</button>}
    {message && <p role={failed ? "alert" : "status"}>{message}</p>}
    {connected && <div aria-label="本份资料的已存笔记"><p className="observation-note">本份资料的笔记（从最近读取的最多 100 条记录中筛选）</p>{currentNotes.length === 0 ? <p>还没有笔记。</p> : currentNotes.map(note => <article className="observation-source" key={note.id}><p>{note.text}</p><time>{note.createdAt}</time><small> 用户附加的归档来源</small></article>)}</div>}
  </section>
}

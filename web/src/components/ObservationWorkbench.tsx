import { useRef, useState } from "react"
import { ARCHIVE_MAX_BYTES, parseObservationArchive, type ObservationArchive } from "../workbench/observationArchive"
import { SafeMarkdown } from "./SafeMarkdown"
import "../styles/observation.css"

const positions: Record<string, string> = { mid: "中路", support: "辅助", top: "上路", jungle: "打野", adc: "下路", MIDDLE: "中路", UTILITY: "辅助" }
const positionName = (value: string) => positions[value] ?? value
const metric = (value: number | null) => value === null ? "未提供" : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value)
function readFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject()
    reader.onerror = () => reject()
    reader.readAsText(file, "utf-8")
  })
}

export function ObservationWorkbench() {
  const [archive, setArchive] = useState<ObservationArchive>()
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(false)
  const [selectedPosition, setSelectedPosition] = useState("all")
  const [completed, setCompleted] = useState<Set<string>>(new Set())
  const generation = useRef(0)
  async function importFile(file: File | undefined) {
    if (!file) return
    const current = ++generation.current
    setArchive(undefined); setError(false); setLoading(true); setCompleted(new Set()); setSelectedPosition("all")
    try {
      if (file.size > ARCHIVE_MAX_BYTES) throw new Error("large_file")
      const parsed = await parseObservationArchive(await readFile(file))
      if (current === generation.current) setArchive(parsed)
    } catch { if (current === generation.current) setError(true) }
    finally { if (current === generation.current) setLoading(false) }
  }
  const matches = archive?.summary.matches.filter(m => selectedPosition === "all" || m.position === selectedPosition) ?? []
  return <main className="observation-workbench" lang="zh-CN">
    <nav className="observation-nav"><a href="/">RIFTCOACH</a><span>观摩工作台 · 本地归档</span></nav>
    <header className="observation-hero">
      <p className="eyebrow">LEARN FROM THE GAME</p>
      <h1>ShowMaker 观摩复盘</h1>
      <p>从同位置对局中提出问题，再用录像验证。无需外服账号。</p>
      <label className="observation-import">导入观摩资料<input aria-label="导入观摩资料" type="file" accept=".json,application/json" onChange={event => { void importFile(event.target.files?.[0]); event.target.value = "" }} /></label>
      <p className="observation-note">文件仅在当前浏览器读取。练习勾选只保留在本页，刷新后清空，不写入个人训练记录。</p>
      {loading && <p role="status">正在检查资料…</p>}
      {error && <p role="alert">资料不完整、内容已变更或格式不受支持，请重新导出观摩资料。</p>}
    </header>
    {!archive && !loading && <section className="panel observation-empty"><h2>从一份完整的观摩资料开始</h2><p>导入本地导出的 ShowMaker 观摩 JSON，即可查看分路样本、人工校订报告、来源时间和练习示例。</p><p>这里只展示归档样本，不代表最新版本环境或你的个人表现。</p></section>}
    {archive && <>
      <section className="observation-summary" aria-label="观摩样本概况">
        <div><span>观摩对象</span><strong>{archive.riot_id}</strong></div>
        <div><span>已选对局</span><strong>{archive.summary.games} 局</strong></div>
        <div><span>样本战绩</span><strong>{archive.summary.wins} 胜 / {archive.summary.losses} 负</strong></div>
        <div><span>比赛资料归档时间</span><strong className="observation-date">{archive.observed_at}</strong></div>
      </section>
      <div className="observation-layout">
        <div>
          <section className="panel observation-section" aria-labelledby="observation-matches">
            <div className="observation-section-heading"><h2 id="observation-matches">按位置看对局</h2><label>位置 <select aria-label="筛选位置" value={selectedPosition} onChange={e => setSelectedPosition(e.target.value)}><option value="all">全部位置</option>{archive.summary.positions.map(p => <option key={p.position} value={p.position}>{positionName(p.position)} · {p.games} 局</option>)}</select></label></div>
            <p className="observation-note">不同职责分开比较；本次位置分布不代表长期主位置，也不能判断补位意图。</p>
            <div className="observation-table-scroll"><table><caption>已选对局明细</caption><thead><tr><th>英雄 / 对局</th><th>位置</th><th>结果</th><th>补刀/分</th><th>伤害/分</th><th>15 分钟前死亡</th></tr></thead><tbody>{matches.map(m => <tr key={m.match_id}><td><strong>{m.champion}</strong><small>{m.match_id}</small></td><td>{positionName(m.position)}</td><td>{m.win ? "胜" : "负"}</td><td>{metric(m.cs_per_min)}</td><td>{metric(m.damage_per_min)}</td><td>{metric(m.deaths_before_15)}</td></tr>)}</tbody></table></div>
          </section>
          <section className="panel observation-section" aria-labelledby="observation-report"><h2 id="observation-report">人工校订报告</h2><p className="observation-note">原模型报告复评 {archive.report.automated_score} 分，人工复核仍发现问题；以下是另行校订副本，未重新自动评分。</p><SafeMarkdown markdown={archive.report.text} /></section>
        </div>
        <aside>
          <section className="panel observation-section" aria-labelledby="observation-exercises"><p className="eyebrow">WATCH · QUESTION · VERIFY</p><h2 id="observation-exercises">观摩练习示例</h2><p className="observation-note">勾选表示你完成了本页的观察，不代表该选手或你的训练指标改善。</p>{archive.exercises.map(e => <article className="observation-exercise" key={e.id}><label><input type="checkbox" checked={completed.has(e.id)} onChange={() => setCompleted(old => { const next = new Set(old); if (next.has(e.id)) next.delete(e.id); else next.add(e.id); return next })} /><strong>{e.title}</strong></label><p>{e.prompt}</p><small>{e.evidence_note}</small></article>)}<p role="status">本页已完成 {completed.size} / {archive.exercises.length} 项观察</p></section>
          <section className="panel observation-section" aria-labelledby="observation-sources"><h2 id="observation-sources">来源与时间</h2><p className="observation-note">以下均为归档快照，不能自动当作当前版本或同段位基准。</p>{archive.evidence.sources.map((s, i) => <article className="observation-source" key={i}><h3>{s.label}</h3><p>{s.detail}</p><time>{s.observed_at}</time></article>)}<details><summary>查看来源记录</summary><p>源运行：{archive.source_run_id}</p><p>证据摘要：{archive.evidence.bundle_digest}</p><p>校订报告摘要：{archive.report.sha256}</p><p>导出时间：{archive.exported_at}</p></details></section>
        </aside>
      </div>
    </>}
  </main>
}

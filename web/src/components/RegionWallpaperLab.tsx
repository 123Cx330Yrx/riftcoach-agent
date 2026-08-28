import { useEffect, useMemo, useState } from "react"

import { LocaleSwitch } from "./LocaleSwitch"
import { regionWallpaperCatalog } from "../wallpapers/regionWallpaperCatalog"
import { useI18n } from "../i18n/ProductLocaleProvider"

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const query = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setReduced(query.matches)
    update()
    if (typeof query.addEventListener === "function") {
      query.addEventListener("change", update)
      return () => query.removeEventListener("change", update)
    }
    query.addListener?.(update)
    return () => query.removeListener?.(update)
  }, [])
  return reduced
}

export function RegionWallpaperLab() {
  const { locale } = useI18n()
  const reducedMotion = useReducedMotion()
  const candidates = regionWallpaperCatalog.candidates
  const [selectedId, setSelectedId] = useState(candidates[0]?.id ?? "")
  const [videoFailed, setVideoFailed] = useState(false)
  const [activating, setActivating] = useState(false)
  const selected = useMemo(() => candidates.find((candidate) => candidate.id === selectedId) ?? candidates[0], [candidates, selectedId])
  if (selected === undefined) return null

  const label = selected.label[locale]
  const description = selected.description[locale]
  const playVideo = !reducedMotion && !videoFailed
  const handleActivate = () => {
    if (activating) return
    setActivating(true)
    window.setTimeout(() => setActivating(false), 760)
  }

  return (
    <main className={`wallpaper-lab${activating ? " wallpaper-lab--activating" : ""}`} data-testid="wallpaper-lab" data-region={selected.region} data-video={playVideo ? "enabled" : "poster"}>
      <div className="wallpaper-lab__media" aria-hidden="true">
        <img className="wallpaper-lab__poster" src={selected.poster} alt="" />
        {playVideo ? (
          <video
            className="wallpaper-lab__video"
            autoPlay
            loop
            muted
            playsInline
            poster={selected.poster}
            onError={() => setVideoFailed(true)}
          >
            <source src={selected.webm} type="video/webm" />
            <source src={selected.mp4} type="video/mp4" />
          </video>
        ) : null}
      </div>
      <div className="wallpaper-lab__scrim" aria-hidden="true" />
      <header className="wallpaper-lab__header">
        <div className="wallpaper-lab__brand"><span className="wallpaper-lab__brand-mark" aria-hidden="true">R</span><span>RIFTCOACH</span></div>
        <LocaleSwitch />
      </header>
      <section className="wallpaper-lab__content" aria-labelledby="wallpaper-lab-title">
        <p className="wallpaper-lab__kicker">{locale === "zh-CN" ? "地区地图 / 本地预览" : "REGION ATLAS / LOCAL PREVIEW"}</p>
        <h1 id="wallpaper-lab-title">{locale === "zh-CN" ? <>选择一处地区<br /><em>开启 RiftCoach。</em></> : <>Choose the region<br /><em>that opens the Rift.</em></>}</h1>
        <p className="wallpaper-lab__lede">{locale === "zh-CN" ? "先选一处符文大陆，再进入 RiftCoach。这里的画面只负责氛围，复盘仍由真实数据驱动。" : "Choose a place in Runeterra before entering RiftCoach. The scene sets the mood; your review still comes from real data."}</p>
        <div className="wallpaper-lab__selection" aria-label={locale === "zh-CN" ? "地区选择" : "Region selection"}>
          {candidates.map((candidate) => {
            const active = candidate.id === selected.id
            return (
              <button className={`wallpaper-lab__region${active ? " wallpaper-lab__region--active" : ""}`} key={candidate.id} type="button" aria-pressed={active} onClick={() => { setSelectedId(candidate.id); setVideoFailed(false) }}>
                <span className="wallpaper-lab__region-glyph" aria-hidden="true">◇</span>
                <span><strong>{candidate.label[locale]}</strong><small>{candidate.region.toUpperCase()}</small></span>
              </button>
            )
          })}
          <span className="wallpaper-lab__region-note">{locale === "zh-CN" ? "更多地区素材待核验" : "More regions after source review"}</span>
        </div>
        <div className="wallpaper-lab__footer-row">
          <div><span className="wallpaper-lab__status-dot" /> <span>{label}</span><small>{description}</small></div>
          <button className="wallpaper-lab__enter" type="button" onClick={handleActivate} aria-describedby="wallpaper-lab-enter-note" aria-disabled={activating ? "true" : undefined}>
            <span>{locale === "zh-CN" ? "进入 RiftCoach" : "Enter RiftCoach"}</span><span aria-hidden="true">↗</span>
          </button>
        </div>
        <p id="wallpaper-lab-enter-note" className="wallpaper-lab__note">{reducedMotion ? (locale === "zh-CN" ? "已按系统设置使用静态画面。" : "Static poster follows your motion setting.") : videoFailed ? (locale === "zh-CN" ? "动态文件无法播放，已切换静态画面。" : "The motion file could not play, so the poster is shown.") : (locale === "zh-CN" ? "本地候选 · 尚未进入正式素材清单" : "Local candidate · not yet in the adopted media set")}</p>
      </section>
      <div className="wallpaper-lab__transition" aria-hidden="true"><span /><span /><span /></div>
    </main>
  )
}

import { useEffect, useMemo, useState } from "react"

import { useI18n } from "../i18n/ProductLocaleProvider"
import { regionIconCatalog } from "../wallpapers/regionIconCatalog"
import { regionWallpaperCatalog, type WallpaperRegion } from "../wallpapers/regionWallpaperCatalog"
import { LocaleSwitch } from "./LocaleSwitch"

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

export function RegionWallpaperLab({ onEnter }: { readonly onEnter?: (region: WallpaperRegion) => void } = {}) {
  const { locale } = useI18n()
  const reducedMotion = useReducedMotion()
  const candidates = regionWallpaperCatalog.candidates
  const [selectedId, setSelectedId] = useState(candidates[0]?.id ?? "")
  const [videoFailed, setVideoFailed] = useState(false)
  const [activating, setActivating] = useState(false)
  const selected = useMemo(
    () => candidates.find((candidate) => candidate.id === selectedId) ?? candidates[0],
    [candidates, selectedId],
  )
  if (selected === undefined) return null

  const label = selected.label[locale]
  const description = selected.description[locale]
  const playVideo = !reducedMotion && !videoFailed
  const selectedIcon = regionIconCatalog.find((icon) => icon.id === selected.region)
  const readyCount = candidates.length
  const handleActivate = () => {
    if (activating) return
    setActivating(true)
    window.setTimeout(() => {
      setActivating(false)
      onEnter?.(selected.region)
    }, 760)
  }

  return (
    <main
      className={`wallpaper-lab${activating ? " wallpaper-lab--activating" : ""}`}
      data-testid="wallpaper-lab"
      data-region={selected.region}
      data-video={playVideo ? "enabled" : "poster"}
    >
      <div className="wallpaper-lab__media" aria-hidden="true">
        <img className="wallpaper-lab__poster" src={selected.poster} alt="" />
        {playVideo ? (
          <video
            key={selected.id}
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
        <div className="wallpaper-lab__brand">
          <span className="wallpaper-lab__brand-mark" aria-hidden="true">R</span>
          <span>RIFTCOACH</span>
        </div>
        <div className="wallpaper-lab__header-meta">
          <span>{locale === "zh-CN" ? "地区入口" : "REGION ENTRY"}</span>
          <LocaleSwitch />
        </div>
      </header>
      <section className="wallpaper-lab__content" aria-labelledby="wallpaper-lab-title">
        <div className="wallpaper-lab__intro">
          <p className="wallpaper-lab__kicker">{locale === "zh-CN" ? "地区档案 · 本地预览" : "REGION ATLAS · LOCAL PREVIEW"}</p>
          <h1 id="wallpaper-lab-title">
            {locale === "zh-CN" ? <>先选一处<br /><em>落脚点。</em></> : <>Choose your<br /><em>starting point.</em></>}
          </h1>
          <p className="wallpaper-lab__lede">
            {locale === "zh-CN"
              ? "选定地区后，RiftCoach 会带着对应的场景进入账号页。画面负责氛围，复盘仍由真实数据驱动。"
              : "Choose a region and RiftCoach will carry its scene into your account setup. The mood is visual; the review stays grounded in real data."}
          </p>
          <div className="wallpaper-lab__current" aria-live="polite">
            <span className="wallpaper-lab__current-mark" aria-hidden="true">
              {selectedIcon === undefined ? null : <img src={selectedIcon.asset} alt="" />}
            </span>
            <span>
              <small>{locale === "zh-CN" ? "当前地区" : "CURRENT REGION"}</small>
              <strong>{label}</strong>
            </span>
          </div>
        </div>
        <div className="wallpaper-lab__atlas" aria-label={locale === "zh-CN" ? "地区选择" : "Region selection"}>
          <div className="wallpaper-lab__atlas-head">
            <span>
              <b>{locale === "zh-CN" ? "选择地区" : "Select a region"}</b>
              <small>{locale === "zh-CN" ? "背景会即时切换" : "The scene switches instantly"}</small>
            </span>
            <small className="wallpaper-lab__atlas-count">
              {readyCount.toString().padStart(2, "0")} / 13 {locale === "zh-CN" ? "可用" : "READY"}
            </small>
          </div>
          <div className="wallpaper-lab__selection">
            {regionIconCatalog.map((icon, index) => {
              const candidate = candidates.find((item) => item.region === icon.id)
              const active = candidate?.id === selected.id
              return (
                <button
                  className={`wallpaper-lab__region${active ? " wallpaper-lab__region--active" : ""}${candidate === undefined ? " wallpaper-lab__region--pending" : ""}`}
                  key={icon.id}
                  type="button"
                  aria-pressed={active}
                  disabled={candidate === undefined}
                  onClick={() => {
                    if (candidate !== undefined) {
                      setSelectedId(candidate.id)
                      setVideoFailed(false)
                    }
                  }}
                >
                  <img className="wallpaper-lab__region-glyph" src={icon.asset} alt="" />
                  <span>
                    <strong>{candidate ? candidate.label[locale] : icon.label[locale]}</strong>
                    <small>
                      {candidate
                        ? (locale === "zh-CN" ? "可切换背景" : "SWITCH BACKDROP")
                        : (locale === "zh-CN" ? `待核验 · ${String(index + 1).padStart(2, "0")}` : `PENDING · ${String(index + 1).padStart(2, "0")}`)}
                    </small>
                  </span>
                </button>
              )
            })}
          </div>
          <div className="wallpaper-lab__selection-note">
            <span className="wallpaper-lab__selection-note-line" />
            {locale === "zh-CN"
              ? "徽记沿用 Riot Universe 语义；当前先开放两份已核验格式的本地候选。"
              : "Crests follow Riot Universe semantics; two format-audited local candidates are open in this pass."}
          </div>
        </div>
        <div className="wallpaper-lab__footer-row">
          <div>
            <span className="wallpaper-lab__status-dot" />
            <span>{label}</span>
            <small>{description}</small>
          </div>
          <button
            className="wallpaper-lab__enter"
            type="button"
            onClick={handleActivate}
            aria-describedby="wallpaper-lab-enter-note"
            aria-disabled={activating ? "true" : undefined}
          >
            <span>{locale === "zh-CN" ? "进入账号" : "Enter RiftCoach"}</span>
            <span aria-hidden="true">↗</span>
          </button>
        </div>
        <p id="wallpaper-lab-enter-note" className="wallpaper-lab__note">
          {reducedMotion
            ? (locale === "zh-CN" ? "已按系统设置使用静态画面。" : "Static poster follows your motion setting.")
            : videoFailed
              ? (locale === "zh-CN" ? "动态文件无法播放，已切换静态画面。" : "The motion file could not play, so the poster is shown.")
              : (locale === "zh-CN" ? `将以${label}背景进入账号页` : `Account setup will open with the ${label} scene`)}
        </p>
      </section>
      <div className="wallpaper-lab__transition" aria-hidden="true"><span /><span /><span /></div>
    </main>
  )
}

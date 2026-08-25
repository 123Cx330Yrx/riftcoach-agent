import type {
  AwakeningPresentationState,
} from "../awakening/model"
import type { PortalActivationState } from "../cinematic/portalActivation"
import { useI18n } from "../i18n/ProductLocaleProvider"
import { LocaleSwitch } from "./LocaleSwitch"

export function AwakeningScene({
  state,
  disclosure,
  onEnter,
  activationState,
  onActivate,
  entryMode = "production",
}: {
  readonly state: AwakeningPresentationState
  readonly disclosure?: string
  readonly onEnter: () => void
  readonly activationState?: PortalActivationState
  readonly onActivate?: () => void
  readonly entryMode?: "production" | "demo"
}) {
  const { t } = useI18n()
  const activationPhase = activationState?.phase ?? "idle"
  const activating = activationPhase !== "idle"

  const enter = () => {
    if (activating) return
    const activate = onActivate ?? onEnter
    activate()
  }

  return (
    <main
      className={`awakening-scene awakening-scene--${state.phase}${activating ? " awakening-scene--departing" : ""}${activationPhase !== "idle" ? ` awakening-scene--activation-${activationPhase}` : ""}`}
      data-testid="awakening-scene"
      data-phase={state.phase}
      data-motion={state.motion}
      data-departing={activating ? "true" : "false"}
      data-activation={activationPhase}
    >
      <div className="awakening-scene__field" aria-hidden="true">
        <svg viewBox="0 0 1200 760" preserveAspectRatio="xMidYMid slice">
          <path d="M-80 610C170 470 230 260 470 220s330 160 730-120" />
          <path d="M-30 710C210 520 310 450 520 430s350 80 730-290" />
          <path d="M80 780c230-210 330-270 540-260s320-60 570-270" />
          <path className="awakening-scene__route" d="M50 720 580 390 1160 60" />
          <circle cx="580" cy="390" r="18" />
          <circle cx="580" cy="390" r="52" />
        </svg>
      </div>
      <header className="awakening-scene__header">
        <div className="awakening-scene__header-copy">
          <p className="eyebrow"><span className="eyebrow__line" /> {t("awakening.header_kicker")}</p>
          {disclosure === undefined ? null : <p className="awakening-scene__status">{disclosure}</p>}
        </div>
        <LocaleSwitch />
      </header>
      <section className="awakening-scene__hero" aria-labelledby="awakening-title">
        <h1 id="awakening-title">{t("awakening.hero_title")}</h1>
        <p className="awakening-scene__lede">{t("awakening.hero_lede")}</p>
        <button
          className="awakening-scene__core"
          type="button"
          onClick={enter}
          aria-disabled={activating ? "true" : undefined}
          aria-describedby="awakening-enter-hint"
        >
          <span className="awakening-scene__core-orbit" />
          <span className="awakening-scene__core-orbit awakening-scene__core-orbit--inner" />
          <span className="awakening-scene__core-point" />
          <span className="awakening-scene__core-label">
            {t(entryMode === "demo" ? "awakening.demo_enter" : "awakening.enter")}
          </span>
        </button>
        <p id="awakening-enter-hint" className="awakening-scene__enter-hint">
          {t("awakening.enter_hint")}
        </p>
      </section>
    </main>
  )
}

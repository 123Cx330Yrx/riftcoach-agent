import { Glyph } from "./VisualGlyphs"
import { useI18n } from "../i18n/ProductLocaleProvider"
import type { MessageKey } from "../i18n/locale"
import { LocaleSwitch } from "./LocaleSwitch"

const links = [
  { href: "#overview", label: "nav.review" as MessageKey, icon: "review" as const },
  { href: "#coach-brief", label: "nav.coach" as MessageKey, icon: "command" as const },
  { href: "#training", label: "nav.training" as MessageKey, icon: "training" as const },
  { href: "#evidence", label: "nav.evidence" as MessageKey, icon: "evidence" as const },
]

export function CommandRail({ mode }: { readonly mode: "fixture" | "live" }) {
  const { t } = useI18n()
  return (
    <nav className="command-rail" aria-label={t("nav.label")}>
      <a className="brand-mark" href="#review-workspace" aria-label={t("nav.brand_label")}>
        <span className="brand-mark__sigil">
          <Glyph name="command" />
        </span>
        <span className="brand-mark__word">RIFT<br />COACH</span>
      </a>

      <div className="command-rail__links">
        {links.map((link, index) => (
          <a
            className={`command-link${index === 0 ? " command-link--active" : ""}`}
            href={link.href}
            key={link.href}
          >
            <Glyph name={link.icon} />
            <span>{t(link.label)}</span>
          </a>
        ))}
      </div>

      <div className="command-rail__locale">
        <LocaleSwitch />
      </div>

      <div className="command-rail__mode" aria-label={t("nav.runtime_environment")}>
        <span className="mode-pulse" />
        <span>{mode === "live" ? t("nav.live") : t("nav.fixture")}</span>
        <small>{mode === "live" ? t("nav.owner_scoped") : t("nav.no_live_io")}</small>
      </div>
    </nav>
  )
}

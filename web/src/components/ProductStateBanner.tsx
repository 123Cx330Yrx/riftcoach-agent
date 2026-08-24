import type { WorkbenchProductState } from "../workbench/model"
import { useI18n } from "../i18n/ProductLocaleProvider"
import type { MessageKey } from "../i18n/locale"
import { taskStatusMessageKeys } from "../i18n/productCopy"
import { Glyph, type GlyphName } from "./VisualGlyphs"

const stateContent: Record<
  WorkbenchProductState["state"],
  { label: MessageKey; title: MessageKey; description: MessageKey; icon: GlyphName }
> = {
  published: {
    label: "product.published_label",
    title: "product.published_title",
    description: "product.published_body",
    icon: "check",
  },
  degraded: {
    label: "product.degraded_label",
    title: "product.degraded_title",
    description: "product.degraded_body",
    icon: "limit",
  },
  rejected: {
    label: "product.rejected_label",
    title: "product.rejected_title",
    description: "product.rejected_body",
    icon: "withheld",
  },
  not_ready: {
    label: "product.not_ready_label",
    title: "product.not_ready_title",
    description: "product.not_ready_body",
    icon: "pending",
  },
}

const freshnessKeys = {
  current: "evidence.freshness.current",
  expired: "evidence.freshness.expired",
} as const

export function ProductStateBanner({ state }: { readonly state: WorkbenchProductState }) {
  const { t } = useI18n()
  const content = stateContent[state.state]

  return (
    <section className={`product-state product-state--${state.state}`} aria-labelledby="product-state-title">
      <span className="product-state__icon"><Glyph name={content.icon} /></span>
      <div className="product-state__copy">
        <div className="product-state__label-row">
          <span className="product-state__label">{t(content.label)}</span>
        </div>
        <h3 id="product-state-title">{t(content.title)}</h3>
        <p>{t(content.description)}</p>
      </div>
      <div className="product-state__telemetry" aria-label={t("product.telemetry")}>
        <span>{t("product.task")}</span>
        <strong>{t(taskStatusMessageKeys[state.taskStatus])}</strong>
        <span>{t("product.evidence")}</span>
        <strong>{state.evidenceFreshness === undefined ? t("common.pending") : t(freshnessKeys[state.evidenceFreshness])}</strong>
      </div>
    </section>
  )
}

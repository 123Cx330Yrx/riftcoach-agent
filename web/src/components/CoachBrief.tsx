import type { WorkbenchCoachReport, WorkbenchProductState } from "../workbench/model"
import { SafeMarkdown } from "./SafeMarkdown"
import { Glyph } from "./VisualGlyphs"
import { useI18n } from "../i18n/ProductLocaleProvider"

interface CoachBriefProps {
  readonly productState: WorkbenchProductState
  readonly report: WorkbenchCoachReport | undefined
}

export function CoachBrief({ productState, report }: CoachBriefProps) {
  const { t } = useI18n()
  if (productState.state === "rejected") {
    return (
      <section className="coach-brief coach-brief--withheld panel" id="coach-brief" aria-labelledby="withheld-title">
        <span className="coach-brief__sigil"><Glyph name="withheld" /></span>
        <div>
          <p className="eyebrow">{t("coach.quality_control")}</p>
          <h3 id="withheld-title">{t("coach.withheld_title")}</h3>
          <p>{t("coach.withheld_body")}</p>
        </div>
      </section>
    )
  }

  if (productState.state === "not_ready" || report === undefined) {
    return (
      <section className="coach-brief coach-brief--pending panel" id="coach-brief" aria-labelledby="pending-brief-title">
        <span className="coach-brief__sigil"><Glyph name="pending" /></span>
        <div>
          <p className="eyebrow">{t("coach.channel")}</p>
          <h3 id="pending-brief-title">{t("coach.pending_title")}</h3>
          <p>{t("coach.pending_body")}</p>
        </div>
      </section>
    )
  }

  return (
    <section className="coach-brief panel" id="coach-brief" aria-labelledby="coach-brief-title">
      <div className="coach-brief__header">
        <span className="coach-brief__sigil"><Glyph name="command" /></span>
        <div>
          <p className="eyebrow">{t("coach.core")}</p>
          <h3 id="coach-brief-title">{t("coach.title")}</h3>
        </div>
        <span className="coach-brief__status">{productState.state === "degraded" ? t("coach.status_limited") : t("coach.status_verified")}</span>
      </div>
      <p className="original-content-disclosure">{t("coach.original_content")}</p>
      <div translate="no">
        <SafeMarkdown markdown={report.markdown} />
      </div>
    </section>
  )
}

import type { WorkbenchCoachReport, WorkbenchProductState } from "../workbench/model"
import { SafeMarkdown } from "./SafeMarkdown"
import { Glyph } from "./VisualGlyphs"

interface CoachBriefProps {
  readonly productState: WorkbenchProductState
  readonly report: WorkbenchCoachReport | undefined
}

export function CoachBrief({ productState, report }: CoachBriefProps) {
  if (productState.state === "rejected") {
    return (
      <section className="coach-brief coach-brief--withheld panel" id="coach-brief" aria-labelledby="withheld-title">
        <span className="coach-brief__sigil"><Glyph name="withheld" /></span>
        <div>
          <p className="eyebrow">QUALITY CONTROL</p>
          <h3 id="withheld-title">Review withheld</h3>
          <p>The report did not clear the publication gate. RiftCoach does not replace it with an unverified draft.</p>
          <code>{productState.reasonCode}</code>
        </div>
      </section>
    )
  }

  if (productState.state === "not_ready" || report === undefined) {
    return (
      <section className="coach-brief coach-brief--pending panel" id="coach-brief" aria-labelledby="pending-brief-title">
        <span className="coach-brief__sigil"><Glyph name="pending" /></span>
        <div>
          <p className="eyebrow">COACH CHANNEL</p>
          <h3 id="pending-brief-title">Brief awaits a terminal review</h3>
          <p>Lifecycle truth stays visible while the coaching surface remains locked.</p>
        </div>
      </section>
    )
  }

  return (
    <section className="coach-brief panel" id="coach-brief" aria-labelledby="coach-brief-title">
      <div className="coach-brief__header">
        <span className="coach-brief__sigil"><Glyph name="command" /></span>
        <div>
          <p className="eyebrow">COACH CORE · QUALITY-GATED</p>
          <h3 id="coach-brief-title">Tactical brief</h3>
        </div>
        <span className="coach-brief__status">{productState.state === "degraded" ? "LIMITED" : "VERIFIED"}</span>
      </div>
      <SafeMarkdown markdown={report.markdown} />
    </section>
  )
}

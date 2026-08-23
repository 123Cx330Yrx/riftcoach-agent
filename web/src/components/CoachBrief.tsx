import type { CoachReportFixture, ProductStateFixture } from "../contracts/workbench"
import { Glyph } from "./VisualGlyphs"

interface CoachBriefProps {
  readonly productState: ProductStateFixture
  readonly report: CoachReportFixture | undefined
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
      <blockquote>{report.verdict}</blockquote>
      <p className="coach-brief__summary">{report.summary}</p>
      <div className="coach-brief__orders">
        <div>
          <span className="order-label">HOLD</span>
          <p>{report.strengths[0]}</p>
        </div>
        <div>
          <span className="order-label order-label--move">MOVE</span>
          <p>{report.priorities[0]}</p>
        </div>
      </div>
      <div className="next-session">
        <span>NEXT SESSION</span>
        <p>{report.nextSession}</p>
      </div>
    </section>
  )
}

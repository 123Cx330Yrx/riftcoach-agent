import type { WorkbenchProductState } from "../workbench/model"
import { Glyph, type GlyphName } from "./VisualGlyphs"

const stateContent: Record<
  WorkbenchProductState["state"],
  { label: string; title: string; description: string; icon: GlyphName }
> = {
  published: {
    label: "Published",
    title: "Review cleared for coaching",
    description: "Quality gate passed with complete, current evidence.",
    icon: "check",
  },
  degraded: {
    label: "Degraded",
    title: "Evidence limitations",
    description: "The coaching brief remains useful, with the limits below kept in view.",
    icon: "limit",
  },
  rejected: {
    label: "Rejected",
    title: "Publication blocked",
    description: "The quality gate blocked publication. No substitute report is shown.",
    icon: "withheld",
  },
  not_ready: {
    label: "Not ready",
    title: "Analysis in progress",
    description: "Lifecycle events are available; no percentage or finish time is invented.",
    icon: "pending",
  },
}

export function ProductStateBanner({ state }: { readonly state: WorkbenchProductState }) {
  const content = stateContent[state.state]

  return (
    <section className={`product-state product-state--${state.state}`} aria-labelledby="product-state-title">
      <span className="product-state__icon"><Glyph name={content.icon} /></span>
      <div className="product-state__copy">
        <div className="product-state__label-row">
          <span className="product-state__label">{content.label}</span>
          <code>{state.reasonCode}</code>
        </div>
        <h3 id="product-state-title">{content.title}</h3>
        <p>{content.description}</p>
      </div>
      <div className="product-state__telemetry" aria-label="Product state telemetry">
        <span>Task</span>
        <strong>{state.taskStatus.replaceAll("_", " ")}</strong>
        <span>Evidence</span>
        <strong>{state.evidenceFreshness ?? "pending"}</strong>
      </div>
    </section>
  )
}

import * as Dialog from "@radix-ui/react-dialog"
import { LazyMotion, MotionConfig, domAnimation, m } from "motion/react"

import type {
  WorkbenchEvidence,
  WorkbenchRun,
  WorkbenchTaskEvent,
} from "../workbench/model"
import { Glyph } from "./VisualGlyphs"

const statusCopy = {
  complete: "Evidence chain complete",
  degraded: "Evidence chain limited",
  rejected: "Evidence chain rejected",
} as const

interface EvidenceDrawerProps {
  readonly evidence: WorkbenchEvidence | undefined
  readonly events: readonly WorkbenchTaskEvent[]
  readonly run: WorkbenchRun | undefined
}

export function EvidenceDrawer({ evidence, events, run }: EvidenceDrawerProps) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button className="evidence-launch" id="evidence" type="button" disabled={evidence === undefined}>
          <span className="evidence-launch__icon"><Glyph name="evidence" /></span>
          <span><small>EVIDENCE LEDGER</small><strong>Open evidence</strong></span>
          <Glyph className="evidence-launch__arrow" name="arrow" />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <MotionConfig reducedMotion="user">
          <LazyMotion features={domAnimation}>
            <Dialog.Overlay asChild>
              <m.div className="evidence-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            </Dialog.Overlay>
            <Dialog.Content asChild aria-describedby="evidence-description">
              <m.section
                className="evidence-drawer"
                initial={{ opacity: 0, x: 48 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 24 }}
                transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              >
                <div className="evidence-drawer__energy" aria-hidden="true" />
                <header className="evidence-drawer__header">
                  <div>
                    <p className="eyebrow">PROVENANCE · REVISION {evidence?.revision ?? "—"}</p>
                    <Dialog.Title>Evidence ledger</Dialog.Title>
                    <Dialog.Description id="evidence-description">
                      Sources, joins and limits behind this coaching state. Hidden reasoning is never exposed.
                    </Dialog.Description>
                  </div>
                  <Dialog.Close asChild>
                    <button className="icon-button" type="button" aria-label="Close evidence ledger"><Glyph name="close" /></button>
                  </Dialog.Close>
                </header>

                {evidence !== undefined && (
                  <div className="evidence-drawer__body">
                    <section className={`evidence-verdict evidence-verdict--${evidence.disposition}`}>
                      <span><Glyph name={evidence.disposition === "complete" ? "check" : "limit"} /></span>
                      <div><small>{evidence.disposition.toUpperCase()} · {evidence.freshness.toUpperCase()}</small><strong>{statusCopy[evidence.disposition]}</strong></div>
                      <b>{evidence.confidence.toUpperCase()} CONFIDENCE</b>
                    </section>

                    <section aria-labelledby="sources-title">
                      <div className="drawer-section-title"><span>01</span><h3 id="sources-title">Source stack</h3></div>
                      <div className="source-stack">
                        {evidence.sources.map((source) => (
                          <article key={source.sourceKind}>
                            <span className={`source-node source-node--${source.status}`} />
                            <div><strong>{source.label}</strong><p>{source.detail}</p></div>
                            <small>{source.status} · {source.freshness}</small>
                          </article>
                        ))}
                      </div>
                    </section>

                    <section aria-labelledby="run-path-title">
                      <div className="drawer-section-title"><span>02</span><h3 id="run-path-title">Safe run path</h3></div>
                      <div className="run-path">
                        {events.map((event, index) => (
                          <article className="run-path__event" key={`${event.cursor}-${event.eventKind}`}>
                            <span className={`run-path__node${index === events.length - 1 ? " run-path__node--terminal" : ""}`} aria-hidden="true" />
                            <div>
                              <strong>{event.eventKind.replaceAll("_", " ")}</strong>
                              <small>{event.statusAfter.replaceAll("_", " ")}</small>
                            </div>
                            <time dateTime={event.occurredAt}>
                              {new Date(event.occurredAt).toLocaleTimeString("en-GB", {
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit",
                                timeZone: "UTC",
                              })}Z
                            </time>
                          </article>
                        ))}
                      </div>
                      {run !== undefined && (
                        <dl className="run-summary">
                          <div><dt>Runtime</dt><dd>{run.runtimeStatus}</dd></div>
                          <div><dt>Publication</dt><dd>{run.publicationStatus ?? "pending"}</dd></div>
                          <div><dt>Elapsed</dt><dd>{run.elapsedMs === undefined ? "pending" : `${(run.elapsedMs / 1000).toFixed(1)}s`}</dd></div>
                        </dl>
                      )}
                      <p className="run-path__boundary">Only body-free lifecycle facts are shown. Prompts, tool arguments and hidden reasoning stay private.</p>
                    </section>

                    <section aria-labelledby="joins-title">
                      <div className="drawer-section-title"><span>03</span><h3 id="joins-title">Join decisions</h3></div>
                      <div className="join-grid">
                        {evidence.joins.map((join) => (
                          <article key={join.label}><small>{join.status.toUpperCase()}</small><strong>{join.label}</strong><p>{join.detail}</p></article>
                        ))}
                      </div>
                    </section>

                    {evidence.gaps.length > 0 && (
                      <section aria-labelledby="gaps-title">
                        <div className="drawer-section-title"><span>04</span><h3 id="gaps-title">Known gaps</h3></div>
                        {evidence.gaps.map((gap) => (
                          <article className="evidence-gap" key={gap.code}><code>{gap.code}</code><strong>{gap.summary}</strong><p>{gap.impact}</p></article>
                        ))}
                      </section>
                    )}

                    <section className="digest-block" aria-labelledby="digest-title">
                      <div className="drawer-section-title"><span>05</span><h3 id="digest-title">Bundle digest</h3></div>
                      <code>{evidence.bundleDigest}</code>
                      <p>Full SHA-256 of the safe evidence bundle. This is not a player identifier.</p>
                    </section>
                  </div>
                )}
              </m.section>
            </Dialog.Content>
          </LazyMotion>
        </MotionConfig>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

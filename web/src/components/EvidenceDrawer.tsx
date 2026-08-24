import * as Dialog from "@radix-ui/react-dialog"
import { LazyMotion, MotionConfig, domAnimation, m } from "motion/react"

import type {
  WorkbenchEvidence,
  WorkbenchEvidenceSource,
  WorkbenchRun,
  WorkbenchTaskEvent,
} from "../workbench/model"
import { useI18n } from "../i18n/ProductLocaleProvider"
import type { MessageKey } from "../i18n/locale"
import {
  eventMessageKeys,
  publicationMessageKeys,
  taskStatusMessageKeys,
} from "../i18n/productCopy"
import { Glyph } from "./VisualGlyphs"

const verdictKeys: Readonly<Record<WorkbenchEvidence["disposition"], MessageKey>> = {
  complete: "evidence.verdict.complete",
  degraded: "evidence.verdict.degraded",
  rejected: "evidence.verdict.rejected",
}

const dispositionKeys: Readonly<Record<WorkbenchEvidence["disposition"], MessageKey>> = {
  complete: "evidence.disposition.complete",
  degraded: "evidence.disposition.degraded",
  rejected: "evidence.disposition.rejected",
}

const confidenceKeys: Readonly<Record<WorkbenchEvidence["confidence"], MessageKey>> = {
  high: "evidence.confidence.high",
  medium: "evidence.confidence.medium",
  low: "evidence.confidence.low",
  unknown: "evidence.confidence.unknown",
}

const sourceNameKeys: Readonly<Record<WorkbenchEvidenceSource["sourceKind"], MessageKey>> = {
  riot_official: "evidence.source.riot_official",
  data_dragon: "evidence.source.data_dragon",
  riot_patch: "evidence.source.riot_patch",
  opgg: "evidence.source.opgg",
}

const sourceStatusKeys: Readonly<Record<WorkbenchEvidenceSource["status"], MessageKey>> = {
  verified: "evidence.status.verified",
  partial: "evidence.status.partial",
  unavailable: "evidence.status.unavailable",
}

const freshnessKeys: Readonly<Record<WorkbenchEvidenceSource["freshness"], MessageKey>> = {
  current: "evidence.freshness.current",
  stale: "evidence.freshness.stale",
  unknown: "evidence.freshness.unknown",
  expired: "evidence.freshness.expired",
}

const joinLabelKeys: Readonly<Record<WorkbenchEvidence["joins"][number]["labelCode"], MessageKey>> = {
  review_patch_official_patch: "evidence.join.review_patch_official_patch",
  champion_current_meta: "evidence.join.champion_current_meta",
  champion_position: "evidence.join.champion_position",
}

const joinStatusKeys: Readonly<Record<WorkbenchEvidence["joins"][number]["status"], MessageKey>> = {
  joined: "evidence.join.status.joined",
  joined_partial: "evidence.join.status.joined_partial",
  unjoined: "evidence.join.status.unjoined",
  stale: "evidence.join.status.stale",
  conflict: "evidence.join.status.conflict",
}

const positionKeys = {
  top: "position.top",
  mid: "position.mid",
  jungle: "position.jungle",
  adc: "position.adc",
  support: "position.support",
} as const

const knownGapKeys: Readonly<Record<string, { readonly title: MessageKey; readonly body: MessageKey }>> = {
  data_dragon_missing: {
    title: "evidence.gap.data_dragon_missing.title",
    body: "evidence.gap.data_dragon_missing.body",
  },
  official_patch_missing: {
    title: "evidence.gap.official_patch_missing.title",
    body: "evidence.gap.official_patch_missing.body",
  },
  opgg_meta_missing: {
    title: "evidence.gap.opgg_meta_missing.title",
    body: "evidence.gap.opgg_meta_missing.body",
  },
}

interface EvidenceDrawerProps {
  readonly evidence: WorkbenchEvidence | undefined
  readonly events: readonly WorkbenchTaskEvent[]
  readonly run: WorkbenchRun | undefined
}

export function EvidenceDrawer({ evidence, events, run }: EvidenceDrawerProps) {
  const { formatNumber, formatUtcTime, t } = useI18n()

  function sourceDetail(source: WorkbenchEvidenceSource): string {
    if (source.sourceKind === "riot_official") {
      if (source.matchCount !== undefined && source.matchCount > 0) {
        return t("evidence.source.riot_count", { count: formatNumber(source.matchCount) })
      }
      return source.status === "unavailable"
        ? t("evidence.source.riot_missing")
        : t("evidence.source.structured_available")
    }
    if (source.sourceKind === "data_dragon") {
      if (source.version !== undefined) return t("evidence.source.data_dragon_version", { version: source.version })
      return source.status === "unavailable"
        ? t("evidence.source.data_dragon_missing")
        : t("evidence.source.structured_available")
    }
    if (source.sourceKind === "riot_patch") {
      if (source.patchVersion !== undefined) return t("evidence.source.patch_version", { version: source.patchVersion })
      return source.status === "unavailable"
        ? t("evidence.source.patch_missing")
        : t("evidence.source.structured_available")
    }
    if (source.evidenceCount !== undefined && source.evidenceCount > 0) {
      return t("evidence.source.opgg_count", { count: formatNumber(source.evidenceCount) })
    }
    return source.status === "unavailable"
      ? t("evidence.source.opgg_missing")
      : t("evidence.source.structured_available")
  }

  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button className="evidence-launch" id="evidence" type="button" disabled={evidence === undefined}>
          <span className="evidence-launch__icon"><Glyph name="evidence" /></span>
          <span><small>{t("evidence.launch_kicker")}</small><strong>{t("evidence.open")}</strong></span>
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
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              >
                <div className="evidence-drawer__energy" aria-hidden="true" />
                <header className="evidence-drawer__header">
                  <div>
                    <p className="eyebrow">{t("evidence.provenance_revision", { revision: evidence === undefined ? "—" : formatNumber(evidence.revision) })}</p>
                    <Dialog.Title>{t("evidence.title")}</Dialog.Title>
                    <Dialog.Description id="evidence-description">
                      {t("evidence.description")}
                    </Dialog.Description>
                  </div>
                  <Dialog.Close asChild>
                    <button className="icon-button" type="button" aria-label={t("evidence.close")}><Glyph name="close" /></button>
                  </Dialog.Close>
                </header>

                {evidence !== undefined && (
                  <div className="evidence-drawer__body">
                    <section className={`evidence-verdict evidence-verdict--${evidence.disposition}`}>
                      <span><Glyph name={evidence.disposition === "complete" ? "check" : "limit"} /></span>
                      <div><small>{t(dispositionKeys[evidence.disposition])} · {t(freshnessKeys[evidence.freshness])}</small><strong>{t(verdictKeys[evidence.disposition])}</strong></div>
                      <b>{t("evidence.confidence", { confidence: t(confidenceKeys[evidence.confidence]) })}</b>
                    </section>

                    <section aria-labelledby="sources-title">
                      <div className="drawer-section-title"><span>01</span><h3 id="sources-title">{t("evidence.section.sources")}</h3></div>
                      <div className="source-stack">
                        {evidence.sources.map((source) => (
                          <article key={source.sourceKind}>
                            <span className={`source-node source-node--${source.status}`} />
                            <div><strong>{t(sourceNameKeys[source.sourceKind])}</strong><p>{sourceDetail(source)}</p></div>
                            <small>{t(sourceStatusKeys[source.status])} · {t(freshnessKeys[source.freshness])}</small>
                          </article>
                        ))}
                      </div>
                    </section>

                    <section aria-labelledby="run-path-title">
                      <div className="drawer-section-title"><span>02</span><h3 id="run-path-title">{t("evidence.section.run_path")}</h3></div>
                      <div className="run-path">
                        {events.map((event, index) => (
                          <article className="run-path__event" key={`${event.cursor}-${event.eventKind}`}>
                            <span className={`run-path__node${index === events.length - 1 ? " run-path__node--terminal" : ""}`} aria-hidden="true" />
                            <div>
                              <strong>{t(eventMessageKeys[event.eventKind])}</strong>
                              <small>{t(taskStatusMessageKeys[event.statusAfter])}</small>
                            </div>
                            <time dateTime={event.occurredAt}>
                              {formatUtcTime(event.occurredAt)}Z
                            </time>
                          </article>
                        ))}
                      </div>
                      {run !== undefined && (
                        <dl className="run-summary">
                          <div><dt>{t("evidence.runtime")}</dt><dd>{run.runtimeStatus === "completed" ? t("runtime.completed") : t("runtime.failed")}</dd></div>
                          <div><dt>{t("evidence.publication")}</dt><dd>{run.publicationStatus === undefined ? t("common.pending") : t(publicationMessageKeys[run.publicationStatus])}</dd></div>
                          <div><dt>{t("evidence.elapsed")}</dt><dd>{run.elapsedMs === undefined ? t("common.pending") : t("evidence.seconds", { value: formatNumber(run.elapsedMs / 1000, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) })}</dd></div>
                        </dl>
                      )}
                      <p className="run-path__boundary">{t("evidence.lifecycle_boundary")}</p>
                    </section>

                    <section aria-labelledby="joins-title">
                      <div className="drawer-section-title"><span>03</span><h3 id="joins-title">{t("evidence.section.joins")}</h3></div>
                      <div className="join-grid">
                        {evidence.joins.map((join, index) => {
                          const label = join.labelCode === "champion_position"
                            ? t(joinLabelKeys[join.labelCode], {
                                champion: join.championName ?? "—",
                                position: join.position === undefined ? "—" : t(positionKeys[join.position]),
                              })
                            : t(joinLabelKeys[join.labelCode])
                          const sources = join.sourcesPresent.map((source) => t(sourceNameKeys[source])).join(", ")
                          return (
                            <article key={`${join.labelCode}-${join.championName ?? index}`}>
                              <small>{t(joinStatusKeys[join.status])}</small>
                              <strong>{label}</strong>
                              <p>{sources === "" ? t("evidence.join.no_sources") : t("evidence.join.sources", { sources })}</p>
                            </article>
                          )
                        })}
                      </div>
                    </section>

                    {evidence.gaps.length > 0 && (
                      <section aria-labelledby="gaps-title">
                        <div className="drawer-section-title"><span>04</span><h3 id="gaps-title">{t("evidence.section.gaps")}</h3></div>
                        {evidence.gaps.map((gap) => {
                          const known = knownGapKeys[gap.code]
                          const source = gap.sourceKind === undefined ? t("common.unknown") : t(sourceNameKeys[gap.sourceKind])
                          return (
                            <article className="evidence-gap" key={gap.code}>
                              <strong>{known === undefined ? t("evidence.gap.generic.title") : t(known.title)}</strong>
                              <p>{known === undefined ? t("evidence.gap.generic.body", { source }) : t(known.body)}</p>
                            </article>
                          )
                        })}
                      </section>
                    )}

                    <section className="digest-block" aria-labelledby="digest-title">
                      <div className="drawer-section-title"><span>05</span><h3 id="digest-title">{t("evidence.section.digest")}</h3></div>
                      <code translate="no">{evidence.bundleDigest}</code>
                      <p>{t("evidence.digest_boundary")}</p>
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

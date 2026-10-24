import type { RuntimeUsageWire } from "../api/wire"
import { useI18n } from "../i18n/ProductLocaleProvider"

export function RunUsagePanel({ usage }: { readonly usage: RuntimeUsageWire | null }) {
  const { t, formatNumber } = useI18n()
  const totalsKnown = usage?.token_observation === "complete" || usage?.token_observation === "not_applicable"
  const tokens = totalsKnown && usage !== null
    && usage.input_tokens !== null && usage.output_tokens !== null
    ? formatNumber(usage.input_tokens + usage.output_tokens) : t("usage.unknown")
  return (
    <section className="source-summary panel" aria-labelledby="run-usage-title">
      <h3 id="run-usage-title">{t("usage.title")}</h3>
      {usage === null ? <p>{t("usage.unavailable")}</p> : <>
        <dl className="run-summary">
          <div><dt>{t("usage.calls")}</dt><dd>{formatNumber(usage.provider_calls_attempted)}</dd></div>
          <div><dt>{t("usage.tokens")}</dt><dd>{tokens}</dd></div>
          <div><dt>{t("usage.estimate")}</dt><dd>{usage.cost_observation === "complete" && usage.cost !== null && usage.currency !== null
            ? `${usage.cost} ${usage.currency}` : t("usage.unknown")}</dd></div>
        </dl>
        {!totalsKnown && <p>{t("usage.observed", {
          tokens: formatNumber(usage.observed_input_tokens + usage.observed_output_tokens),
        })}</p>}
        <p>{t("usage.boundary")}</p>
      </>}
    </section>
  )
}

import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { RuntimeUsageWire } from "../api/wire"
import { decodeRunUsage } from "../api/decoders"
import { ProductLocaleProvider } from "../i18n/ProductLocaleProvider"
import { RunUsagePanel } from "./RunUsagePanel"

const usage: RuntimeUsageWire = {
  provider_calls_attempted: 3, provider_responses_observed: 2,
  observed_input_tokens: 100, observed_output_tokens: 40,
  input_tokens: null, output_tokens: null, token_observation: "partial",
  tool_calls: 0, tool_attempts: 0, tool_latency_ms: 0,
  cost: "0.01", currency: "CNY", pricing_profile_id: "estimate", pricing_profile_version: "1",
  cost_observation: "partial",
}
const show = (value: RuntimeUsageWire | null) => render(
  <ProductLocaleProvider store={{ read: () => "zh-CN", write: () => undefined }}>
    <RunUsagePanel usage={value} />
  </ProductLocaleProvider>,
)

describe("terminal task usage", () => {
  it("keeps missing records unknown instead of free", () => {
    show(null)
    expect(screen.getByText("暂无可信用量记录，不代表没有消耗。")).toBeInTheDocument()
    expect(screen.queryByText("0")).not.toBeInTheDocument()
  })
  it("does not show partial tokens or partial cost as totals", () => {
    show(usage)
    expect(screen.getAllByText("未知")).toHaveLength(2)
    expect(screen.getByText("已记录 140 Token，总量尚不完整。")).toBeInTheDocument()
    expect(screen.queryByText("0.01 CNY")).not.toBeInTheDocument()
  })
  it("shows complete observed totals with the estimate boundary", () => {
    show({ ...usage, provider_responses_observed: 3, input_tokens: 100, output_tokens: 40, token_observation: "complete", cost_observation: "complete" })
    expect(screen.getByText("140")).toBeInTheDocument()
    expect(screen.getByText("0.01 CNY")).toBeInTheDocument()
    expect(screen.getByText(/估算费用不等于供应商账单/)).toBeInTheDocument()
  })
  it("keeps verified zero distinct from missing observations", () => {
    show({ ...usage, provider_calls_attempted: 0, provider_responses_observed: 0,
      observed_input_tokens: 0, observed_output_tokens: 0, input_tokens: 0, output_tokens: 0,
      token_observation: "not_applicable", cost: "0", cost_observation: "complete" })
    expect(screen.getAllByText("0")).toHaveLength(2)
    expect(screen.queryByText(/总量尚不完整/)).not.toBeInTheDocument()
  })
  it("rejects wrong run, in-flight status and unexpected content", () => {
    const value = { schema_version: "1.0", run_id: "review_usage_1", task_status: "cancelled", usage }
    expect(decodeRunUsage(value, value.run_id).usage?.input_tokens).toBeNull()
    expect(() => decodeRunUsage(value, "other")).toThrow()
    expect(() => decodeRunUsage({ ...value, task_status: "running" }, value.run_id)).toThrow()
    expect(() => decodeRunUsage({ ...value, report: "unpublished" }, value.run_id)).toThrow()
  })
})

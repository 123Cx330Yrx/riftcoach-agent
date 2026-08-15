# 5D-7 DeepSeek 资源校准失败采用决策

## 1. 这一步解决什么问题

DeepSeek V4 Pro 的低层 Adapter 协议曾以 3/3 次真实调用通过，但领域评测没有得到可用的
质量结论。V2 因旧 Token 合同不可达而停止；随后专门设计的 V3 development Usage
校准又在第 1 个请求后停止：请求已经发送，但响应没有形成 RiftCoach 统一的
`ChatResponse`，所以 8 个阶段只完成 0 个 Usage observation。

此时不能继续问“模型回答得好不好”，因为报告、工具、RAG 和 Evaluation 都没有开始。
真正要决定的是：是否值得为了查明这个适配失败，再建立一版新的真实诊断实验。

## 2. 先区分三个事实层级

### 已知事实

- 当前 calibration 只发送 1 次请求，后 7 次按首错停止未发送；
- 结果只保留 `provider_response_invalid`，实际 Token、延迟和费用未知；
- DeepSeek Adapter 本身能产生更细且不含正文的安全错误码，例如
  `unexpected_reasoning_content`、`resolved_model_mismatch`、
  `incomplete_chat_response`、`invalid_finish_reason` 和
  `invalid_tool_call_response`；
- `classify_provider_error()` 会把上述大部分 `ProviderResponseError.code` 压缩成同一个
  `provider_response_invalid`，因此细节是在实验结果层丢失，不是 Adapter 从未生成；
- 当前不可变结果不能修改、覆盖或补跑。

### 可以做出的结论

- 当前 V3 资源合同无法推导，也不能创建 V3 held-out；
- 当前 DeepSeek 候选没有取得领域质量准入；
- 未来真实 Provider 门需要保留安全、有限、无正文的错误 provenance。

### 不能做出的结论

- 不能断言 DeepSeek 质量差；
- 不能断言具体根因是 reasoning、model ID、finish reason、ToolCall 或 Usage；
- 不能把账本 0 token / `$0` 解释为厂商实际未计费；
- 不能因为低层协议通过就把 DeepSeek 设为产品默认模型。

## 3. 底层 Agent 工程原理

Provider Adapter 是“厂商协议”与“项目统一协议”的翻译层。它的失败至少要分成两层：

```text
产品/实验分类：provider_response_invalid
        |
        +-- 安全适配细节：invalid_finish_reason 等
```

第一层适合跨厂商统计，第二层用于判断下一步应该修什么。只保存第一层虽然安全，却会让
不同错误看起来完全相同；保存原始响应又会泄露 Prompt、reasoning、工具内容或用户数据。
正确的折中不是保存原文，而是透传 Adapter 已经产生的、经过允许列表校验的安全错误码。

这与 5E 的完整 Trace 有区别：本轮只决定未来 Provider 采用门必须携带哪种最小失败
provenance，不提前实现统一事件流、Tracing 或生产监控。

## 4. 方案比较

### 方案 A：关闭当前 DeepSeek V3，保留安全可观测性为未来真实门前置条件

当前 V3 不再创建 budget 或 held-out，DeepSeek 不获得领域/产品准入；已通过的低层
Adapter 协议和现有代码保留。任何未来 Provider 真实门必须先在离线 TDD 中证明：

- 公开结果保留稳定的高层失败分类；
- 另有可空的、允许列表约束的 `provider_error_code`；
- 不保存响应、reasoning、Prompt、原始 request ID 或异常正文；
- 未知错误仍 fail closed，不用自由文本猜测；
- 旧结果保持原样可复读。

这是推荐方案。它停止对当前 DeepSeek 考卷继续投入，同时把真实 Bad Case 转化为下一候选
可以复用的工程约束。

### 方案 B：立即建立 DeepSeek V4 诊断门并再次调用

优点是可能定位本次根因。缺点是需要新实验 ID、结果路径、预算、公开 CI 和再次授权；
即使找到根因，仍没有领域质量证据，还可能在修复后遇到下一个问题。它容易把项目变成
围绕单一 Provider 追绿的连续实验，因此当前拒绝。

### 方案 C：保持无限搁置

它不增加成本，也不给错误结论，但没有明确重新采用条件，会让 5D-7 长期停留在“以后
也许再试”。当前拒绝。

## 5. 决策

采用方案 A：

1. 当前 DeepSeek V3 资源校准与领域采用尝试正式关闭；
2. 不生成 V3 budget，不创建 V3 held-out，不修改或重跑 V1/V2/calibration；
3. DeepSeek Adapter 和已通过的最小 structured/tool 协议继续保留，但不得表述为领域、
   产品默认模型或自动路由准入；
4. 模型质量结论保持 `unknown`；
5. 将安全细分 Provider 错误 provenance 设为后续任何真实 Provider 门的前置条件；
6. 本轮只记录决策，不实现该字段，不读取 Key，不调用 Provider；
7. 按既定 ADR-0023，下一检查点是 `G53-0`：只审计 GLM-5.3 普通 API、正式模型 ID、
   endpoint、thinking 与工具/结构化合同是否可用。

## 6. 未来错误数据流

本轮不改代码，但冻结后续应达到的最小控制流：

```text
Provider SDK response/error
        |
        v
Provider Adapter
  -> ProviderError(type, safe code)
        |
        v
实验分类器
  -> failure_code: 跨厂商稳定分类
  -> provider_error_code: 允许列表内的安全细节或 null
        |
        v
不可变公开结果
  -> 无 Prompt / response / reasoning / raw exception / raw request ID
```

如果 `provider_error_code` 不在该 Adapter 的冻结允许列表中，结果只能记录
`provider_error_unknown` 或 null，不能把任意 SDK 文本带入公开文件。

## 7. 非功能要求

- **安全**：只允许枚举式安全码；禁止原始响应、异常、URL、header、Key 和正文落盘；
- **可靠性**：错误细分失败时仍保留高层分类并 fail closed；
- **可维护性**：采用 Provider-neutral 字段，不为 DeepSeek 复制专用控制面；
- **可追溯性**：结果绑定代码、公开 CI、实验和请求身份；旧结果字节不变；
- **成本**：本决策外部调用为 0；任何新真实门仍需独立预算和用户确认；
- **性能**：不增加线上调用或重试；仅增加常量级元数据；
- **诚实性**：低层协议、领域质量、Usage 校准和产品采用继续分开表述。

## 8. 怎样验证这个决策不是拍脑袋

本轮验证现有事实，而不是伪造新实验：

1. 解析不可变结果，确认 1 external call、0 normalized responses、无 budget/held-out；
2. 运行 DeepSeek Adapter 失败测试，证明细分 `ProviderError.code` 已存在且不依赖原文；
3. 运行 calibration 结果/裁决测试，证明旧结果保持不可变、计费保持 unknown；
4. 运行治理检查，证明唯一下一步仍在 5D-7，且没有跳到 5E；
5. 运行完整回归和公开 exact-SHA CI，证明纯决策没有破坏既有 Agent/RAG/Harness。

## 9. 当前限制与后续

关闭的是“当前 DeepSeek V3 领域采用尝试”，不是删除 DeepSeek Provider，也不是宣布未来
永不使用 DeepSeek。未来只有出现新的产品需求、更新的模型版本或同任务对照价值，并且
使用全新 development/held-out 身份、先补安全 provenance、再经过新 ADR 和预算门时，
才可重新评估。

`G53-0` 只是可用性与合同审计。若 GLM-5.3 普通 API 尚不可用，应记录为 deferred，而
不是改用 Coding Plan endpoint、回退到旧考卷或立即增加第三家模型。

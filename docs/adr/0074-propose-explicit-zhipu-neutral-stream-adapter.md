# ADR-0074：候选级显式智谱→中立流适配接缝（本地实现记录）

- 日期：2026-09-01
- 状态：`implemented-local / public-ci-pending`
- 范围：Stage 8 / 8E；GLM-5.3-Flash 候选 streaming 接缝
- 当前证据：工作树本地实现与聚焦测试 `20 passed`；尚无同 SHA 公共 CI 证据

## 背景与历史设计

RQ-192 冻结了不依赖 SDK 的 `ProviderStreamEvent` 与
`ProviderStreamAssembler`。RQ-193 又用测试内 fake translator 证明代表性的
智谱 OpenAI-compatible 分块可以落到该合同，并在提交
`8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的公共 CI 中通过。最初的 RQ-194
草案曾使用 `<zhipu-neutral-stream-adapter>`、`<ZhipuNeutralStreamAdapter>` 等
占位符，先等待 port 评审；本记录保留那一阶段的约束，但现在以实际本地实现为准。

## 实际实现决策

1. `app/providers/zhipu_stream_adapter.py` 提供真实的
   `ZhipuStreamAdapter`。它实现现有独立的 `ProviderStreamAdapter` 协议，
   但不是 `LLMProvider`，也不修改能力协商。
2. `ZhipuProvider.stream_adapter(*, tool_stream: bool = False)` 是唯一显式工厂。
   每个 adapter 实例在创建时绑定 `tool_stream`；调用方必须主动取得实例，
   默认组合根、AgentLoop 和同步 `chat()` 不会自动选择它。
3. `stream_events(request)` 只把一个 Zhipu 原始流翻译为
   `ProviderStreamEvent`；`assemble(request, *, max_output_tokens=None,
   require_request_identity=True)` 只打开一次流，交给
   `ProviderStreamAssembler`，最后返回 `StreamAssemblyResult`。
4. Provider 私有 port `_open_stream_for_adapter(request, *, tool_stream)`
   负责一次 SDK stream open、请求校验、工具别名编码和 runtime profile 约束；
   适配器负责字段形状/身份翻译，中立装配器负责终态和隐私合同。

## 预算、身份与关闭边界

- 输出额度必须为 `1..8192` 的整数。已绑定的 runtime profile（若有）提供
  trusted `max_output_tokens`；显式 cap、`ChatRequest.max_tokens` 与该上限取最小值，
  不能通过直接构造适配器绕过 profile，也不能用更大的显式 cap 越界。相同 cap 同时
  传给供应商请求和中立装配器，避免供应商响应超支。
- Provider 身份必须是 `zhipu`，model 是安全标识；每个事件的 model 必须与
  adapter 绑定值一致。默认 `require_request_identity=True`，事件只携带请求 ID 的
  SHA-256 摘要，响应和 Trace 不保存原始 request ID。
- 一次 `assemble()` 只允许一次 stream open。只有正常迭代器 EOF 才能
  `mark_exhausted()`，随后由装配器要求 terminal 与有效 Usage 再 `finalize()`。
  迭代器异常、取消、翻译错误或供应商错误均走 `abort("stream_aborted")` 或
  已有 typed provider error；不能把异常误认成 EOF，也不能隐式 retry/recovery。
- 迭代器和供应商流在 `finally` 中关闭；正常 EOF 时 close 失败会变成安全的
  `zhipu_stream_close`。Trace、异常文本和默认 repr 均 body-free，不包含 Prompt、
  正文、reasoning、工具参数、SDK 对象、Key 或原始 request ID。

## 评审与下一门

`tests/test_zhipu_stream_adapter.py` 以 fake SDK/client 覆盖文本与 reasoning、工具
别名与分片、runtime cap、请求 cap、model/identity、坏 chunk、typed iterator error、
关闭失败、消费者提前关闭和 capability 不变，聚焦结果为 `20 passed`。这些是本地
证据，不等于公共 CI 或生产准入。下一门是把包含实现与测试的同一干净提交送入
exact-SHA 公共 CI；记录真实 run/job 后，才另行评审是否允许候选 runtime 接线。

## 明确不做的事

本 ADR 不注册 recovery，不打开 `capabilities.streaming`（仍为 `False`），不改变
严格 Flash v1 的 2048 输出上限与零额外调用，不接入默认模型、AgentLoop、ToolRuntime、
统一 Runtime Trace、产品预算账本、Portal、Account、Workbench、Auth、路由或
`production_media`。不调用真实 API、不读取 Key、不执行 G53-7/黄金切片，也不宣称
streaming、领域采用、公共部署或 Stage 8/8E 完成。

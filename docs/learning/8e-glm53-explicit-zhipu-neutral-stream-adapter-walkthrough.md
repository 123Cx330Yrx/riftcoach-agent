# 8E 学习记录：候选级显式智谱→中立流适配接缝（RQ-194）

状态：`completed-local / public-ci-pending`。本 walkthrough 记录当前本地实现；
它不是公共 CI 或生产准入证明。

## 1. 问题与原则

RQ-193 的 fake conformance 证明了字段翻译样例，但测试夹具不是可调用的 provider
port。RQ-194 把“供应商字段翻译”“完整流装配”和“产品是否采用 streaming”拆开：
provider adapter 只负责形状与字段，中立 assembler 负责终态、Usage、预算和隐私，
运行时采用仍需另一个明确决策。

## 2. 历史设计到实际代码

早期设计使用 `<zhipu-neutral-stream-adapter>`、`<ZhipuNeutralStreamAdapter>` 和
`<stream_candidate(request)>` 占位符；评审后已落为以下真实 API：

- `app/providers/zhipu_stream_adapter.py`：`ZhipuStreamAdapter`；实现独立的
  `ProviderStreamAdapter` 协议，不是 `LLMProvider`。
- `ZhipuProvider.stream_adapter(*, tool_stream: bool = False)`：调用方显式取得
  adapter；`tool_stream` 在实例创建时绑定，不能在一条流中途改变。
- `ZhipuStreamAdapter.stream_events(request)`：返回单条 Zhipu 原始流的
  `ProviderStreamEvent` 迭代器。
- `ZhipuStreamAdapter.assemble(request, *, max_output_tokens=None,
  require_request_identity=True)`：消费一条流并返回 `StreamAssemblyResult`。
- `ZhipuProvider._open_stream_for_adapter(request, *, tool_stream)`：私有 provider
  port；真正的 SDK open、请求校验、thinking/runtime profile 应用和工具 alias 编码
  集中在这里，旧同步路径仍由原有 API 使用。

## 3. 数据与控制流

```text
显式调用 provider.stream_adapter()
  → assemble(ChatRequest)
  → _open_stream_for_adapter()（一次 SDK stream open）
  → 校验 OpenAI-compatible chunk、zhipu/model 身份、工具 alias、Usage
  → ProviderStreamEvent
  → ProviderStreamAssembler.accept()
  → 正常 EOF 后 mark_exhausted()
  → terminal + 有效 Usage → StreamAssemblyResult + body-free Trace
```

事件里的 request ID 只计算 SHA-256；每个 event 的 model 必须与 adapter 绑定 model
一致。工具别名（例如 `knowledge_search`）在 provider 层解码为内部名称，参数分片
交给中立装配器按连续 index 组装。

## 4. 预算、关闭和失败

- 输出上限为 `1..8192`；若 provider 绑定注册 runtime profile，则默认使用其
  `max_output_tokens`（当前 Flash profile 为 2048）。显式 cap 和请求 cap 只能取更小值，
  同时传给供应商 payload 与 assembler，不能越过 trusted cap。
- `require_request_identity` 默认开启；缺少或冲突的身份由中立合同拒绝，原始
  request ID 不进入 response/Trace。
- 只有迭代器正常 EOF 才能 `mark_exhausted()`；SDK/迭代器异常、取消、翻译错误或
  close 失败会安全终止（`abort("stream_aborted")` 或 typed `ProviderError`），不能
  把异常误当 EOF，不能自动 retry、recovery 或执行 ToolRuntime。
- iterator/raw stream 在 `finally` 中关闭；Trace、错误文本和默认 repr 不包含 Prompt、
  正文、reasoning、工具参数、Key、SDK 对象或原始 request ID。

## 5. 本地证据

`tests/test_zhipu_stream_adapter.py` 使用 fake SDK/client 覆盖：文本与 reasoning、
工具 alias/参数分片、runtime/request cap、model mismatch、映射 chunk、坏 chunk、
typed iterator error、消费者提前关闭、close failure、thinking profile、tool_stream
约束和 capability 不变。聚焦命令结果为 `20 passed`。

这只是当前工作树的本地证据；实现尚未取得同 SHA 公共 CI，因此不能写成公共可复现、
生产 streaming 或领域准入。

## 6. 明确未接线边界

`capabilities.streaming` 仍为 `False`；严格 Flash v1 仍为 2048 输出上限和零额外调用。
默认模型、AgentLoop、ToolRuntime、统一 Runtime Trace、产品预算账本、Workbench、
Portal、Account、Auth、路由和 `production_media=0` 均未接入。没有 recovery 注册、
真实 API/Key I/O、G53-7 或黄金切片执行；8E 仍进行中，8F 尚未开始。

## 7. 下一门与面试表述

下一步是将实现与测试放入同一干净提交，运行 exact-SHA 公共 CI 并记录真实 run/job；
通过后还要单独评审候选 runtime 接线范围、预算/Trace/回退和失败门。

可以说：“我把智谱的 OpenAI-compatible 分块限制在显式 `ZhipuStreamAdapter`，
先归一化为中立事件，再由装配器以 EOF、terminal、Usage 和 body-free Trace 收口，
目前有 20 项 fake/local 测试，等待同 SHA 公共 CI。”

不能说：“我已经把智谱 streaming 接入生产 Agent 或打开了 streaming capability。”

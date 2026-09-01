# 8E：候选级显式智谱→中立流适配接缝（RQ-194 计划与本地实现）

## 状态与目标

状态：`implemented-public / candidate-only`。RQ-194 已把最初的设计草案落成
候选级、仅显式调用的本地 adapter；包含实现与测试的同一干净提交已取得
exact-SHA 公共 CI（提交 `a7580e861cd986c026040c7fcfcc3fa577737961` / Actions
`33496237588` 三 job 全绿）。尚未注册候选或接入产品 runtime。

目标是把智谱 OpenAI-compatible 原始分块隔离在 provider 层：翻译为 RQ-192 的
中立事件，再由既有装配器负责完整终态、Usage、预算和隐私边界。

## 历史设计阶段（保留）

初稿曾使用 `app/providers/<zhipu-neutral-stream-adapter>.py`、
`<ZhipuNeutralStreamAdapter>` 和 `<stream_candidate(request)>` 占位符，先要求
评审调用者、身份、终止和撤出语义。实现后，真实名称以代码为准；占位符只保留
为设计演进记录，不再是当前 API。

## 当前代码地图与 API

- `app/providers/zhipu_stream_adapter.py`：`ZhipuStreamAdapter`，实现独立的
  `ProviderStreamAdapter` 协议；不是 `LLMProvider`。
- `ZhipuProvider.stream_adapter(*, tool_stream: bool = False)`：显式工厂；创建时
  固定是否发送工具流形状。
- `ZhipuStreamAdapter.stream_events(request)`：一次性返回规范化
  `ProviderStreamEvent` 迭代器；校验 OpenAI-compatible chunk、model、工具 alias、
  Usage 和安全错误码。
- `ZhipuStreamAdapter.assemble(request, *, max_output_tokens=None,
  require_request_identity=True)`：只打开一次底层流，交给
  `ProviderStreamAssembler`，返回 `StreamAssemblyResult`（含 body-free Trace）。
- `ZhipuProvider._open_stream_for_adapter(request, *, tool_stream)`：私有 provider
  port，负责请求校验、thinking/runtime profile 绑定、工具编码和唯一 SDK stream open；
  不改变旧的同步 `chat()`/`chat_stream()` 调用方式。

## 给初学者的边界说明

- **问题**：测试 conformance 证明字段能翻译，不等于生产调用路径安全。适配器若
  同时负责终态、Usage、工具和重试，容易把首正文或半流误当完整回答。
- **原则**：provider adapter 只做形状/字段翻译；中立 assembler 负责状态机和
  fail-closed；是否采用 streaming 仍是独立的运行时决策。
- **本批已做**：实现显式工厂、单流翻译与装配、预算上限、身份摘要、关闭/异常
  处理和 fake fixture 测试。
- **本批未做**：不改默认模型或同步 `chat()`，不把 `capabilities.streaming` 改为
  true，不接 AgentLoop、Workbench、Portal、Account、Auth，不注册候选/recovery，
  不发真实 API。

## 数据与控制流

```text
调用方显式 provider.stream_adapter(tool_stream=...)
    ↓ 传入 ChatRequest；按 runtime/request/explicit cap 取最小输出上限
ZhipuProvider._open_stream_for_adapter()  （唯一一次 SDK stream open）
    ↓ 校验 chunk / model；request id 只做 SHA-256 摘要；工具名 alias 解码
ZhipuStreamAdapter.stream_events()
    ↓ ProviderStreamEvent
ProviderStreamAssembler.accept()
    ↓ 正常 EOF → mark_exhausted() → terminal + 有效 Usage
StreamAssemblyResult.response + body-free StreamAssemblyTrace
```

### 预算与身份

- `max_output_tokens` 只能是 `1..8192`；绑定 runtime profile 时默认 cap 取其
  `max_output_tokens`，显式 cap 和 `ChatRequest.max_tokens` 只能进一步收紧，不能越界。
- 同一个有效 cap 同时传给供应商 payload 和 assembler，避免供应商返回超过装配预算。
- adapter 只接受 `provider_name == "zhipu"`；model 是安全标识，每个 event model 必须
  与绑定模型一致。默认 `require_request_identity=True`，只保留 request ID SHA-256，
  不把原始 ID 放入 response/Trace。

### 关闭与失败

- 只有原始迭代器正常 EOF 才调用 `mark_exhausted()`；terminal 与有效 Usage 缺一不可。
- SDK/迭代器异常、取消、翻译错误会调用 assembler `abort("stream_aborted")`，或保留
  已有的 typed `ProviderError`；不能误当 EOF，也不能自动 retry、recovery 或执行工具。
- iterator 和原始 stream 在 `finally` 中关闭；正常 EOF 的 close 失败映射为安全
  `zhipu_stream_close`。
- chunk、异常和默认 repr 均 body-free：不保存 Prompt、正文、reasoning、工具参数、
  SDK 对象、Key 或原始 request ID。

## 本地验证与下一门

`tests/test_zhipu_stream_adapter.py` 使用 fake SDK/client 覆盖文本/reasoning、工具别名
与参数分片、runtime/request cap、model/identity、坏 chunk、typed iterator error、
消费者提前关闭、close 失败、thinking profile 和 capability 不变；聚焦结果为
`20 passed`。提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA Actions run
`33496237588` 已完成 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job；
下一门是独立评审候选 runtime 接线范围。

## 退出条件与未接线边界

公共 CI 通过只证明这条候选接缝可复现，不自动激活它。`capabilities.streaming` 仍为
`False`，严格 Flash v1 仍 2048/零额外调用；默认模型、AgentLoop、ToolRuntime、
统一 Runtime Trace、产品预算账本、Workbench、Portal、Account、Auth、路由和
`production_media=0` 均不变。8E 仍 `in_progress`，8F 尚未开始；G53-7、黄金切片、
真实 API、recovery、领域采用和生产部署必须另行授权与裁决。

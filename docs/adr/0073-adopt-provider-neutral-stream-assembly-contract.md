# ADR-0073：采用提供商无关的流式装配合同（候选）

- 日期：2026-09-01
- 状态：accepted-local / candidate-only
- 范围：Stage 8 / 8E；GLM-5.3-Flash 候选流式响应接缝

## 背景

RQ-191 证明了一条当前 Flash 请求形状的智谱原始流可以完整收到正文、终止
原因和 Usage，但原始 SDK 分块仍不是 RiftCoach 的统一响应。不同提供商可能把
reasoning、可见正文、工具参数、模型标识和 Usage 放在不同分块中；若由业务层
直接拼接，就容易把“首个正文”误当成可交付完成，或在截断后偷偷继续请求。

## 决策

新增纯离线 `app/providers/stream_adapter_contract.py`：

1. `ProviderStreamEvent` 是供应商翻译后的唯一输入形状，正文、reasoning、工具
   片段、终止原因、Usage、稳定 model、可选序号和请求身份摘要均显式建模；请求
   身份只允许小写 SHA-256，不接收原始 request ID。
2. `ProviderStreamAssembler` 是单次、无重试的状态机。只有收到合法终止原因、
   有效 Usage，并在底层迭代器真正 EOF 后调用 `mark_exhausted()`，才生成完整
   `ChatResponse`；终止后最多允许一个 Usage-only 尾块。`mark_exhausted()` 只对应
   正常 EOF；底层迭代器异常或取消必须先 `abort()`，不能把异常路径封口为成功流。
3. 工具片段按连续索引装配，参数必须是无重复键、有限数字、深度受限的 JSON
   对象；正文、reasoning、工具数量/参数和事件数量都有硬上限。终止、序号、
   model、请求身份或预算边界出错时，装配器毒化并 fail closed，不提供隐式恢复路。
4. `StreamAssemblyTrace` 只输出固定白名单的状态、计数、序号、模型和摘要哈希；
   不包含正文、reasoning、Prompt、工具参数、SDK 对象、Key 或原始 request ID。
   `ProviderStreamAdapter` 协议独立于现有同步 `LLMProvider`，不改变能力声明。

## 为什么先做离线接缝

当前 `ZhipuProvider.chat_stream()` 仍是供应商私有的完整消费表面，产品
`capabilities.streaming` 仍为 `False`。先冻结无 SDK 的装配合同，可以在无网络条件
下证明顺序、终态、Usage、工具和脱敏边界；直接把原始流接进 AgentLoop 会同时改变
调用语义、预算、Runtime Trace 和错误恢复边界，超出本批范围。

## 不做的事

本 ADR 不修改 `ChatRequest`/`ChatResponse`、`LLMProvider`、`ZhipuProvider`、
AgentLoop、ToolRuntime、Runtime Trace、默认模型、Workbench、Portal/Account、
Auth、路由或 `production_media`；不发真实请求、不注册候选、不打开 fresh recovery，
不宣称工具流、跨轮思考回放、领域采用、公共部署或 8E/8F 完成。

## 证据与后续闸门

`tests/test_stream_adapter_contract.py` 的聚焦测试为 `29 passed`，覆盖正常文本与
reasoning、终止/Usage/EOF、失败毒化与原子性、序号/身份冲突、并行工具片段、JSON
深度/数字/重复键、输出与输入上限和 Trace 脱敏。RQ-193 又以测试内 fake translator
完成智谱分块一致性对照（`13 passed`）；提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72`
的同 SHA 公共 CI run `33489903978` 三 job 全绿且 head_sha 精确匹配，并包含全部 Trace 脱敏断言。
公共证据完成后进入候选接线裁决。
正文只用 `strip()` 判断是否为空而不改写首尾空白；异常文本只保留安全错误码，底层迭代器异常/取消必须先 `abort()`。
在那些闸门完成前，严格 Flash v1 继续 2048 输出上限和零额外调用，候选保持未注册，
`production_media=0` 不变。

## RQ-193 证据增量：智谱 conformance（2026-09-01）

这次一致性测试不是新的生产适配器。`_FixtureZhipuStreamAdapter` 留在测试模块，使用
fake SDK 形状验证字段提取、工具别名解码、终态/EOF 与异常边界，再和旧的
`ZhipuProvider.chat_stream()` fake-client 结果对照。它证明的是“智谱形状可以被翻译到候选
合同”的可重复接缝，不证明真实供应商 streaming 已接入。

公共 CI 已对 `8bcbaa5` 完成。因此当前决策仍保持 `candidate-only`，下一项是候选
接线裁决（runtime 范围、预算/Trace/回退与失败处理），而非自动启用或领域准入。

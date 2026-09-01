# 8E：GLM-5.3-Flash 提供商无关流式装配合同

## 目标

RQ-191 已经证明一条当前形状的智谱原始流可以收到可见正文、终止原因和
Usage，但这仍是厂商传输观察。此计划只把“厂商适配器如何交出规范化事件、
如何在本地装配为一份完整 `ChatResponse`”冻结成可离线验证的接缝。

## 初学者说明

- **要解决的问题**：不同模型 SDK 的流式分块字段不同；如果把 SDK 对象直接
  传进 Agent，正文、思考、工具片段和 Usage 的边界会散落在业务代码里，容易
  把“首个正文”误当成“完整回答”。
- **核心原则**：厂商层先把每个分块翻译成统一事件，装配器再按状态机检查顺序，
  只有看到终止原因和有效 Usage 才生成完整回答；任何缺口都安全失败。
- **本批实现**：新增纯 Python 的 `ProviderStreamEvent`、工具片段类型、可选的
  `ProviderStreamAdapter` 协议、`ProviderStreamAssembler` 和脱敏 Trace。它们不
  调 SDK、不发网络请求、不重试、不改变 `LLMProvider`、AgentLoop、Runtime 或
  `capabilities.streaming=False`。
- **本批不实现**：不把智谱 `chat_stream()` 改成产品默认路径，不注册 GLM-5.3
  候选，不打开 fresh recovery，不改变严格 Flash v1 的 2048/零额外调用，也不
  宣称工具流、跨轮思考回放或生产成熟度。

## 数据与控制流

```text
厂商 SDK 分块
    ↓（未来的 provider-specific translator）
ProviderStreamEvent
    ↓ accept()：序号 / model / request identity / terminal / Usage 校验
ProviderStreamAssembler
    ↓ finalize()：正文、reasoning、工具 JSON 与预算边界
完整 ChatResponse + body-free StreamAssemblyTrace
```

事件中的请求身份只能是 SHA-256 摘要，Trace 不含正文、reasoning、工具参数、
Prompt、原始响应、API Key 或原始 request ID。终止后只允许 Usage-only 尾块；
超时、提前结束、缺少终止或缺少 Usage 均不能生成完整回答。调用方必须在底层
迭代器真正到达 EOF 后调用 `mark_exhausted()`；任何接收错误都会把装配器置为
不可继续使用的状态，不能借此偷偷打开第二次请求。若迭代器抛出异常或被取消，
调用方必须先用安全错误码调用 `abort()`，不得把异常路径误当作 EOF。

## 验证

`tests/test_stream_adapter_contract.py` 覆盖文本与 reasoning 装配、工具片段顺序
和 JSON 解码、终止/Usage 顺序、显式序号与请求身份冲突、预算/字符上限、提前中止、
失败原子性与毒化状态和 Trace 脱敏。相邻回归继续覆盖现有智谱适配器、响应完成策略、候选
恢复合同和 Runtime 生命周期事件流。

## 退出边界

本合同完成只代表离线装配接缝被冻结。下一步若要继续，仍需单独的厂商适配器
一致性测试、同一新实现 SHA 的公共 CI，以及重新审查是否值得进入候选运行时；
不得把本地合同通过写成领域准入、公共部署或 8E/8F 完成。

## 完成记录（2026-09-01）

- 新增 `app/providers/stream_adapter_contract.py` 与聚焦测试，当前聚焦结果为
  `29 passed`。
- `app/providers/__init__.py` 仅导出合同类型；未修改现有 Provider 的请求路径。
- 真实 API 调用、Key、Workbench、Portal、Account、Auth、默认模型和
  `production_media=0` 均未改变。

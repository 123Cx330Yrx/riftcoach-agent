# 8E 学习记录：提供商无关的流式装配接缝

## 1. 问题与原则

RQ-191 观察到的是智谱原始分块；它不能直接证明 RiftCoach 已经有通用流式
运行时。SDK 可能把 reasoning、可见正文、工具参数和 Usage 分散到不同分块，
所以必须把“收到首正文”和“完整终态可交付”分成两道门。统一事件、显式终态、
有效 Usage 和失败即停止，是这条接缝的核心原则。

## 2. 设计与代码地图

`app/providers/stream_adapter_contract.py` 定义：

- `ProviderStreamEvent`：厂商翻译后的正文/reasoning/工具片段、终止原因、Usage、
  model、序号和请求身份摘要；事件的 `repr` 不显示正文或工具参数；
- `StreamToolCallDelta`：按索引累积的函数工具片段；
- `ProviderStreamAssembler`：单次、无重试状态机；
- `StreamAssemblyResult` 与 `StreamAssemblyTrace`：内部完整回答和明确白名单的
  脱敏观测；
- `ProviderStreamAdapter`：可选协议，独立于同步 `LLMProvider`。

现有 `app/providers/zhipu.py::ZhipuProvider.chat_stream()` 保持不动；它仍是
智谱私有的整流表面，`capabilities.streaming` 仍为 `False`。

## 3. 数据与控制流

```text
分块 → 规范化事件 → accept() 状态检查 → EOF 后 mark_exhausted() → finalize()
                                     ├─ 完整 ChatResponse
                                     └─ 无正文 Trace
```

装配器允许终止分块后再出现一个 Usage-only 尾块；不允许终止后的正文、reasoning
或工具片段，也不允许重复 Usage。Usage 不能早于终止。工具索引必须从 0 连续，
参数必须是无重复键且深度受限的 JSON 对象。请求身份只保留 SHA-256，model 必须
在整条流中稳定；调用方必须在 EOF 后调用 `mark_exhausted()` 才能 `finalize()`。
任何接收错误都会毒化当前装配器，超时或迭代器异常/取消必须通过 `abort()` 安全地结束；
只有正常 EOF 才能调用 `mark_exhausted()`。

## 4. 验证结果

`tests/test_stream_adapter_contract.py` 当前 `29 passed`，覆盖：

- reasoning → 正文 → terminal + Usage-only 的正常文本流；
- 工具片段拼接、索引/JSON/元数据错误；
- 缺少终止、缺少 Usage、提前 Usage、终止后载荷/重复 Usage、冲突序号与身份；
- 输出额度、缓存 token 合法性、超时/中止、重复 finalize；
- EOF 封口、失败毒化、失败事件原子性，以及 Trace 不包含正文、reasoning、Prompt、工具参数、
  原始响应、Key 或原始 request ID。

相邻智谱 Provider、响应完成策略、候选恢复合同和 Runtime stream 回归仍通过。

## 5. 运行与复现

```powershell
D:\riftcoach-agent\.venv\Scripts\python.exe -m pytest `
  tests/test_stream_adapter_contract.py `
  tests/test_zhipu_provider.py `
  tests/test_response_completion_policy.py `
  tests/test_response_recovery_contract.py `
  tests/test_agent_runtime_stream.py -q
```

此合同是离线代码；不需要 Key、代理、外部服务或前台服务器。

## 6. 失败、安全与边界

装配器不做自动重试或恢复，也不把不完整流包装成成功回答。`abort()` 只记录
安全错误码；`finalize()` 在没有 EOF 封口、terminal、Usage 或可交付正文时
fail-closed。正文、reasoning、工具参数、事件数量和 JSON 深度均有硬上限，避免
未来把该接缝直接暴露给不受控输入。
Trace 使用显式白名单，避免把 SDK 对象或敏感字段沿链路传播。

这仍不等于工具流已进入 Agent、跨轮 reasoning replay 已验证、候选已注册、领域
黄金切片已通过或产品已具备生产成熟度。

## 7. 面试表述

可以说：“我把供应商流分块先翻译成无 SDK 的规范化事件，再用单次状态机装配；
只有终止原因和有效 Usage 同时出现才交付完整回答，Trace 只保留状态和摘要。”
不能说：“GLM-5.3 已经完成了产品级 token streaming。”

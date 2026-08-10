# 5D-6b P1 脱敏失败诊断设计

> 状态：提案，等待用户确认后才进入离线 TDD。本文不授权任何真实 Provider 调用，
> 不修改生产 `ZhipuProvider`，也不进入 5D-6b Task 4。

## 1. 现在究竟在测试什么

RiftCoach 当前有四层不同证据，不能混为一谈：

```text
内部合同测试
→ 真实厂商微探针
→ 生产 Provider Adapter
→ 真实 Skill / Agent / Harness 领域链路
```

第一层已经通过 Fake Provider 证明：RiftCoach 的消息、结构化 Schema、工具协议、预算、
AgentLoop 和 Harness 控制流在本地合同层可以组合。它不证明任何真实模型 API。

第二层是当前 5D-6b 的 P1-P5 微探针：

| Case | 检查对象 | 不检查什么 |
|---|---|---|
| P1 | 认证、端点、模型和标准文本返回面 | LoL 水平、报告质量 |
| P2/P3 | JSON mode 能否通过严格 Evaluation Schema | 复盘内容是否优秀 |
| P4 | 模型能否返回合法函数调用 | 本地 RAG 质量 |
| P5 | Tool Observation 回传后能否继续回答 | 完整 Skill/Harness |

上一轮只运行到 P1。API 返回了可解析的基础响应 envelope，但 `message.content` 没有满足
非空文本合同，所以探针停止。P2-P5 没有运行，生产 Adapter 和真实领域链路也没有开始。

## 2. 为什么现有错误码还不够

当前 `_run_case()` 在 validator 失败后只保存：

```text
error_code + latency
```

已经成功规范化的安全信息也被丢弃，包括：

- 实际返回模型；
- finish reason；
- prompt/completion token；
- request ID 的哈希；
- tool call 数量；
- `content` 是缺失、null、空字符串还是错误类型；
- 是否存在非空 `reasoning_content`。

因此 `invalid_text_response` 只说明最终文本入口不合格，不能进一步区分响应截断、字段
表面差异、思考内容与最终内容分离或其他响应形态。保存原始响应可以解决问题，但会把
Prompt、模型原文、服务端字段和误提交风险引入公开仓库。

## 3. 方案比较

### 方案 A：维持单一错误码

改动为零，隐私风险最低，但下一次调用仍可能得到同一个不可解释结果。拒绝。

### 方案 B：把完整原始响应写入本地忽略目录

诊断信息最多，但需要新的敏感数据生命周期、清理和误提交防护。当前只是一个基础文本
失败，不足以引入这套调试面。拒绝。

### 方案 C：白名单安全观察投影（推荐）

在响应返回后先生成不含文本的 `SafeResponseObservation`，再执行语义 validator。即使
validator 失败，也只把该安全观察投影到公开 case result：

```text
raw SDK response（仅瞬时存在）
→ whitelist observation（无正文）
→ semantic validator
→ passed 或 failed + 同一份安全元数据
```

它比方案 A 可诊断，又不承担方案 B 的原文持久化风险。

## 4. 安全观察合同

公开结果只新增以下机器字段：

```text
response_received: bool
content_state:
  not_observed | missing | null | empty | non_empty | non_string
reasoning_content_state:
  not_observed | missing | null | empty | non_empty | non_string
```

已有字段在响应 envelope 可规范化时继续保留：

```text
resolved_model
finish_reason
input_tokens / output_tokens
request_id_sha256
tool_call_count
```

严格禁止进入结果：

- `content` 与 `reasoning_content` 原文；
- 原始 request ID；
- API Key、请求 Prompt、原始异常；
- 未列入白名单的厂商扩展字段；
- 根据正文猜出的主题、情绪或安全原因。

状态字段只描述 Python 观察到的形状。例如 `reasoning_content_state=non_empty` 只表示
该字段存在非空值，不表示允许把思考过程当作最终回答，也不表示模型已经通过 P1。

## 5. 数据流与错误边界

```text
SDK 抛出认证/网络/HTTP 错误
→ response_received=false
→ content/reasoning state=not_observed
→ 现有安全错误码

SDK 返回响应
→ response_received=true
→ 白名单提取 model/finish/usage/request hash/字段状态
→ validator 检查 P1 精确哨兵
   ├─ 成功：passed + output SHA-256
   └─ 失败：failed + error_code + 安全观察；无输出摘要
```

`_ProbeFailure` 可以携带安全 observation，但不得携带 raw response 或原始文本。
`CapabilityProbeCaseResult` 继续要求 failed case 没有 `output_sha256`；只有响应层元数据可以
保留。skipped case 仍然没有调用指标，所有状态为 `not_observed`。

公开 Schema 升到 `1.1`。旧 `1.0` 结果保持字节不变；解析器接受旧版并为新增字段提供
保守默认值，新运行才写 `1.1`，不重写历史实验来伪造当时没有采集的证据。

## 6. 诊断重跑边界

离线实现通过后也不自动重跑原 P1-P5。若用户再次明确授权，只运行一个新的
`p1_diagnostic` scope：

```text
显式 --confirm-real-call
+ scope=p1_diagnostic
+ max_calls=1
→ 只运行 P1
→ 无论成功失败都停止
```

这样即使 P1 通过，也不会自动继续消耗 P2-P5。诊断结果只决定下一步：

- `content=non_empty` 且精确哨兵通过：另行决定是否重新授权完整 P1-P5；
- `content` 空而 `reasoning_content` 非空：记录为输出字段表面 Bad Case，不把 reasoning
  文本当最终答案；
- finish reason 或 usage 给出新的安全线索：据文档和 Adapter 合同设计下一实验；
- 仍无有效元数据：停止重复调用，重新检查端点、模型和 SDK 响应合同。

## 7. 离线 TDD 验收

实现前先写失败测试，至少证明：

1. `content=None` 时 failed case 保留 model、finish、usage、request hash 和 `null` 状态；
2. 非空 `reasoning_content` 只记录 `non_empty`，正文绝不进入 JSON；
3. 空字符串、字段缺失和非字符串具有不同枚举；
4. SDK 异常仍为 `response_received=false`，不伪造 usage；
5. skipped case 不含响应指标；
6. 旧 v1.0 结果仍可读取，新结果写 v1.1；
7. baseline-only CLI 未确认时不创建客户端，预算严格为 1；
8. 默认 pytest/CI 不进行真实网络调用；
9. 完整回归、compileall、密钥/运行数据检查和治理预检通过。

## 8. 本设计不做什么

- 不修改生产 `ZhipuProvider` capability flags；
- 不把 `reasoning_content` 当成正常回答；
- 不重新运行 GLM；
- 不测试 JSON、Tool Calling、RAG 或教练报告质量；
- 不选择 DeepSeek、Qwen 或其他第二 Provider；
- 不进入 5D-7 Prompt/Context 领域评测。

## 9. 面试中的准确表述

可以说：

> 我把真实模型准入拆成基础文本、结构化输出、Function Calling、Adapter 和领域链路
> 五类证据。首次基线返回空 content 后，没有盲目重试或记录原文，而是设计白名单响应
> 观察合同，在保留模型、finish reason、usage 和字段形状的同时对正文和 request ID
> 脱敏，并用单调用预算隔离诊断实验。

不能说：

> GLM 已经证明不支持 RiftCoach，或 GLM 已经通过 Tool Calling / Agent 准入。

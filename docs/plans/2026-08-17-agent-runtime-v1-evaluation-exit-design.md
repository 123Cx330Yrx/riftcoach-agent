# 5E-4：Runtime Evaluation & Exit Review 入口审计与验收矩阵

## 1. 这一步要回答什么

5E-1、5E-2、5E-3 分别建立了合同、同步运行和实时事件交付。5E-4 不再默认“再写一个
功能就算完成”，而是回答：

```text
我们是否能用代码、测试和公开 CI 证明 AgentRuntime V1 的承诺？
哪些承诺只是设计？哪些已在本地实现？哪些已公开验证？哪些仍明确不支持？
```

退出审查的产物是一张逐项可追溯矩阵，而不是一个漂亮的通过数字。

## 2. 初学者理解：为什么还需要 Exit Review

单元测试像检查汽车的刹车、轮胎和车灯；纵向测试像开一圈；Exit Review 则检查整辆车的
说明书、测试记录、故障边界和交付证据是否互相一致。

因此：

- `762 passed` 只能说明当前测试集通过，不能自动说明生产可用；
- 本地 `stream()` 通过不等于 API/SSE 已完成；
- Fake Provider + 真实本地 RAG 证明控制流，不证明 GLM/DeepSeek/Qwen 的领域质量；
- Trace 写入成功不等于有 durable event log 或崩溃恢复；
- 5E 关闭也不等于模型选型、Memory、MCP、前端或部署完成。

## 3. 入口范围

### 纳入

1. 5E-1 合同、Recorder、Usage completeness、Trace Store；
2. 5E-2 两个真实 Skill 的统一同步 `run()`、Harness 唯一发布权、失败映射和 Artifact SHA；
3. 5E-3 进程内 `stream()`、实时事件顺序、terminal commit 后交付、backpressure、关闭隔离
   和 run/stream parity；
4. 代码、聚焦测试、完整回归、compileall、两套 RAG、治理、secret/run-data boundary、
   Harness dry-run 和 exact-SHA GitHub Actions；
5. 用户理解所需的面试级解释、当前限制和后续阶段边界。

### 不纳入

- 真实 Provider、Key、GLM/DeepSeek/Qwen 对照或模型切换；
- Prompt/RAG 内容重做；
- API、SSE、前端、Session/Memory、MCP、durable event log、cancel/resume；
- LangGraph、Pi、Claude Agent SDK、Multi-Agent 或 DAG；
- 用测试数量替代领域质量或生产 SLO。

## 4. Exit Matrix 初始列

每一行必须至少有：

```text
requirement
→ source files / ADR
→ focused tests
→ proportional regression
→ public CI evidence
→ current limitation
→ exit decision
```

建议分六组：

| 组 | 要复核的事实 |
|---|---|
| Contract | request selected-only、item/event/Trace schema、终态和 Artifact 引用不变量 |
| Functional | recent/single Skill、knowledge Tool、Harness 评测/修订/发布与 typed output |
| Failure | boundary/context、Agent/Evaluation Provider failure、rejected、observation、Trace persistence |
| Resource | event budget 最坏上界、queue 背压、关闭、Usage complete/partial/unknown、无 Provider I/O 边界 |
| Security | Prompt/正文/Tool data/request ID/异常不进入 Trace；Artifact SHA 真实字节校验 |
| Delivery | 本地回归、exact-SHA Actions、治理状态、README/公开边界和未完成能力 |

## 5. 审查顺序

1. 先从 canonical state 和 ADR 读取承诺；
2. 对照 5E-1/2/3 源码和测试，不凭对话记忆补事实；
3. 运行现有聚焦/完整门禁，记录真实数量和失败；
4. 对每个缺口判断：属于事实文档修正、测试补强、当前最小实现，还是后续阶段；
5. 若需修补，先写红灯，再做单一最小改动并回归；
6. 形成 exit decision：`close-5E`、`close-with-deferred-boundary` 或 `remain-open`；
7. 更新 canonical 状态、活动计划、决策/路线/能力矩阵，并通过 exact-SHA 公共 CI。

## 6. 5E-4 完成标准

- 每个 5E 承诺都有源码、测试、公共证据和限制记录；
- 未把 Fake Provider、stream 订阅或最终 Trace 夸大为真实模型质量、SSE、durable runtime；
- 已知失败语义没有互相矛盾，Usage/Trace/terminal 终态可复读；
- 所有必要的最小修补和回归通过；
- 得到明确的 5E 退出决策，并把后续唯一阶段写入 canonical 状态；
- 不引入本阶段未授权的 Provider、SDK、框架或基础设施。

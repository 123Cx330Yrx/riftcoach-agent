# DeepSeek 模型分层延后设计

## 1. 要解决的具体问题

RiftCoach 当前正在 5D-7 验证第二个 Provider。唯一候选是
`deepseek-v4-pro`，因为这一轮不仅检查 JSON 和 Tool Calling，还要验证完整的领域
Skill、RAG、AgentLoop、Evaluation 和 Harness 控制流。

与此同时，`deepseek-v4-flash` 更快、更便宜，未来可能适合普通任务。因此一个自然的
产品设想是：

```text
DeepSeekProvider
├─ deepseek-v4-flash：低成本普通任务
└─ deepseek-v4-pro：复杂任务或质量升级
```

问题不在于这个设想能不能写出来，而在于现在还没有真实产品数据证明它比“全部使用 Pro”
更好。若当前同时测试两个模型，会扩大 5D-7 的首次 held-out 暴露面，把第二 Provider
准入门变成模型排行榜，并延迟已经冻结的 Pro 协议门。

## 2. 底层原理

### 2.1 Provider 与 Model 不是一回事

`DeepSeekProvider` 负责厂商协议：请求、工具调用、结构化输出、usage 和错误归一化。
Flash 与 Pro 是该 Provider 下的两个模型 ID。增加模型分层不需要第二个 Agent，也不等于
Multi-Agent。

### 2.2 准入、选型和运行策略是三层决策

```text
协议/领域准入
  某个精确模型能否安全完成 RiftCoach 控制流
        ↓
产品选型
  质量、稳定性、成本和延迟是否满足使用条件
        ↓
运行策略
  哪类任务用哪个模型，失败后是否允许受控升级
```

当前 5D-7 只处理第一层，并绑定精确 Pro 模型。未来分层属于第三层，不能根据官方定位或
主观感受直接上线。

### 2.3 5F 的职责保持不变

5F 比较的是 RiftCoach 自建 `AgentRuntime V1` 与 Pi / Claude Agent SDK：第三方 Runtime
能否保留 Skill 权限、Tool Runtime、Harness、Trace、预算和终止语义。模型切换可以作为
SDK 可移植性的一个观察维度，但 5F 不负责建立 Flash/Pro 路由策略。

## 3. 采用决定

选择延后模型分层：

1. 当前 5D-7 继续只以 `deepseek-v4-pro` 运行最多 3-call 协议门；协议通过后，仍只让
   Pro 进入已经冻结的领域 held-out；
2. 5E 先统一 `run/stream/event/trace/usage`，5P 再形成早期产品纵向切片；
3. Flash 分层实验最早只能在 5P 完成后重开，默认等待阶段 6 出现真实 API 调用、延迟、
   Token、成本或容量 Bad Case；
4. 该实验是横向 Provider 优化门，不新增、重排或改名阶段 0-8，也不占用 5F 的 Runtime
   SDK 采用职责；
5. 若最终证据不支持分层，继续使用单一模型是合法结果。

## 4. 未来候选架构

未来若重开，先在 `DeepSeekProvider` 之上增加确定性的 `ModelTierPolicy`，而不是让模型
自行决定调用哪个模型：

```text
typed Skill request + capability/quality budget
                    |
                    v
             ModelTierPolicy
              /           \
     Flash ordinary       Pro complex
              \           /
                    v
          same AgentLoop / ToolRuntime
                    |
                    v
          same ReviewHarness quality gate
                    |
         pass ------+------ fail
                              |
                       bounded Pro escalation
                       （仅在策略明确允许时）
```

首版策略必须只读取可信、类型化信号，例如 Skill 身份、所需能力、Context/Token 预算和质量
门结果；不能根据用户文本中的“复杂”“简单”等词直接授予更昂贵调用，也不能让 Flash 失败
后无限重试 Pro。

## 5. 未来实验怎样开展

### 5.1 触发条件

至少出现一种可复现证据：

- Pro 的 p50/p95 延迟影响产品体验；
- Pro 的单位成功报告成本超过已冻结预算；
- 普通任务占比足够高，存在明确的成本优化空间；
- 供应可用性或容量要求需要同 Provider 内的第二模型层级。

只有“Flash 更便宜”而没有产品调用分布，不构成触发条件。

### 5.2 三组对照

```text
A：Pro-only
B：Flash-only
C：Flash default + bounded Pro escalation
```

三组使用相同的新 development/held-out、Skill、Prompt/Context、RAG、Harness 和安全
门禁。当前 5D-7 held-out 的首次结果不能拿来调未来策略；未来需要单独记录污染并冻结新
数据集。

### 5.3 接受标准

分层策略至少需要证明：

- unsafe publication 不增加；
- 事实、引用、工具往返和终态正确率不低于冻结阈值；
- 总成本或 p95 延迟有可测收益；
- Pro 升级次数、额外 Token 和最大调用数有硬预算；
- Flash 或 Pro 失败时仍由 Harness 降级，不能绕过发布门禁。

结果 ADR 可以是采用、部分采用或拒绝采用。

## 6. 本次调整实现与不实现什么

本次只修正规划和责任归属：

- 保留当前 Pro-only 5D-7 实验；
- 明确 Flash 分层最早在 5P 后、默认在阶段 6 依据真实数据重开；
- 保持 5F 为 Pi / Claude Agent SDK Runtime 采用实验；
- 不修改 `DeepSeekProvider` 的 Pro-only 配置；
- 不添加 Flash allowlist、自动路由、fallback、用户模型选择器或新 API 调用；
- 不运行 held-out，也不改变当前唯一下一步。

## 7. 当前限制与面试表述

现在可以准确地说：

> RiftCoach 已把 Provider 与 Model 分层，并将同厂商模型分级设计为证据驱动的后续优化；
> 当前先用 V4 Pro 完成复杂领域准入，待产品 Trace、延迟和成本数据出现后，再比较
> Pro-only、Flash-only 与 Flash 默认/Pro 升级策略。

现在不能说已经实现智能模型路由、成本最优调度、自动降级或多模型生产组合。

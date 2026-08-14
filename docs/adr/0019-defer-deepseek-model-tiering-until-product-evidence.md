# ADR-0019：将 DeepSeek 模型分层延后到产品证据形成后

## 状态

已接受；修正 ADR-0018 中 Flash 后续评估的阶段归属，不改变 Pro 的当前准入选择

## 日期

2026-08-14

## 背景

ADR-0018 选择 `deepseek-v4-pro` 作为 5D-7 唯一领域准入候选，并把 Flash 留作未来
成本/时延分层候选。其正面影响部分曾把该未来实验放到 5F。

但 5F 已有固定职责：用真实业务切片比较 RiftCoach 自建 AgentRuntime 与 Pi / Claude
Agent SDK，并通过成本、能力保持和 ADR 决定采用、局部采用或拒绝。把 Flash/Pro 选型
也放进 5F，会混淆 Runtime 采用和 Provider 模型策略，导致同一子阶段同时改变编排框架与
模型，无法归因结果。

当前也没有真实产品流量、p95 延迟或单位成功报告成本，无法证明 Flash 默认、Pro 升级
优于 Pro-only。5D-7 的 held-out 已冻结给唯一 Pro 候选，不应在首次执行前扩成同系列
模型排行榜。

## 决策

当前 5D-7 保持 Pro-only：协议门和后续领域 held-out 都绑定
`deepseek-v4-pro`，不加入 Flash。

DeepSeek 模型分层改为横向 Provider 优化门：最早在 5P 早期产品切片完成后重开，默认
等待阶段 6 产生真实 API 调用、Trace、延迟、Token、成本或容量 Bad Case。它不属于 5F，
也不新增或重排阶段 0-8。

未来若触发，必须比较：

1. Pro-only；
2. Flash-only；
3. Flash default + bounded Pro escalation。

三组必须使用同一套新鲜 development/held-out、Skill、Prompt/Context、RAG、Harness、
安全门和资源预算。只有质量与安全不低于冻结阈值，并在成本或延迟上获得可测收益时，
才可采用分层。没有收益时继续单一 Pro 或拒绝 Flash 都是合法结论。

5F 仍只比较第三方 Agent Runtime。它可以验证 SDK 是否保留显式 Provider/Model 选择能力，
但不能借此实现或宣称 Flash/Pro 自动路由。

## 影响

### 正面

- 当前 5D-7 不扩候选、不污染首次 held-out，能按既定 Pro 门继续；
- 5F 的 Pi / Claude Agent SDK 采用实验保持单一变量和清晰归因；
- 未来模型分层由真实成本/时延分布触发，而不是由价格宣传或主观偏好触发；
- `DeepSeekProvider` 可以在证据成立后承载 Flash/Pro，而无需复制 Agent、Skill 或
  Harness。

### 负面

- 当前不能获得 Flash 的真实质量、成本和延迟对照；
- 在 5P/阶段 6 之前不会实现普通任务自动降本；
- 未来需要新的数据集、策略预算、对照实验和结果 ADR。

### 不变边界

- ADR-0018 的 Pro 当前候选、3+12 calls、Token/金额停止线和 fail-closed 规则不变；
- 当前 `DeepSeekProvider` 继续只允许 Pro，不增加 Flash 配置；
- 不增加用户模型选择器、自动 fallback、Multi-Agent 或第三 Provider；
- Harness 继续拥有唯一发布权。

## 备选方案

### 现在在 5D-7 同时比较 Pro 与 Flash

拒绝。会扩大当前第二 Provider 准入范围、增加首次 held-out 暴露和真实调用，也把准入门
变成同厂商模型排行。

### 在 5F 比较 Pro 与 Flash

拒绝。5F 的变量是 Agent Runtime；同时改变模型会破坏 SDK 采用实验的可归因性。

### 永久只使用 Pro

暂不预先锁死。它是当前范围最小的选择，但未来若真实成本/时延 Bad Case 成立，拒绝
评估 Flash 会损失可测的产品优化机会。

## 参考

- `docs/plans/2026-08-14-deepseek-model-tiering-deferred-design.md`
- `docs/adr/0018-select-deepseek-v4-pro-for-domain-admission.md`
- `docs/roadmap_v1_3_amendment.md`
- `docs/architecture_capability_matrix.md`

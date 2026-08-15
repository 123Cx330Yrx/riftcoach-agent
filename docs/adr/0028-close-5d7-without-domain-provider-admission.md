# ADR-0028：在没有领域 Provider 准入的情况下完成 5D-7

## 状态

Accepted

## 日期

2026-08-15

## 背景

5D-7 已建立分层领域评测、Prompt/Context 身份、development/held-out 生命周期、
Evaluation 1.1 注入阻断、资源预算和安全失败归因。Zhipu 与 DeepSeek 有最小协议层真实
证据，但两者都没有完成并通过近期复盘的真实领域全链路。DeepSeek 当前尝试已由
ADR-0027 关闭；GLM-5.3 普通 API 尚未正式可用。

如果把真实模型领域通过设为 5D-7 的必要退出条件，项目将被外部模型发布或围绕旧候选的
重复追绿阻塞，也会把“评测系统完成”与“某个候选采用成功”混为一谈。

## 决策

1. 5D-7 以评测、实验控制和采用决策能力作为退出标准，不要求某个 Provider 必须通过；
2. 接受 5D-7 完成，同时明确领域 Provider 采用结果为“当前无准入，质量 unknown”；
3. 保留 GLM-5.2 开发基线、Zhipu/DeepSeek 最小协议事实和所有不可变负面结果；
4. G53 保持 deferred，但不再阻塞 5D-7 或 5D 的退出审查；
5. Flash/Pro 分层继续受 ADR-0019 约束，不因 5D-7 完成而自动重开；
6. 下一检查点仅为 `5D-exit-review`，不直接进入 5E；
7. 本决策不授权读取 Key、调用 Provider、修改 Prompt、切换默认模型或重跑旧结果。

## 后果

### 正面

- 评测阶段可以用诚实的 reject/unknown 结果结束，而不必为追求绿色结论过拟合；
- 项目不再依赖 GLM-5.3 的外部发布时间；
- 负面模型证据、确定性 fallback 和安全发布权继续保留；
- 5D 退出审查可以独立检查整体运行链与 5E 前置项。

### 负面

- 当前没有可声称生产可用的真实领域模型报告链；
- 无法给出完整成功路径的质量、p50/p95、Token 和成本基线；
- 未来模型采用仍需新的实验身份、预算和真实调用。

### 中性

- 不删除 Provider Adapter，也不宣布 DeepSeek 或 GLM 质量差；
- 不改变阶段 0-8、5E、5F、5P、Memory、MCP 或 Multi-Agent 的顺序；
- 统一 Trace 仍留在 5E。

## 备选方案

### 等待 GLM-5.3 后再完成 5D-7

拒绝。它把内部评测阶段绑定到外部 API 上线，并不能保证新模型通过领域门。

### 立即切换 Flash 或重开 DeepSeek Pro

拒绝。当前没有新的成本/延迟 Bad Case或全新采用需求，且旧实验禁止补跑追绿。

### 将真实领域模型质量默认为 GLM-5.2 已通过

拒绝。既有真实领域结果不支持这个结论；开发默认配置不能替代准入证据。

## 参考

- `docs/plans/2026-08-15-5d-7-prompt-context-domain-evaluation-review.md`
- `docs/plans/2026-08-13-domain-e2e-evaluation-v1-design.md`
- `docs/plans/2026-08-13-injection-evaluation-and-provider-gates-design.md`
- `docs/adr/0013-adopt-layered-domain-evaluation.md`
- `docs/adr/0019-defer-deepseek-model-tiering-until-product-evidence.md`
- `docs/adr/0027-close-deepseek-v3-and-require-safe-provider-error-provenance.md`

# ADR-0006：将 Sea-Mult-Agent 作为可靠执行参考

- 状态：接受
- 日期：2026-07-21

## 背景

RiftCoach 已经把 EchoMind 作为应用层迁移来源，把 AGI-Saber 作为复杂检索和高级运行时参考。后续新增的 Sea-Mult-Agent 官方仓库提供了 Artifact 驱动 DAG、确定性约束、预算、审批、执行租约、迟到结果隔离、事件历史和沙箱治理等实现。

Sea 的业务场景是科研代码复现，技术栈以 Go、React 和 Docker Sandbox 为主；RiftCoach 当前是 Python 垂直教练应用。两者的业务目标与部署成本不同。

## 决策

- RiftCoach 不切换为 Sea，也不迁移到 Go；
- 阶段 2 吸收 Sea 的 Artifact、预算、终态和过期结果隔离原则，用于报告质量 Harness；
- 阶段 8 在确有复杂任务需求时，参考其 DAG Ready 条件、租约、事件历史、取消、审批和恢复机制；
- Sea 的科研仓库发现、论文复现、Benchmark 沙箱和 ToT 消融模块不进入 RiftCoach 主线；
- 只以官方仓库 `https://github.com/yu-xin-c/Sea-mult-agent` 的实际源码与测试为证据，区分当前文档和归档设计稿。

## 备选方案

- 整体采用 Sea：会引入 Go 重写、Docker Sandbox 和科研业务耦合，收益不足；
- 完全忽略 Sea：会错过比纯 LLM 工作流更成熟的可靠执行思想；
- 立即在阶段 2 实现完整 DAG：当前流程是线性的质量闭环，属于过度设计。

## 影响

阶段 2 仍保持轻量 Python 状态机，但 Artifact 和运行约束从一开始按未来可扩展方向设计。复杂 DAG 和产品级恢复机制继续后置到阶段 8，避免推翻既有路线。

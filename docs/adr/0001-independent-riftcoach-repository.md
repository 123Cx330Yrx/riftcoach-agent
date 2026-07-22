# ADR-0001：保持 RiftCoach 独立仓库

- 状态：接受
- 日期：2026-07-16

## 背景

EchoMind 和 AGI-Saber 都提供可参考的 Agent 能力，但直接选择其中一个换皮会削弱 RiftCoach 的领域边界与自主贡献，也会引入不必要耦合。

## 决策

RiftCoach 保持独立仓库。Riot API、Data Dragon、MatchAnalyzer、LoL RAG、训练逻辑和质量门控由本项目维护；参考项目只按明确接口迁移设计与能力。

## 备选方案

- 直接 fork EchoMind：业务骨架接近，但需要修正模型耦合、评测覆盖、Memory 和非标准 MCP；
- 直接 fork AGI-Saber：高级能力完整，但基础设施负担和换皮风险较高。

## 影响

短期需要自行建设应用接口；长期能够保持清晰的贡献边界，并按实际需求吸收两边能力。

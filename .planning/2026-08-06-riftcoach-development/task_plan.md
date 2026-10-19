# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

2026-10-19 实测：用户已授权本批最多六次。s01-facts完成1次HTTP200、25593已知tokens、122.843秒；主审全文核源接受，独立作者真实native及原件字节核验/导入通过。当前ready，next=s01-completion，余5次、未知0、未审0；未发布、未授资格。

## Active Work Package

**目标：** 用三稿六审检验正确全文、事实单错和完成度缺口，决定候选是否值得继续评估。
**实施：** 固定8cdc9d2c、既有worker/批控制/真实native；每项审查，每对实际补丁preview后全文验收。
**证据：** data/evaluation/results/reviewer_semantic_live_20261019.json。
**边界：** 最多六次、482304tokens/1800秒，零重试；熟悉来源非holdout，8E未完成。
**失败分支：** 语义实错停止配置；协议/用量/观测故障停止且保留未知，不补发。
**下一动作：用户执行已绑定最新checkpoint 204f216fbbff329485f9635552bab48b0edb9ba5c70a3de2b6a050406da61669的send-s01-completion.ps1，在本机隐藏输入Key；只发第二项，返回后逐项审查。既有授权有效期不延长，不重跑首项。**

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker与本机
Postgres已恢复：官方停止及两运行目录完整备份，现用127.0.0.1:15432绕过Windows保留端口；
原卷保留、healthy/SELECT1/迁移head已核。配置见workspace_map；当前组合已完成一份自然观摩真实消费，业务验收拒绝，不能外推产品可用。

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

Canonical checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。

以canonical和上方工作卡为准：本地合同修复与裁决更正完成；GLM采用保持，厂商迁移未决定。
原稿保留提案已关闭，不再排transport或新付费授权；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

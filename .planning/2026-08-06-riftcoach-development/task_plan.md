# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

business v1的两例实测和v2终止修复已固化；ADR0104分层候选的精确HEAD `8014a56` / CI `35689438741` 已完成三例开发控制。
三例真实结果均合法结束；随后651a207原归因负例漏检，候选覆盖停止，未接产品。

## Active Work Package

**目标：** 把ADR0108已获得正负区分证据的审查能力接回实际Agent闭环；生成、工具、审查、一次编辑和终评共用原预算，不把两份诊断当产品完成。

**起点和差距：** 原GLM来源失败保留；后续用户另行批准的显式ID两例均通过。正确控制稿不是模型改稿；真实编辑/终评、原15例资格及产品消费仍未验证。原结果入口ADR0108及canonical，不在当前工作卡重抄历史。

**本包实现：** ADR0109 + scripts/reviewer_role_proposal.py；在现有预算算法增加默认不变的委派选择入口，未注册原型精确区分Flash生成/编辑与GLM审查，复用现有状态机和可逆来源投影。真实产品编译消息及5条知识来源用于离线两角色组合验证；禁止网络，不称真实质量。实际发出的policy hash与未变validator hash分别记录。

**本包验收：** 正常五次路径、恢复耗尽、错模型/profile/回执、未投影/冲突phase、传输失败、整体时限和token拒绝；相关默认产品/runtime回归。实际产品默认不注入原型，原合同拒绝该复合身份。公共检查通过后交付可审查的采用提案。

**依赖和失败决策：** 真实Runtime观测、全局序号、逐模型价格、双transport原回执、manifest指纹及资格绑定一起完成后才验证新组合。不能混报模型身份或复用旧a71eb94五例准入。若新实测出现协议/来源/语义/改坏正确段，停止余下批并按首次偏离诊断，不排列提示变体。方法沿用docs/plans/2026-09-22-agent-delivery-method.md。

**预算和授权：** 5调用/401920tokens/900秒，单次32768/300秒，SDK retry0，一次改稿；恢复可能使终评无预算，必须拒绝。产品仍Flash/high，分工采用及新付费需具体决定；本包没有新增Provider请求。Luna仅Codex开发协作。

**当前状态和下一动作：** 离线分工原型、影响表和相关回归完成；具体采用提案见ADR0109。用户若采用则完成表中实际接线，再准备新有界真实整链验证；不重开已结束诊断。此前真实结果/失败/未知用量仍保留在progress和ADR0108。当前8E checkpoint不变。

## Dependencies and Follow-through

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 发布前处理 `run_native_coach_product.py` 硬编码 a71eb94 旧五例结果的问题；不作为诊断误报的前置，也不新建资格框架 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
具体下一动作及失败分支仅维护在上方 `Active Work Package` 的“当前动作”，此处不复制动态排程。
全周期按交付方法执行，工作包结束或出现关键反证时复核策略与下游依赖；普通工程调整沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

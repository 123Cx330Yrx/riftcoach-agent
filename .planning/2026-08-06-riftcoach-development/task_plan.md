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

**本包实现：** 已采用ADR0109，实际入口为build_role_coach_application与ROLE_COACH_CONTRACT 1.5.0；Flash/high生成/工具/改稿，GLM/high首评/重评/终评，共用一个预算和全局调用序号。单个Observer、逐模型Recorder、双传输原回执、可信混合Trace、可逆来源投影及新资产指纹一并接入，复用原Memory/RAG/Harness/Evidence。旧默认不变。实际policy hash与validator hash分别记录。

**本包验收：** 实际应用组装的正常五次发布、恢复耗尽后拒绝终评、错模型/profile/回执、未投影/冲突phase、传输失败、时限和token拒绝；observed身份、Evidence文件及Trace持久化；旧默认产品回归。原15输入全部重新pending，入口拒绝旧五例、两份诊断和模拟资格。完成公开检查及具体真实批预检；离线通过不能替代真实质量资格。

**依赖和失败决策：** 核对实际组装、原始回执和资格指纹一致后再做新组合真实验证。不能混报模型身份或复用旧a71eb94五例准入。若新实测出现协议/来源/语义/改坏正确段，停止余下批并按首次偏离诊断，不排列提示变体。方法沿用docs/plans/2026-09-22-agent-delivery-method.md。

**预算和授权：** 5调用/401920tokens/900秒，单次32768/300秒，SDK retry0，一次改稿；恢复可能使终评无预算，必须拒绝。默认产品仍Flash/high；用户已采用分工，实际接线及离线验证继续；新真实批以具体有界方案安排，本包尚无新增Provider请求。Luna仅Codex开发协作。

**当前状态和下一动作：** 实际接线、开发入口、离线回归及具体预检已完成，验证范围见progress。提交并核对新HEAD公共三项后，请求具体新增批次：同输入Flash对照≤2次/600秒，加一次真实混合应用任务≤5次/900秒；合计≤7次/1500秒，保守未缓存估价4.7638256元，尚未获费用授权。精确计划见data/evaluation/results/role_flash_glm_review_preflight_20260923_v1/next-batches.json，已绑定实际应用预检和首请求。Flash对照首次失败停止比较并暂缓后批，其结论不外推为混合候选失败；真实应用实质失败则停止并审查最早偏离。初评通过不证明改稿，固定报告不证明Agent整链。完成已有准备后不再询问是否采用方案，不重开已结束诊断。当前8E checkpoint不变；此前真实结果/失败/未知用量保留在progress和ADR0108。

## Dependencies and Follow-through

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
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

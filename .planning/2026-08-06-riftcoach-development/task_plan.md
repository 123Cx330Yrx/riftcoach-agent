# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

当前1.5.2原15仍1接受/1失败/13未跑；初评解释错误保留。
现有两调用尾部已实际修复原报告真错、fresh GLM95/pass，主/独立接受全部成稿和最终审查。
这是本例错误未传播的能力证据，不是review准确率、完整15或完整生成任务资格。

## Active Work Package

**目标：** 把实际Agent任务的纠错与交付纳入验收，区分中间模型缺陷和最终交付错误，同时保持原15覆盖和最终质量。

**起点与证据：** 465e3fd8 / CI35962952000成功后，固定未改坏首评离线注入，新增Flash编辑和GLM fresh终评。真全称错句已修、23正确原段保持、错误27–43未传播，最终95/pass、仅正确段可选标记，主/独立接受。2真实调用25693tokens、未知0、未缓存估价0.1510924元；完整golden_role_containment_result_v1.json。原首评仍失败，不推测Flash显式识别该错数；无新生成、完整任务预算或产品持久消费证据。

**选定路径：** 复用现有链路，不建新数值协议。ADR0111与role_task_outcome已实现独立reviewer_quality/task_outcome证据，原正确稿true/true、历史失败首评加尾部false/true；全部准入门保持false。实际请求/阶段/成稿/用量与host裁决绑定，误报、漏检、错误修法、传播和终评错分别检验。run_role_task_observation复用原executor，仅正确定位且修法正确、附属解释有错的初评可带accepted=false继续；实际编辑和终评须全来源通过，禁止协议重评，不写旧qualification_row。

**反证与边界：** 中间错误能否被处理不能根据一例外推；未修报告、错误传播、删除正确内容、最终评审错误、身份/协议/安全/来源/预算失败仍拒绝最终交付。旧失败不改，不从离线注入或跨任务拼接生成fresh资格；真实任务仍5calls/401920tokens/900秒，产品模型和85分保持。

**当前动作：** 完成独立执行审查、冻结新三例并通过同提交公共CI后执行原正确稿→全称错稿→归因错稿连续观察。最多7调用/677376tokens/2100秒，正确例1次/300秒、两错例各3次/900秒，含host时间；保守全GLM预留估价10.006528元，非账单。首个错误verdict、非允许初评缺陷、编辑/终评失败或安全协议预算问题停；不改提示或标签，原两批保持关闭。成功后才能规划原15余项和实际生成消费；旧资格关系见ADR0111，不用新指标偷换。

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

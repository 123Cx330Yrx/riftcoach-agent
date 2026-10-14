# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：用户已确认6次候选并完成零付费接线；新worktree codex/natural-duty-six，旧冻结目录保留。
结构及模型双pass不授语义资格，候选始终拒发布；无新付费授权，automation PAUSED，8E未完成。

## Active Work Package

**目标与结果：** 解决最短自然修订6次与旧5次合同的工程矛盾，独立候选接线完成；不承诺质量准入。
**实际路径：** RecentReview → Runtime单一共享预算 → AgentLoop/本地RAG → 双初审 → 程序预览/唯一应用 → 双fresh。
**边界：** 新1.6.0合同6/401920/900/单请求300；其余high模型和单次输入输出保持，无Flash编辑请求。
追加检索导致不足两fresh slot时停止；未知预留计入预算，取消后下一发送前停止。
**证据：** 新候选22项与相关旧回归；真实产品对象和本地工具、替身模型且socket禁止。
覆盖预算/取消、坏补丁、身份/回执/Trace篡改及来源/原稿/新稿绑定；完整结果见机器验证记录。
**发布判断：** 所有候选成功仍返回FAIL给Harness，另记内部unqualified outcome；未伪造Host验收。
工程接线不证明自动语义冲突检测或真实质量；详见ADR0118及natural-duty-six-implementation。
**旧证据：** 原冻结854源码/3包/103原件及seal一致，不修改旧裁决；固定报告通过仅开发证据。
**下一动作：** 先修CI38590893161历史快照夹具的3份缺失源码副本并复核公共CI；再继续零付费语义反例与同版本资格设计。
四分片均因同一setup摘要错误提前退出，本机124项不代表全库通过；旧摘要与生产拒绝门保持。
发布门关闭，不另开付费批；6次已确认，不重复请求。所有原15、自然产品、前端和学习依赖保留。

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker与本机
Postgres已恢复：官方停止及两运行目录完整备份，现用127.0.0.1:15432绕过Windows保留端口；
原卷保留、healthy/SELECT1/迁移head已核。配置见workspace_map，当前模型组合消费尚未实测。

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

Canonical checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。

以canonical和上方工作卡为准：六次候选接线已有124项离线验证；先完成公共CI历史夹具修复，再推进自动语义裁决反例与同版本资格设计。
不恢复旧付费批，不直接购买正式15；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

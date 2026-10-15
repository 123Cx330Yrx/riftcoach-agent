# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：本次自然观摩真实开发验证已失败关闭；候选不准入，automation PAUSED，8E未完成。

## Active Work Package

**目标：** 对观摩越界及双职责漏检作有证据的路线取舍，保留现有真实Runtime/工具/预算/发布围栏。
**已完成：** 已确认单任务在f606ecb4/CI38704482702全绿后唯一执行；4HTTP/59574tokens/229.531秒，
自主4次知识检索/5片段；两初审pass后结束，无编辑/双fresh。API拒发布；46原件只读replay通过。
**反证：** 初稿block24把只限观摩写成输局补刀≥8和训练后成效；主审与独立均拒绝，双模型初审漏检。
**原生缺口：** 独立作者比唯一native final多末尾LF，JSON同值但严格字节失败；原件和缺口均保留，未补签。
**机制核对：** 实际生成与两职责已有观摩约束/建议审查，没有确定性合同冲突；模板/K3压力未证因果。
本例未进补丁路径；已有Training存储拦截不能修正文。不能靠补一句提醒或数字特判宣布修复。
**路线比较：** 用户允许替代模型比较、可靠性优先，随后提出Astra费用及重做适配的疑问。比较已完成，
GLM采用决定仍有效；撤回过早的Astra首测建议，不实施迁移。通用层可复用，新厂协议/回执/身份需增量验证。
**验收：** 必须保留合法条件观摩选项，不能靠隐藏数字/只匹配本句通过；旧身份、来源、范围边界不退化。
**失败决策：** 本批已结束，不重试、不换例续购、不将工程通过称语义合格；当前没有下一付费批授权。
**下一动作：** 先准备能改变决策的具体诊断材料、合法正例/真实反例、次数与费用，再选择是否执行；
不按模型比较表直接开始接入/付费。比较见docs/plans/2026-10-15-reviewer-route-comparison.md；旧自然批结果保持。

原稿保留提案的主审stop/独立unresolved、原15及所有旧失败/封存保持；不重判、拼资格或重启。
当前候选6/401920/900/300是已确认开发合同，原产品5次不变。原后端冻结与主树前端仍分离。

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

以canonical和上方工作卡为准：自然观摩单任务已结束，机制核对/路线比较已完成；GLM采用保持，厂商迁移未决定。
原稿保留提案已关闭，不再排transport或新付费授权；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

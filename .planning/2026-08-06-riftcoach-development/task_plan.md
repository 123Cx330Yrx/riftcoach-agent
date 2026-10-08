# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 将已验证的必要编辑能力接回现有原15与自然Coach验证，保证实际错误被修正而正确内容保留。
**当前动作与边界：**

2026-10-08：获授权的竞争范围诊断已执行并关闭；8da51fd1/CI37723918833三项成功。
第一项actual-mixed完整返回82/needs_revision，仅block6补刀真错，本次没有block4早死误报；
但scope_checks只覆盖block6，漏掉冻结方案要求的block4竞争范围证据。主审及真实独立审查
一致拒绝audit完整性，原生final成功导入，competition_host_rejected正常停止；第二项未发送。
1调用15888tokens、unknown0，未缓存估价0.186804元；活动46.641秒、host165.312秒。
20原件摘要公开封存golden_scope_competition_result_20261008.json，SHA96e9db8f…1981。
已证明本次问题清单与修法正确；未证明新audit机制完整、稳定或明确错误反例能力。
不能再称本次重现同一事实误报，也不能把单次改善当成核心误报已修复。旧原15仍严格2/15。
本批关闭，不转授剩余一次；未改产品模型/预算/采用标准，生产router仍拒绝新schema。
下一动作：依据本次原始响应完成该实验职责的采用取舍，区分完整审查必需质量与额外audit
证明价值，复用已验证必要编辑能力；不直接登记候选、展开新15或增加字段提醒再花钱试。
证据与边界见docs/plans/2026-10-08-scope-competition-result.md；自然五槽与真实产品仍未验证。
等待期间实测定位资格回放重复投影/绑定的高开销，仅记录性能证据，未改代码或减少检查。
四块联动、自然Coach/本人Training、前端审美/必要重做/英雄头像、Memory、Worker/DB/API/UI、
身份运维、两树整合和学习保持原依赖，8E未完成。

上一批真实三阶段全部通过，3调用45538tokens、unknown0、约0.4230100元；
封存及适用范围见docs/plans/2026-10-01-review-bound-edit-result.md。

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

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
具体下一动作及失败分支仅维护在上方 `Active Work Package` 的“当前动作”，此处不复制动态排程。
全周期按交付方法执行，工作包结束或出现关键反证时复核策略与下游依赖；普通工程调整沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

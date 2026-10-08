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

2026-10-08：完整重评反证之后已核对整链及历史备选；旧批仍关闭，原15严格2/15。
不再重复完整重评、扩输出或重开9月28日已否决的裸四格定向审查。
新增未注册的竞争范围审计离线原型：同次完整初评/终评记录候选范围及全文支持/反对锚点，
必要编辑仍消费原有完整actionable issues；原始scope记录保留journal，成稿fresh不带旧意见。
原15全部请求正文/来源与引用约束保持，未修改生产路由、模型、预算、采用标准或历史回执。
当前真实workflow＋scripted sender三步骤可达；生产router明确拒绝新schema，尚未接自然五调用。
引用/地址合法仍不能证明语义；空记录或错误但格式合法的范围解释仍可能通过结构检查，
离线测试明确保留该反例，不称误报已修。无新Provider请求，无新付费方案。
独立代码复核无阻断，明确保留语义覆盖局限；原15请求审计可复现，单请求保守输入上界最大50976。
下一动作：按ADR0116准备最小完整报告对照的独立实验传输身份及预算验证，核对无需改变
现有生产路由后再冻结具体请求/成本、完成CI与必要授权；不先铺开新15或借旧批余额。
最新完整重评失败证据仍见docs/plans/2026-10-08-scope-resolution-result.md；
本轮设计及限制见docs/adr/0116-proposed-scope-competition-audit.md。
四块联动、本人Training、前端审美/必要重做/头像、Memory、Worker/DB/API/Workbench、
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

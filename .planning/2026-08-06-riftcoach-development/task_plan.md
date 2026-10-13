# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：J1/J2授权批已关闭；执行1708c0cd/CI38372269298全绿，4完整响应/4真实双审/4submit。原件和历史缺口保留，automation PAUSED；主阶段8E未完成，普通无付费项目工作继续。

## Active Work Package

**目标：** 检验事实正确性与任务完成度分工能否改善两处误报和一处修复覆盖分歧；核心语义问题未解决。
**路径：** 三份原失败上下文各full/facts一对，全文/来源/Schema/修法相同，只改职责和明确新身份；不指定目标段/正确口径。生成器及6请求/manifest已离线准备，尚未建执行适配器或授权。
**依据及反证：** 旧模型已看到数字/限定仍误判；职责混合仅是假设。任一facts实错否定本候选，两臂皆过无改善证据；正向单次差异只支持互补职责与编辑消费开发验证，不支持资格。
**范围与成本：** 拟6 GLM-5.3/high、Flash0、580608tokens/3600活动秒/86400Host秒、单次600秒，估价8.577024元非硬账单封顶。没有新付费授权，不借旧身份/授权发送。产品5→7调用另需覆盖/合同取舍，不静默扩容。
**交付与证据：** [职责研究与方案](../../docs/plans/2026-10-14-review-duty-design.md)，7件逐字重建、三对完整性和旧身份拒绝通过；旧readiness审计和700历史原件保持。尚无语义改善实测。
**独立完成：** 取消/失败用量的owner API与UI消费已补，报告权限不放宽，未知不补0；52后端（含6真实Postgres）、32前端、6浏览器及类型检查通过，见[工作记录](../../docs/plans/2026-10-14-terminal-usage-consumption.md)。主树未改，分段模拟消费非自然任务或8E完成。
**下一动作：** 对这六次新成本作明确决定；获准后完成新身份/原生Host绑定并首次发送。普通无付费后续可继续，本包公共CI须核新提交；automation PAUSED。

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

以canonical和上方工作卡为准：职责分离完成离线准备但未被证实；三处语义问题继续阻断新15。六次新诊断待成本决定，原生Host/执行绑定尚未开始；取消用量API/UI分段验证完成，公共CI待核。automation PAUSED，8E及全部产品依赖未完成。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

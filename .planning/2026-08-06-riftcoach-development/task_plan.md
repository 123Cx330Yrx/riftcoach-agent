# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 同一本人训练对象在Training查询和Coach记忆中选择同一最新进度；一次记忆读取不把旧计划与新计划的进度混合。
**起点与差距：** 发现training_query_repository按progress_id降序打破时间并列，而memory_context_repository升序；后者还两次选择active Plan，在READ COMMITTED并发换计划时可能混合对象。需最小可复现红灯，不将静态推断当真实运行事故。
**实现路径：** 保留已有Candidate采用/版本/终态与进度追加合同，在Memory读取中选择一次active Plan，共用于Plan/Progress投影；时间并列排序与Training查询一致，不增加写入口或模型调用。
**交付与验收：** 公共夹具验证同时间记录及读取中换计划；相邻Training/Memory查询、候选/身份/API检查；隔离真库验证同对象与回滚，避免触碰已有卷/数据库。
**失败分支：** 若红灯不能复现，缩回证据而不造修法；若涉及业务语义变化，重审合同。数据库检查只能在本次新建专用test DB运行。
**边界与依赖：** Provider0，不改主树前端/冻结模型政策，不自动准入或重开闭批。两处分歧、旧2/15及3/15、新资格0、正式15/当前组合自然消费/8E与所有下游保持。
**验证结果：** 两真库红灯已复现，修后含无计划并发边界9项通过；13项Memory消费通过，Sol精确SHA真实原生代码复核无阻断。专用test DB已删除，原库head保持；见training-context-consistency。
**当前下一动作：** 收尾提交推送并核公共CI；随后免费追踪实际服务器Progress创建者与已批准指标映射，核完整复盘→Candidate生产路径，不把主观反馈当测量。

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
五尾链硬关闭、尚无充分共同语义修法；既有Coach路径已核。本人Training页面/Coach记忆的并列Progress和换Plan混绑两真库反例已修复，9项真库/13项消费检查通过。下一免费动作核服务器Progress创建者与已批准指标映射、完整复盘→Candidate路径；不补旧字段、重开批或当当前组合真实消费。新资格0、正式15及全部下游保留。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

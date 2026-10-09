# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 核实完整复盘是否真的产生本人训练进度；先修复时间线缺失被汇总/交付为零的问题。
**起点与差距：** 实际v2 executor零候选，terminal模型拒绝deterministic，公开POST来源也不允许Progress；生产者缺口已核。公共夹具原始未知却聚合为0，部分缺失均值没有样本分母，不能直接映射为训练测量。
**实现路径：** 早期死亡的命名样本不完整则None，保留真正零；沿Summary→报告→已验签查询/HTTP/MCP→decoder/adapter/页面打通nullable，不新增写入口或放宽来源。
**交付与验收：** 6个公共整链反例/正例，已有相邻后端/API检查、前端解码/组件与类型检查；只更新backend树，旧run/请求/评级原件保持。
**失败分支：** 字段nullable无法通过消费者时修其真实合同，不能填零；测量范围/时间/去重未定时不抢接自动Progress，也不把获取时间当比赛时间。
**边界与依赖：** Provider0，不改主树前端/冻结模型政策，不自动准入或重开闭批。两处分歧、旧2/15及3/15、新资格0、正式15/当前组合自然消费/8E与所有下游保持。
**验证结果：** 生产路径5项通过；缺失修复前5失败/1正例，修后6通过，相邻后端合计131通过；前端15解码/适配与3中英文组件通过，类型检查通过。前一4e87e28c公共DB/web成功、全CI未结束；见training-progress-source-audit。
**当前下一动作：** 本包提交推送/核公共CI；随后免费形成服务器Progress测量的范围、时间与跨run去重最小合同，先核公开正反例再选择接线。

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
五尾链硬关闭、尚无充分共同语义修法；已有同对象Training/Memory缺陷修复。生产路径审计确认没有自动Progress创建者，先修了时间线缺失变零的Summary→报告→查询/MCP→页面路径，后端131/前端18检查通过。下一免费动作形成测量范围/时间/跨run去重最小合同；不补旧字段、重开批或当当前组合真实消费。新资格0、正式15及全部下游保留。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

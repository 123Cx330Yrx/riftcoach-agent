# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 让新的完整本人复盘实际产生可信逐场训练测量候选，并沿用户accept事务物化。
**方案与范围：** 显式match早死/count与视野/score，纳入的单场/全实际分路；原始比赛结束时间限定在Plan/task创建之间。旧泛指key/窗口/特定分路不猜映射。
**实现路径：** Worker既有terminal入口→验签文件Summary/规范化来源摘要→当前active self Plan→同事务pending Candidate/消息/completed→统一用户accept/再核来源与单位→已有Progress writer。关系/Plan/metric/match固定key跨run首次占位，来源不改。
**交付证据：** 测量23例通过；两组相邻纯合同/API/Worker/Source157+70（新4例另核，复跑23不累计）；生产/采用/来源损坏/并发/中断恢复/换Plan与相邻Memory真库31通过，测试库已删除。原库head0014未变；编译/diff通过。
**失败及边界：** 未测到跳过，来源损坏整笔回滚；修正既有pending批双列查询scalars缺陷。completed/legacy不回填，重复/拒绝/隐藏不重发；system不自动采用。新逐场纠错未开放，旧泛指纠错保留，模型提案独立事务未扩大。
**依赖：** Provider0、资格0；新提交需独立公共CI。未改主树/历史原件，不启动业务Worker、模型或闭批；旧2/15与3/15、正式15/自然消费/8E和所有下游保留。
**当前下一动作：** 本包提交推送；核本人Training计划创建/候选说明与用户accept的现有HTTP/UI可达性，补最短产品断点。

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

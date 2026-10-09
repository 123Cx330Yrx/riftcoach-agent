# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 在现有教练报告Review→必要编辑→fresh路径集中发现尚未测到的修法风险，修复共同问题后解锁同版本完整15及自然消费。
**起点与差距：** 原checkpoint批首案scope:4仅1Flash/11224tokens，Host故障无native final关闭；新授权五尾链在3954ff16/CI37912659534全绿后首次执行，仅claim-scope:6 Flash1/11055tokens，工具参数缺block协议硬关闭。两批有效阶段均0，旧首案与新首案fresh、observed:2..5均未发；缺口各自保留。
**已选路径：** 保留四字段与严格拒绝。当前attribution原文误读与scope修法观测/因果读法不支持共同根因；离线反例证实直接删修法丢指控身份、人工explanation可区分但不保证判断正确。尚无充分共同修法，不建候选发送器或付费冻结；转核自然Coach已有工程路径及独立缺口，不补模型字段/改旧原件/重签初评。
**Host处理：** Sol开发复核和实时谱系/current-route预检通过；本次编辑参数失败在成稿/checkpoint前，未派业务审查。未来实际阶段仍须checkpoint/SHA/全文policy/native final；工程证据不当业务认证。
**交付与验收：** 新批15原件/6公开JSON只读strict seal保留；免费脚本从9份固定SHA公共seal审计11次真实编辑，实际schema与SDK接缝重建一致；7项离线检查覆盖字段丢失/通道/证据漂移/锚点歧义。工程复核不当模型质量证据，未改冻结模型源码。
**成本与决策：** 用户明确“确认吧，继续下一轮”授权最多5Flash+5GLM、967680tokens、3000活动秒/86400Host秒、估价7.862272元非硬封顶。实际Flash1/GLM0、11055tokens、unknown0/receiptless0、估价0.009498元、活动14.266秒/Host0；未超预算，闭批余量不可用于重开或新批。接续自动任务PAUSED，唯一waiter/runner已退出。
**失败分支：** 语义拒绝停该案依赖阶段并继续独立案；身份/来源/native/checkpoint/协议/transport/预算/主体不可用硬停全批，无重试、重评、重开或资格。发现Provider问题集中处理；没有有效新证据不原样重买15。
**限制与依赖：** 首案未认证、两处分歧和共同语义修复保持未完成。旧3/15与历史2/15不拼，新资格0；正式15、自然消费、8E和下表产品依赖保留。泛指不补全称/措辞不升级事实门；ADR0116不复活。
**已完成准备：** 单一117行隔离适配器；20项新旧检查及独立41项回归通过（重叠），实际代码复核native final严格读回/新主体谱系/current-route核验通过，旧冻结和strict replay保持，新五cells/request/identity精确不变。方案d7bf39c634a603b1bcee299de7e7d87e596e258c6c9b4c5afe8bc9c9329aa3e4。
**当前下一动作：** 自然Coach路径核验完成，69项已有离线检查通过、无接线缺陷，当前1.5.6真实消费未证。免费追踪本人Training采用/反馈及四块同对象消费的身份/版本/恢复，完成独立验收准备并修明确缺陷。证据见review-responsibility-decision与coach-consumption-path-audit；不重买剩余尾链。

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
已授权五尾链缺block硬关闭；协议审计及责任反例取舍完成，尚无充分共同语义修法。自然Coach已有工程路径69项离线检查通过。下一免费工作包追踪本人Training采用/反馈与四块同对象消费的身份/版本/恢复，不补旧字段、重开付费批或把旧应用替身当当前组合消费。新资格0、正式15和下游依赖保留。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

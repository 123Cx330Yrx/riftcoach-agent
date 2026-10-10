# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 继续用户要求的案例覆盖，准备后8批尚未发送的后4 observed:2..5，不以旧批关闭取消后续执行。
**实际起点：** 后8在49010a33/CI38062139250首次执行；3通过/5认证stage，第4 observed:1初评96/pass双审完成但native不唯一。6calls/known98364/unknown0已封存，后4未发；完整15仍未收齐，新资格0。
**最早偏离/修正：** root对active/interrupted同一turn补followup_task，产生第二个NEW_TASK，frozen native拒绝，helper实际abort退出；不是Provider语义失败或限额。恢复同checkpoint只MESSAGE，前任务完成/导入才派新stage；原事件不补签。首例CLI相对路径纠正独立留存。
**实现：** document_remaining4_adapter隔离复用原remaining8 runner/evidence，核双旧seal、47源码和原完整cell/request；原时间预算、全文双审、唯一dispatch、checkpoint/native/replay/公开白名单不放宽。
**范围与预算：** observed:2..5，最多GLM8+Flash4=12calls/1161216tokens/3600活动秒/86400Host秒、估价12.0078336元非硬封顶，每案900/5/401920；新run=document-remaining4-time600-20261011。前3、observed:1及旧claim-scope:2不重发/补签。
**验收/失败：** 每stage真实全文双审、真实native导入；语义停案继续独立案，身份/来源/协议/native/transport/预算硬停全批；无重试/重评/重开/旧额度迁移。历史独立，不拼完整15。
**当前下一动作：** 后4本机7项断网接缝及独立工程审查通过、native当前单dispatch实读可用，方案b44521f2…f0de1b已create-only；提交/同HEAD公共CI后确认具体新预算。当前Provider0/无新run，旧8不重开。自动任务保持PAUSED。执行收齐后再综合语义改良，正式15、自然消费、8E和全部下游仍保留。
**证据：** docs/plans/2026-10-11-remaining8-time600-result.md、2026-10-11-remaining4-continuation.md；seal75c8c04d…ec2bf8、公开close audit，138原件SHA/5真实认证事件。

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
用户纠偏后回到完整15主线，具体动作以活动工作卡为准。Training/Memory/nullable已交付成果与下游保留，不计入15质量；旧2/15与3/15独立，新资格0。旧批关闭且自动任务PAUSED，不补旧字段、重开或提前准入。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

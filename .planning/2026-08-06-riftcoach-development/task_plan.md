# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：六次职责对照已关闭；执行85a37432/CI38433654680全绿，实际2次HTTP、1完整响应及真实双审，第二次429硬失败、4未发。原件/历史缺口保持，automation实核PAUSED；8E未完成。

## Active Work Package

**目标：** 消除两处误报和一处修法覆盖分歧，保留真错检出；核心语义问题未解决。
**路径与证据：** 三对full/facts仅system职责及新身份不同；第二项HTTP429使诊断中止。full首项正确检出全称真错且未复现旧误报，facts没有有效回答，不能选择或否定职责分离。见[关闭结果](../../docs/plans/2026-10-14-review-duty-result.md)。
**关闭：** 严格replay/create-only seal及唯一真实native通过；43本批原件含外部观测/作者不变，8个历史批次760文件/53冻结源码/readiness保持。已知17250tokens、0.223940元部分估价，失败用量与总账单未知。不重试/补发/补签/新资格。
**反证与依赖：** 职责分离尚未检验；任一facts实错否定候选，两臂皆过无改善证据。正向开发差异仍需互补职责和真实编辑消费；产品5→7不能静默扩容，新15仍未准入。
**下一动作：** 用户确认余额耗尽且已充值。五次新初评已准备（首组facts、余两组full/facts），原请求逐字不变；最多5次/483840tokens/3000活动秒，估价7.14752元。新范围待单独确认及新HEAD公共CI/即时native绑定，旧授权不重用；详见[具体方案](../../docs/plans/2026-10-14-review-duty-followup.md)。未发送，automation PAUSED。
**独立完成：** 取消/失败用量owner API与UI分段验证已完成，保持报告门与未知语义，详见既有工作记录；不替代核心质量证据。

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

以canonical和上方工作卡为准：职责诊断因传输故障关闭，核心假设未检验；用户已报告充值；五次新初评准备完成，按上方明确新范围推进，旧批不重开。automation PAUSED，三处语义问题继续阻断新15，8E及全部产品依赖未完成。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

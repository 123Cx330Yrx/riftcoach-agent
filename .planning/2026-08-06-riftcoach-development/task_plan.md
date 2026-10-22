# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

2026-10-19：原批第六项HTTP524保持封存；用户单独授权的s03-completion补测HTTP200，22094已知tokens。补测意见与唯一block21修订后的全文均双审接受，真实native/作者字节导入和只读回放通过。三稿六职责由原五项加独立补测取得语义覆盖，不是原六次全成功。累计7HTTP、132730已知tokens、80384未知预留、421.704活动秒；未发布、未授资格，automation PAUSED。

## Active Work Package

**目标：** 从现有真实回执判断哪些意见可用，排除档位反复重测，修正必要修改边界。
**已完成：** 同HTTP原JSON/SDK均max；完整公开意见保留。10月23日主审全源重读、算术/锚点复核、
独立作者→check-answer→唯一native final及主线程原生实读/作者匹配均完成。此处是独立诊断，不是旧批submit。
**结论：** block10为可选表达误升必要修订；block21任意7.5阈值意见及窄修法有依据。保留有用意见，
不自动应用整份意见；原六项双审接受保持，不据不同新稿推断模型退步或max致错。
**现场：** 原seal da687ba3只读replay通过；累计7HTTP/111392known/145824unknown/retry1不变，
本轮Provider0/Key0。原执行入口已消耗，冻结源码/旧seal保持，无补丁应用/模型fresh/产品资格。
**下一动作：** 据本真实误报核对必要修订判定的最小改进与既有正例，先给具体改动再考虑付费；
不因档位重复购买、不重跑原生成和固定六项，复核现有材料不等待新CI。模型/厂商迁移未决定。
**依据：** sol_reasoning_identity_diagnostic_20261022.json；独立checkpoint1355e97a、作者SHA d6c46965；
旧准备及诊断分支留在原工作卡历史部分，不再作为执行队列。automation保持PAUSED。

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

以canonical和上方工作卡为准：诊断已完成，一条误报/一条有用意见已独立复核；先修必要修改判定的具体机制，
复用既有材料，不再等待CI/输入Key/重测档位。原发布门、8E与后续依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

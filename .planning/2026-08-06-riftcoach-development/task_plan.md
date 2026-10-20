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

**目标：** 在自然任务实际链路验证候选审查配置，先完成零付费接线，不以固定稿筛选代替产品验收。
**实施：** 独立候选身份、动态初审/fresh请求、真实回执与共享预算，复用现有Runtime和逐字修订。
**证据：** reviewer_semantic_live_20261019.json、sol_natural_offline_preparation_20261019.json及sol_continuation_audit_20261020.json。断续审计修复清单漂移、deadline硬错遮蔽、缺观测误重试、失败usage归属及Trace消费；稳定回归172、身份25、消费130、最终超时17项分别通过（有重叠），隔离SQL/Worker/API16项无skip。
**边界：** 独立候选已实现。拟6逻辑调用+1超时重试/498688tokens/1200秒，估价0.6170624元；未授权新调用，产品五调用/GLM采用不变。
**失败分支：** 明确且已回收的超时同阶段最多重试一次，保留已完成结果及未知预留；结构/身份/语义错误不重试，不无限扩容。
**下一动作：提交并核新的精确HEAD公共CI。混合候选持久执行、重启恢复与独立审查/回放接线已完成离线验证；CI未全绿前不是付费launcher ready，不重开原固定批。**

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

以canonical和上方工作卡为准：本地合同修复与裁决更正完成；GLM采用保持，厂商迁移未决定。
原稿保留提案已关闭，不再排transport或新付费授权；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

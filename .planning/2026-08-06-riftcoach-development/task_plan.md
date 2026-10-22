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

**目标：** 在下一次付费前核清最新HTTP200后的本地档位拒收，验证完整接收/失败/恢复路径，不用重复调用代替诊断。
**事实：** dadb73eb的CI39730401796全绿且用户已经执行。Key等待计时已修；新增1HTTP/28070已知tokens，
首次新facts-initial返回非high字符串而触发reasoning_identity。原返回具体值未保存，不能判定low或语义错误。
**修复：** 补安全固定分类和白名单值，不改变接收规则。沿真实SDK→子进程→观测/回执→应用预算/停止，
并验证启动/长等待/恢复/四审查/唯一应用/只读replay/seal，零付费。
**保留：** 已闭Operator唯一seal1d0a2f49，70项原库存及stdout根复核未变；累计6HTTP/80137known/
145824unknown/retry1，原生成与检索报告保留，native业务审查0。
**验证：** 82项接收/SDK/子进程/应用检查与54项候选/实际启动/续接整链回归通过；CLI启动、治理、编译和diff检查通过。
**判断与下一动作：** 本地整链已验证，按request ID核查原effort/映射的具体问题已备好，未代发消息。
用户确认费用页不含该字段，已排除该证据来源，不再要求重连/继续查价格。
无区分证据不原样重试、不重新输Key、不交付新入口；不能声称整体已修通。
**完成边界：** 软件诊断修复及整链检查通过，只能证明本地路径；不能冒充上游恢复或自然Agent质量。
工作卡及事实分别见docs/plans/2026-10-22-sol-credential-wait-recovery.md当前节、
data/evaluation/results/sol_reasoning_identity_diagnostic_20261022.json。原预算授权不重复索取也不延展；automation PAUSED。

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

以canonical和上方工作卡为准：当前查已有渠道记录，先完成离线整链验证；不再等待Key或交付重复付费入口。GLM产品采用保持，厂商迁移未决定。
复用原稿与历史成本，不重开旧封存；当前发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

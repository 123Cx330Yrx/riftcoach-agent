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

**目标与依据：** 已阻止取消后的下一发送；本包补齐提前停止丢失用量Trace的明确缺陷。三处语义问题仍未解决，新15提议撤回，普通无付费工程工作继续。
**实际机制：** 可信发送guard绑定实际observer；新DispatchAwareRuntime捕获本次启动身份并复用原记录器/终态写盘路径。保存已发生调用与用量，未发不计调用、未知不填0；Worker独立裁定取消/失去租约/数据库错误。真实观察故障继续默认拒绝。
**接线与隔离：** 普通RuntimeCompositionRoot接适配器；冻结native构造由显式with_dispatch_trace包装后使用。直接改native构造会触发组件指纹门，已恢复原字节；没有改旧manifest、frozen runtime或候选默认。适配器依赖V1私有接缝，未知子类拒绝，升级需复验。
**证据：** 最终210项相关回归通过（50.47秒）；独立Postgres17/FastAPI/Worker/显式包装应用6项通过（15.14秒），第1/3/4次取消保留对应Trace，SQL/事件/owner/幂等/报告门保持。0发送、失租、DB错误、真实记录器故障、写盘错误、未绑定停止、unknown用量、并发身份隔离均覆盖。模型/来源为替身，不是自然消费或浏览器验证。
**历史与环境：** 最新执行准备54份源码及700历史原件SHA不变，旧修复就绪审计逐字段相同。测试容器已删除；原产品Postgres卷/15432保持。Docker恢复及前两次CI修复详见取消工作记录。
**当前与下一动作：** 取消Trace实现和本地验证完成，下一项核本次提交公共CI。上一提交d5009705/CI38420884219查询时前端、打包、Postgres及pytest分片2成功，其余三个分片仍运行中，不报全绿。用量查询/UI消费与time600自然生成继续作为后续依赖。
**主阻断：** 责任拆分缺新增语义修复依据，当前不实施；三处旧语义问题不因运行修复改变。无新候选/付费队列，automation PAUSED，8E及下游未完成。

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

以canonical和上方工作卡为准：提前取消Trace已在显式应用/真实数据库链路验证，下一项核本次公共CI。三处语义问题继续阻断新15；责任拆分没有被选为修复，执行准备保留但付费提议已撤回，automation PAUSED，8E及全部产品依赖未完成。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

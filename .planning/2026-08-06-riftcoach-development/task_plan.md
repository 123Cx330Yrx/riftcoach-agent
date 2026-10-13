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

**目标与依据：** 继续保留三处语义问题及新15撤回决定；先修复已在post-joint-consumption记录、现已复现的独立运行缺口：收到取消/失去租约后，真实Agent不得继续发下一次模型请求。
**机制与实际路径：** 旧Worker只在executor返回后处理租约结果；Provider启动观察前增加执行上下文内的租约检查，复用现有heartbeat/CAS终态，周期续租与发送前检查串行，取消/丢失不可被后续ACTIVE覆盖。上下文退出即释放，不改模型输入、业务预算、冻结workflow或资格标准。
**具体实施：** `app/runtime/dispatch_control.py`、`app/runtime/observer.py`及`app/workers/review_worker.py`；真实应用回归在`tests/test_worker_dispatch_control.py`。不修改已登记的ObservedLLMProvider代码或Prompt Program指纹来伪装旧证据覆盖。
**当前证据：** 修改前的观察函数在第一次调用后取消仍发送完整5次；新边界按取消位置只发送1/3/4次，未取消的完整5阶段保留。相关Worker/观察/应用125项44.69秒通过，收尾23项及4项定向复验通过；业务、DB使用替身，后台heartbeat是真线程，无模型请求。54源码绑定与700原件SHA不变。
**验收与边界：** 复核旧源码/700原件、相称测试/治理/提交。正在进行的HTTP仍保留结果；只阻断下一次发送，不承诺打断已发请求。原budget先预留的未发尝试仍保守保留，不伪记第二次实际调用/用量。现有同步Runtime链路之外的自建线程执行须显式传递上下文。
**主阻断与下一动作：** 三处语义问题尚无已证明修法；引用绑定只能证明出处，不能自动证明全文解释正确，因此不增加引用字段或同义教学。本取消修复已完成验证；下一项仍是有历史反证约束的语义修法选择，当前尚未选定有效干预，不创建新付费队列。automation PAUSED，8E及下游未完成。

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

以canonical和上方工作卡为准：模型发送前取消/租约检查已完成离线验证；下一项回到语义修法选择，三处语义问题继续阻断新15。执行准备保留但付费提议已撤回，automation PAUSED，8E及全部产品依赖未完成。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

1.5.4旧manifest严格3/15作为历史保留；修复知识工具对齐后新manifest真实资格0/15。三父已关闭，原九例未启动且身份已过期；不迁资格、不丢费用。完整原15、自然Agent和产品消费仍未完成。

## Active Work Package

**目标：** 让当前Coach合同声明的知识工具能力与真实运行一致，完成相关应用验证，
在启动付费前准备修后完整十五例及累计预算决定。旧人审/续接修复保留。

**起点与实证：** 402恢复后无活动Provider，7d52fd64已推送。原九例尚未启动时发现：
manifest要求knowledge.search2.1.0及retrieved_at，RuntimeExecutionFactory漏掉correction-scope，
实际返回2.0.0。四合同+legacy反例中仅本合同失败；不是模型语义或网络问题。
完整证据：`docs/plans/2026-09-27-knowledge-runtime-alignment.md`。

**实现路径：** 按Native合同继承家族启用知识检索时间，避免逐实例名单再次漏项；
注册实例门、legacy行为和模型政策不变。四当前manifest仅刷新runtime组件与整体摘要；
新增实际工厂/schema/本地检索/知识投影回归，修后完整17项通过。
纯prepare_fresh复用现有完整十五例准备；原执行入口仍拒绝关闭批，不新增after-*执行器。

**身份与预算：** 修后manifest 6be60527…fdebf；原十五请求字节不变，但现有严格门
不允许跨manifest迁资格。旧3作为历史，新真实0/15；旧九例准备443c220a…2d28不能再执行。
历史12调用169342tokens/2799.094秒、unknown0，239原件已再次核验不变。
新完整15最坏35调用3386880tokens/10500秒，累计最坏47/3556222/13299.094；相对原授权
多12调用169342tokens/2799.094秒。提案execution_authorized=false；不隐式扩额。

**验证与失败分支：** 当前组合实际应用生成/工具/审查编辑/fresh、严格资格与工厂相关
回归及同HEAD公共检查完成后，请求具体新增预算决定。完整上下文业务标准不变，
新批继续双审工作稿和显式最终提交、原300/900秒时钟、首错停批，无重试/重评。
不把本地RAG/替身应用成功说成真实模型质量通过；若新检查否定修法，先诊断再冻结。

**当前动作：** 修复与独立检查已完成；知识工具17项、应用/严格资格/工厂66项均通过。
完成新提交公共检查后进入必要预算决定。
新15准备7a797831d4e029846bbe2773b85705237e16e293c5e4c5dbc443fe2adc9f322e与预算提案已保存，
未创建新run或发Provider。完成验证后再进入新增预算决定，不重新启动旧九例。

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker环境故障
单列处理；已获用户单socket清理授权但自动审批仍拒绝，未恢复，不能宣称本地DB实测。

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
具体下一动作及失败分支仅维护在上方 `Active Work Package` 的“当前动作”，此处不复制动态排程。
全周期按交付方法执行，工作包结束或出现关键反证时复核策略与下游依赖；普通工程调整沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：初审逐字补丁固定报告链已真实通过并封存；automation PAUSED。熟悉单例不授资格，
自然修订最少6调用超过产品5上限；零付费审计已完成，6次候选待决定，8E未完成，无新付费授权。

## Active Work Package

**目标与结果：** 查明自然任务为何需要两次生成，并形成完整职责下的预算取舍；零付费审计已完成。
**实际路径：** RecentReview编译 → 同一BudgetedProvider → AgentLoop选择知识工具 → 本地执行 → 模型读取成稿。
一轮工具后双初审pass共4次；程序补丁加双fresh最少6次，追加工具轮次为5/7次。
**证据：** 实际AgentLoop/ToolRuntime/本地RAG三路径探针；共享预算第6次、900秒到期、token不足拒发，
剩50秒timeout裁为50。14项既有产品组装回归通过；模型为替身，外部调用0，不证明自然补丁接线或质量。
详见[具体取舍与实施边界](../../docs/plans/2026-10-14-natural-review-duty-budget.md)。
**推荐与待决定：** 显式候选max_calls从5改6，保留401920tokens/900秒/单请求300秒和现有模型high；
尚未采用或实施。6只容纳最短修订；更多工具轮次仍可拒绝，不能保证任意任务成功。
**其他方案：** 保持5则常规修订停止；确定性预检索会改变Agent检索；合并职责回同一次请求需要重新验证；
并发不减少调用数。推荐保留当前有单例支持的职责分离和动态检索，不删completion/跳fresh/另开账本。
**实质依赖：** 开发600秒身份和六个Host门不能直接移植；产品发布语义、独立身份及同版本资格仍缺。
**下一动作：** 用户决定6次候选后，先做零付费身份/发布语义设计与接线；新付费需具体新方案，不挪旧授权。
**已完成证据保留：** 固定报告development_chain_pass，facts72/needs_revision→两补丁→双fresh96/pass；
4HTTP/65839tokens、103原件及6native/作者严格封存，854源码/3包保持；熟悉单例非holdout或产品准入。
见[关闭结果](../../docs/plans/2026-10-14-review-duty-direct-patch-result.md)。旧失败/分歧和原15裁决不重判。
**范围：** 生产代码/预算未改、automation保持PAUSED、无新业务run或Host任务；正式15、自然Coach/Training、
四块联动/journal、前端头像审美、Memory、身份运维、两树整合、独立评估、学习保留，8E不推进。

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

以canonical和上方工作卡为准：自然调用路径与预算零付费审计完成，下一步是明确6次候选取舍。
批准后先做独立身份/产品发布语义设计与接线；不恢复旧付费批或直接购买正式15。8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

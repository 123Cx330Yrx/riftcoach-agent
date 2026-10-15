# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：用户已确认6次候选并完成零付费接线；新worktree codex/natural-duty-six，旧冻结目录保留。
结构及模型双pass不授语义资格，候选始终拒发布；无新付费授权，automation PAUSED，8E未完成。

## Active Work Package

**目标：** 一份公开历史ShowMaker观摩任务，补真实Agent取知识、自然成稿、自动补丁及双fresh在共享预算内的开发验证入口。
**依据与起点：** 发送前取消修复452972e7的CI38680020527全部通过；独立方案审查支持自然单任务的信息增量。旧helper与transport不能直接用于此候选。
**路径：** typed观摩/OBSERVED Memory → 真实Runtime/Agent工具/本地RAG → Flash成稿 → GLM双职责/程序逐字补丁/双fresh → 原进程回执/Trace → 拒发布 → 事后完整双审。
**实施：** 固定两份公开来源原字节与历史投影时间；实际capture第一请求；专用6次/300秒传输、独占claim、冻结核验、run外观测和只读replay；不另造Agent运行栈。
**验收：** 离线实际应用4/6调用、额外检索、身份/授权/请求漂移/缺观测/超时/重开拒绝；旧应用与历史回放保持。真实质量需要未来新授权后的模型回执及完整双审。
**依赖：** 同HEAD公共CI全绿与具体新费用授权；6/401920/900，单次300，估价5.7595904元非账单硬上限。没有旧授权迁移、waiter或新付费run；automation PAUSED。
**失败分支：** 语义错误、预算不适配、工程故障和事后分歧分开保留；不凑次数、强行修订、扩额、跳fresh或重试。
**当前状态：** 准备提交4d37e344已推送；CI38685915747旧方案源码绑定测试失败，其他分片及非pytest检查通过。已从原提交归档LF源码，在临时目录重建历史库存；当前请求/预算仍逐字段核旧方案，原记录不改。修复前1失败、后相关24项通过（38.02秒），准备包重新生成完全相等。Docker残留运行socket复发已恢复，原卷/容器保持。
**下一动作：** 提交该历史测试修复并核新精确HEAD公共CI；通过后才请求本包新费用授权。见docs/plans/2026-10-15-natural-duty-observed-development.md和natural_duty_preservation_ci_recovery_20261015.json。

**上一包已结束：** 原稿保留诊断的p01信息减少成立，实质损害与合法压缩未决。
主审stop、独立unresolved，真实native与作者原件逐字一致；不写成双方一致stop。
预设门未满足，20请求零发送结束、无sender/run；原设计/标签/材料保留，不换例继续本批。
详见docs/plans/2026-10-15-preservation-material-decision.md；10项来源/原生边界检查通过。

**不变边界：** 用户已确认候选6/401920/900/单请求300，其余high模型及输入输出保持；
候选双pass仍unqualified且拒发布，不伪造Host验收。原产品5不变，无第7次、无新费用授权。
原后端5b19e3ee干净、旧854源码/3包/103原件及全部旧裁决保留，automation PAUSED。
452972e7/CI38680020527全部公共检查通过；新准备提交须有自己的公共CI。

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

以canonical和上方工作卡为准：Docker、真实Worker/SQL/API及取消记账修复已核；完成自然观摩单任务零付费准备及新提交CI。
原稿保留提案已关闭，不再排transport或新付费授权；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

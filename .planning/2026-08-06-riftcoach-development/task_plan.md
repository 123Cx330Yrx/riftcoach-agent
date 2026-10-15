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

**目标：** 验证六次候选在真实Worker/SQL/API中停止后仍保留实际用量，同时未认证报告不可见。
**依据与起点：** 1.6.0应用接线及离线取消已完成；现有数据库测试用旧五次correction-scope组合，不能替代当前组合。
**路径：** API任务 → Postgres领取/owner取消 → RecentReviewTaskExecutor → 自然候选DispatchAwareRuntime → Trace/receipt → SQL终态 → owner用量API。
**实施：** 复用本地RAG与脚本替身Provider，新增当前组合Postgres整链回归并接公共数据库job；无生产路由注册。
**验收：** 初审4次、修订6次均不发布；第1/4/5/6次取消阻止下一发送，已发生tokens保留；外人取消/读取404、报告409、终态不重领。
**依赖：** 只用新建可丢弃Postgres。用户补充要求修Docker启动错误；先修已定位的运行socket残留，不动产品卷/镜像/数据或凭据。
**失败分支：** 真正实现缺陷按实际路径修复；软件替身测试不能改变自动语义结论、同版本15或资格门。
**当前状态：** 7场景真实Postgres/Worker/API全部通过（26.69秒），无skip；公共数据库job已接线。Docker两个运行socket目录同时备份重建后恢复，原产品库healthy，独立测试库已删除。
**下一动作：** 核本提交公共CI并按实际失败最小修复；本包不产生模型质量/自然消费资格或新付费队列。结果见docs/plans/2026-10-15-natural-duty-worker-consumption.md。

**上一包已结束：** 原稿保留诊断的p01信息减少成立，实质损害与合法压缩未决。
主审stop、独立unresolved，真实native与作者原件逐字一致；不写成双方一致stop。
预设门未满足，20请求零发送结束、无sender/run；原设计/标签/材料保留，不换例继续本批。
详见docs/plans/2026-10-15-preservation-material-decision.md；10项来源/原生边界检查通过。

**不变边界：** 用户已确认候选6/401920/900/单请求300，其余high模型及输入输出保持；
候选双pass仍unqualified且拒发布，不伪造Host验收。原产品5不变，无第7次、无新费用授权。
原后端5b19e3ee干净、旧854源码/3包/103原件及全部旧裁决保留，automation PAUSED。
49d7ddd2/CI38675972603最近仍运行，web/packaging/Postgres已过；不宣称后继全绿。

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

以canonical和上方工作卡为准：Docker恢复、六次候选真实Worker/SQL/API验证已完成；核本提交公共CI，失败时沿实际路径修复。
原稿保留提案已关闭，不再排transport或新付费授权；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

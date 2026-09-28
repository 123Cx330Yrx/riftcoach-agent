# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

1.5.4旧manifest严格3/15作为历史保留；修复知识工具对齐后新manifest真实资格0/15。此前闭批误报保留；后继异领域示例两控制通过，实际编辑/fresh尚未验证。原九例未启动且身份已过期，不迁资格、不丢费用。完整原15、自然Agent和产品消费仍未完成。

## Active Work Package

**目标：** 阻止Coach把全文已正确的观摩说明判错并送入编辑；沿既定完整上下文标准
定位本次首评偏差，选择能覆盖真实完整任务的修法。不能用手改正例或一次重新pass交差。

**起点与实证：** 用户2026-09-28已批准修后完整15，1ecd8cd1/CI36307792122三项成功后执行。
首例claim-scope:1返回85/needs_revision，误把全文已明确的全样本早死继承为局部中单。
主/独立全文复核确认误报；28原件封存12f38fda…6965，原strict adapter拒零完成。
后14例未执行，当前身份0/15；旧身份3/15只保留历史。无活动Provider。

**已完成诊断：** 新旧报告/来源/prepared相同；实际SDK payload离线重建除timeout外相同，
旧95/pass+advisory、新85/needs_revision。8808输出未达32768上限，流完整、journal未改意见。
实际Workflow.evaluate用原响应零调用重放，仅一评，未触发产品reassessment；自然路径会把
合法needs_revision交给编辑。不是本次网络/截断/工具时间修复引起的已证错误，也未证明采样原因。

**实现路径与去留：** 不改业务标准/标签/模型/high，不重启失败批，不追加同义规则或先跑15。
先按已读历史反证审核单调用审查职责的完整任务可行性；定向早死诊断仅是备选，不能把
单目标通过当全文修复。必须说明正反例区分、覆盖所有业务义务及共享5调用/900秒可达性，
再决定是否值得冻结新的有界诊断。若结果不会改变可实施的方案选择，就不发付费请求。

**当前动作：** 异领域示例两控制已通过完整主/独立审查：正确稿96/pass、真错82/needs_revision，
来源/解释/修法均正确；没有改稿。37原件封存1a4df090…635ddc，不授稳定性或原15资格。
已准备真实Flash编辑→同示例GLM fresh，原完整负例意见作为明确标注的离线初评注入，
不重新发初评、不拼成连续原15。编辑和终评均须全文双审，首错停，无重试或重评。
尾段准备bb94b55c…07ac冻结；完成本准备独立审查/相关验证及同提交CI后，取得本批具体
成本确认执行。此阶段尚未调用，无产品候选注册。成功才决定后续整套回归和正式接线。
详见docs/plans/2026-09-28-context-scope-failure.md；失败不换示例或借余额重试。

**预算与边界：** 已完成两控制2调用30524tokens/470.953秒，缓存2560/unknown0，未缓存
估价0.365212元非账单。新尾段上限2调用/193536tokens/600秒，按Flash+GLM分别估价1.5724544元，
execution_authorized=false，尚未调用；不能借已关闭批余额。产品仍共享5调用/401920tokens/900秒。
此前低温批1调用19749tokens/325.610秒/估价0.316972元，完整15首例批1调用20608tokens/
192.344秒/估价0.341024元及三父历史保留；不把后两例通过拼回旧manifest3/15或当前0/15。
完整上下文、原报告/来源、双审、原计时和首错停止保持。自然Agent、同组合存储/Worker/API/UI
和8E仍未完成，知识工具能力对齐与Docker恢复的工程结果保留。

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

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
具体下一动作及失败分支仅维护在上方 `Active Work Package` 的“当前动作”，此处不复制动态排程。
全周期按交付方法执行，工作包结束或出现关键反证时复核策略与下游依赖；普通工程调整沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

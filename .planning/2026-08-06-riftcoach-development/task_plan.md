# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 让完整来源支持的正确表述通过、实际数值/范围错误被检出并充分修复，再取得同版本完整15链证据；不以外围工程替代主线质量。
**起点与差距：** time600完整15已授权首次执行并硬关闭。3例通过、3例语义拒绝/分歧、第7例初评返回未审、后8例未发；13调用/known226429/unknown0/receiptless0，估价2.5300928元非账单。结果见`docs/plans/2026-10-10-full15-time600-result.md`。
**当前实现与证据：** 复用既有DocumentReviewWorkflow、block键归组编辑、全文成对教学、TimedDocumentBudget及真实回执/native交接。12已审stage真实终答严格核验，302原件SHA一致、156白名单封存；默认产品未切换，新资格0。旧2/15、3/15和remaining11不拼接；第二例旧成功与本轮回退均保留。
**免费分析路径：** 固定公开seal中的源/完整原稿/实际policy/公开issues和修法，对照两份历史第二例及旧11扫描；分别核全文消歧、明确错误不可被后文撤销、修法覆盖摘要/正文和泛指不可补全称。现有policy/教学已含这些规则，不能将失败直接解释成缺一条提示；先区分信息缺失、决策顺序负担和Host边界分歧。
**取舍与验收：** 输出可审查的逐issue证据及少量竞争机制，写明最强反证、替换掉什么负担和最小区分检查；证据不能选因果时照实保留，不先铺完整变体或新增字段/付费批。确定性软件缺陷可直接修，离线成功不能代替模型语义质量。
**关闭及工程依赖：** 旧root429后新分支无法派冻结独立主体，实际helper routing_failure关闭，runner已退出、自动任务PAUSED。此批禁止重开/补签/借余量。未来批需自己的真实root/独立路径预检与具体新方案授权；不替换旧身份来补第7例，也不将429等同额度耗尽。
**当前状态与下一动作：** 已核三处实际issued policy/响应，规则与对应教学存在，误报仍选择最近语境；不存在已证教学/中转因果。免费准备既有短教学与紧凑决策流程替换扩展示例的对照，固定原稿/来源/实际模型/时间身份，覆盖旧成功第二例、scope:3修后正确稿、明确全称真错及scope:4混合错。具体取舍/反证见结果文档末节；无新Provider调用，不直接实施或购买完整变体。正式15、自然消费、8E和下游依赖保留。

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
用户纠偏后回到完整15主线，具体动作以活动工作卡为准。Training/Memory/nullable已交付成果与下游保留，不计入15质量；旧2/15与3/15独立，新资格0。旧批关闭且自动任务PAUSED，不补旧字段、重开或提前准入。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

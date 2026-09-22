# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

business v1的两例实测和v2终止修复已固化；ADR0104分层候选的精确HEAD `8014a56` / CI `35689438741` 已完成三例开发控制。
三例真实结果均合法结束；该候选只获得继续同版本覆盖资格，未接产品，不能视为完整模型质量或8E结论。

## Active Work Package

**目标与起点：** 完整报告审查应发现真错、保留正确描述，并可靠提交可消费结果。
此前JSON尾文引发完整重评和范围误报；ADR0104把真实阻断与完整上下文下的可选表达建议分开，三例开发控制已验证这条路径的基本行为。

**具体实现：** 现有runner采用`--policy partitioned-tool`，复用全量来源、business语义政策、
NativeIssuesReview Schema、验证器、一次修订及共享预算。review/reassessment以单个
`submit_report_review`工具参数提交结果；revision仍为Markdown。不执行外部工具或追加回合。
AUTO不是强制工具保证；非空正文、多工具/错工具、错误终止或回执直接拒绝，不截尾。
设计取舍见ADR0103；原始Exchange保留，重新序列化参数明确标为projection。

**交付和验收：** 候选三例已实测，不重跑。完整公开证据与人工逐例裁决分别保存，不将机器位置匹配当语义验收。
修正后的coverage_v2绑定15个不同输入：3完成、12待测；先attribution 1（遗漏的归因负例），再scope 4/3、claim-scope 2/5/6/7、observed 1–5。
每例检查全部意见、引用、实际改稿和最终结果；预期标签只在host，旧版本成功不拼接当前资格。

**失败分支：** 终态协议/执行失败、漏检、范围误报、真实问题被放入advisory或改坏正确段时停止该候选批次并定位首次偏离。
既有有界字段重评仍可执行并完整记账，但它会重新判断语义，不称纯格式补齐。没有隐式补字段或放宽准入。

**资源及依赖：** Flash/high、SDK retry0；生成/工具/审查合计5调用、401920tokens、900秒，
单次32768/300秒、一次修订。两次生成加首评/修订/终评恰好五次；若使用字段错误重评，
后续可能预算拒绝，不能宣称全部恢复路径必能完成。business旧批与产品入口仍关闭。

**当前动作：** 修正覆盖遗漏、导出原始公开证据、撤回“仅补字段”表述，产品提示/模型/预算未变。
使用现有runner精确CI检查完成同版本覆盖；源码从8014a56保持，证据提交不能冒称新候选。
Git 12000代理已可用，44ed9bc/35692962399三项通过；后续执行提交CI按实际状态查询，不保留旧网络阻断。

## Dependencies and Follow-through

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 发布前处理 `run_native_coach_product.py` 硬编码 a71eb94 旧五例结果的问题；不作为诊断误报的前置，也不新建资格框架 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
当前行动以活动工作卡的ADR0104候选覆盖为准；旧business/tool失败批保持停止，原始证据不改写。
实现/证据达到同版本覆盖门槛后，才进入真实产品生成/来源发布与消费链路；普通实现选择和有界实测沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

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

**具体实现：** 现有runner新增`--policy tool`，复用全量来源、business语义政策、
NativeIssuesReview Schema、验证器、一次修订及共享预算。review/reassessment以单个
`submit_report_review`工具参数提交结果；revision仍为Markdown。不执行外部工具或追加回合。
AUTO不是强制工具保证；非空正文、多工具/错工具、错误终止或回执直接拒绝，不截尾。
设计取舍见ADR0103；原始Exchange保留，重新序列化参数明确标为projection。

**交付和验收：** 先通过协议正反例、最终SDK请求、完整来源、真实Runtime共享五调用等离线检查；
提交后核对精确HEAD公共CI。新批固定claim-scope 1（正确全文）、4（全称真错）、3（混合真错/正确段），
每例核查实际报告和全部意见后才继续。冻结来源/输入哈希，不把旧批未跑的案例自动接回。

**失败分支：** 协议失败则本批停止，拒绝把自然文字转换成通过；合法工具输出仍误报则否定
“改通道足以解决语义”假设，保留通道证据而不接产品。不得失败后补一句提示重开同批。
三例成功仅允许推进原定同版本覆盖，不代表完整资格或全阶段完成。

**资源及依赖：** Flash/high、SDK retry0；生成/工具/审查合计5调用、401920tokens、900秒，
单次32768/300秒、一次修订。两次生成加首评/修订/终评恰好五次；若使用字段错误重评，
后续可能预算拒绝，不能宣称全部恢复路径必能完成。business旧批与产品入口仍关闭。

**当前动作：** ADR0104分层候选已实现；38项聚焦回归、组合回归112项、治理检查和完整产品组装通过，候选代码的精确CI `35689438741` 通过，三例真实开发控制已冻结。
它把阻断issues与完整上下文下的advisories分开，保留建议而不触发修订；案例3的实际改稿经逐字差异与来源核对确认只修正真实补刀错误。剩余11个去重案例已完成本地preview并冻结身份与预算，但当前状态提交 `34133c2` 尚无exact CI，不能付费执行；公共CI可用后按清单逐例覆盖，任一真实错误漏检、advisory误升级、协议失败或实际改稿伤及正确段，都停止该候选批次并回到机制诊断。

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

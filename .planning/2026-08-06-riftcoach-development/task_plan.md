# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

business v1的两例实测和v2终止修复已固化；ADR0104分层候选的精确HEAD `8014a56` / CI `35689438741` 已完成三例开发控制。
三例真实结果均合法结束；随后651a207原归因负例漏检，候选覆盖停止，未接产品。

## Active Work Package

**目标与起点：** 完整报告审查应发现真错、保留正确描述，并可靠提交可消费结果。
此前JSON尾文引发完整重评和范围误报；ADR0104把真实阻断与完整上下文下的可选表达建议分开，三例开发控制已验证这条路径的基本行为。

**具体实现：** 阶段合同、严格解析、原始回执、来源和共享预算保留；buffered与JSON正文两条真实分支均停止。
位置数组仍是待评估表示；先完成最小合同反例与方案裁决，不直接投入完整工作流。
已有check_review_submission_shapes只验证无损表示和12个坏形状，不是新候选，更未取得模型资格。
具体取舍、反证和实施边界见docs/plans/2026-09-22-review-submission-contract-decision.md。

**交付和验收：** 定点配对结果已人工核对，但不计入完整报告资格。新请求先过原归因负例和其正确对照，
再混合/全称/原观摩正例；之后完成coverage_v2原有15个不同输入的其余10个，不混入旧版本成功。
每例核对全部意见、来源、真实改文及终评。模型不接收host预期标签；公开证据与人工裁决分别保留。

**失败分支：** 终态协议/执行失败、漏检、范围误报、真实问题被放入advisory或改坏正确段时停止该候选批次并定位首次偏离。
既有有界字段重评仍可执行并完整记账，但它会重新判断语义，不称纯格式补齐。没有隐式补字段或放宽准入。

**资源及依赖：** Flash/high、SDK retry0；生成/工具/审查合计5调用、401920tokens、900秒，
单次32768/300秒、一次修订。两次生成加首评/修订/终评恰好五次；若使用字段错误重评，
后续可能预算拒绝，不能宣称全部恢复路径必能完成。business旧批与产品入口仍关闭。

**当前动作：** 11bc7bd / CI35716166747三项通过后JSON首调用持续事件到299.906秒，无正文/usage，300.015秒截止。
该分支已关闭，无改稿/终评，本次1调用用量未知。buffered前例单片重复也保留为失败，未据此改变质量标准。
下一步在现有原型验证公开原响应→严格形状验证→具名投影→旧意见枚举，并核对SDK构造可达性。
本批0次付费；坏类型意见不得消失，无法无损定位的形状拒绝。结果与去留理由写入现有方案裁决。
只有证据支持继续，才实施完整重评/追溯与实际产品预算检查，再裁决实测；不循环开关、不提额度。
本轮7请求/102235已知tokens，另1未知；阶段合同/失败记账改进不等于核心链路已走通。

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
具体下一动作及失败分支仅维护在上方 `Active Work Package` 的“当前动作”，此处不复制动态排程。
全周期按交付方法执行，工作包结束或出现关键反证时复核策略与下游依赖；普通工程调整沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

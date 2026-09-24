# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

ADR0109角色候选已有旧合同下一例真实归因修订/终评及来源修复后自然生成证据，不能计为当前1.5.2资格。
当前1.5.2原15为1接受/1失败/13未跑：正确泛指稿95/pass；全称真错检出，但解释新增错误视野范围。
默认产品、完整标准和8E边界不变；两批失败及各自原始响应均保留。

## Active Work Package

**目标：** 让Agent发现报告真错后完成可靠纠正，同时减少评审自己新增事实的错误；不把内部模型输出、最终报告和资格结果混成一个pass。

**起点与证据：** 88f05647 / CI35960739920三项通过后，冻结三例批仅执行2次。原正确稿主/独立接受；全称真错被正确检出且建议修法正确，但解释把中单视野40/43/25/27写成27–43，完整review被拒绝。原数据未丢、解析无损、无超时/耗尽，编辑与第三例未执行。29576tokens、未知0、未缓存估价0.355568元；完整公开证据golden_role_clarity_result_v1.json。

**目前判断：** 非阻断marker收缩覆盖其自身扩写通道，但实际issues仍有同类自由事实生成责任。补齐通用min/max只能减算术负担，不能强制模型引用；内部review失误能否被已有编辑/独立终评纠正，需要检查实际消费者和旧反证，不能根据单次抓错正确就擅改资格标准。

**选路与验收：** 比较后优先复用现有编辑/终评，固定此次未改bad review和原错稿，不先建源绑定数值新协议。离线注入首评，新增Flash实际编辑→fresh GLM终评；主/独立核对真错已修、正确内容保留、错误27–43未传播及完整最终review。成功只证明本类尾部容错，不证明编辑显式发现错数、review自身通过或原15准入；失败按首次真实偏离裁决，不改一句提示就重试。完整上下文、原15、85分、原稿和旧失败保持。

**新批预算：** 独立role-review-containment-v1，最多2调用/193536tokens/600秒，单次32768/300、retry0，保守全GLM预留2.859008元（非账单）。历史首评注入不新增Provider调用/费用，原实际费用留旧批；同提交公共CI后沿持续授权执行。禁止自动reassessment；首个改稿或终评host拒绝即停。尾部观察不能证明真实2生成＋首评＋尾部在完整401920/900内完成。

**当前动作：** 尾部runner七项离线回执/失败边界检查通过，待独立代码审查和同提交公共CI后执行冻结两调用。产品policy/schema/模型/预算未改；本诊断不为任何旧失败补票。

## Dependencies and Follow-through

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

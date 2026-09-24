# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

当前1.5.2三例连续真实观察均通过，正确报告原文保留，两类真错实际修正并完整终评通过。
旧资格失败不改；新三例尚未自动转换为原15资格，剩12未执行，完整生成/产品消费仍待验证。

## Active Work Package

**目标：** 用已取得的同版本真实原件接上原15完整资格，减少无信息重跑；继而解锁实际Agent生成及产品消费。

**起点与证据：** 34648531 / CI35967784437三项成功后，原正确稿95/pass，全称错稿80→实际改稿→95/pass，归因错稿84→实际改稿→96/pass。所有7stage主/独立全文接受，无例外、重试或reassessment，两个改稿各保留23原段。7请求104967tokens/1436.141秒/未知0，估价0.970882元非账单；100原件及公开投影见golden_role_task_result_v1.json。旧失败原件与原裁决保持。

**实现路径：** 新qualify_role_observations只读封闭原件，重新核对身份/请求/真实回执/全部stage及主独立裁决/连续预算，单独写原格式host-review与qualification row；不读取两个结果布尔直接授资格，原validate_qualification不改。满15才调用原门。剩12复用同executor与StrictObserver，任何accepted=false或defect停止，不使用ADR0111的解释缺陷例外。模型、政策、schema及产品预算保持。

**反证与边界：** 三例不是稳定率或独立holdout；旧失败不改。后续任何实质误报/漏检、错修法、错误解释/引用、编辑/终评/来源/身份/协议/预算失败均停止批次并定位首次偏离，不自动换提示再试。不得用部分资格代替15覆盖或完整Agent任务。

**当前动作：** 严格证据验收及剩12执行器已完成，前三例原件validated_partial；独立审查与聚焦检查通过。同提交公共CI通过后，沿用持续授权执行有界剩余输入。原顺序：claim-scope:3、scope:4、scope:3、claim-scope:2、claim-scope:5、claim-scope:6、claim-scope:7、observed:1–5。4正例各1调用/300秒，8错例各3调用/900秒，最多28调用/2709504tokens/8400秒（含host），保守全GLM预留估价40.026112元、非账单；首失败停，无重试/重评/计时重启。先以严格离线验收确认前三例，单个报告仍不得超过产品5calls/401920tokens/900秒。

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

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 将已验证的必要编辑能力接回现有原15与自然Coach验证，保证实际错误被修正而正确内容保留。
**最新实测与边界：**

2026-10-01最新：用户明确批准冻结359ce034…45c66后，a40753b9公共CI36827955797
三项成功；三阶段真实诊断全部通过，每阶段主审及真实独立审查均接受并完成事件导入。

- 必要编辑：Flash只替换block4的错误句，修正辅助局对不同指标的相反影响，其余全文逐字保留。
- 完整fresh：GLM对精确成稿返回93/pass、issues为空，仅block4建议；双审核对无误报或遗漏。
- 正确保持：Flash对claim-scope:1返回空edits，正确报告逐字不变，建议未升级为必改错误。

本批3调用45538tokens、unknown0，活动200.235秒、host527.672秒；未缓存估价0.4230100元。
含旧两笔合计5调用68223tokens、0.4429600元，未超用户本批批准上限；无重试、无追加请求。
51原件封存golden_review_bound_edit_result_20261001.json，SHA941d3ca5…ceffb；旧26原件不变。
两条历史初评仍只是固定诊断输入，三阶段不算三条原15合格案例；原15旧身份1/15不授新合同。
这次真实证明了该必要修订→完整fresh以及该正确保持控制，未证明总体稳定率或自然Agent能力。

等待期间GitHub读取状态EOF令旧外部等待脚本退出，实际CI未失败、当时Provider0；已将等待
改为只读查询故障与测试结论分开处理，同冻结HEAD只启动一次。这不是模型断流或额外调用。
封存初次隐私检查因request中的reasoning_content=null过严拒绝，未写出文件；核实为空后
保留请求原结构，实际response只用公开字段白名单，未导出私有推理正文。

下一动作：依据已通过的职责方案，复用现有原15执行/资格回放入口准备同合同完整覆盖，
先验证初评→一次必要修订→精确成稿fresh及原始回执消费，保留失败停止、身份和预算约束；
本批三次调用已全部用完，不以诊断成功或旧授权启动新的付费批。不继续展开schema/加字段
提醒碰运气，也不将本次两个固定输入冒充完整原15。具体接线及证据见
`docs/plans/2026-10-01-review-bound-edit-result.md`。
默认产品尚未注册该适配器；完整原15、自然Coach生成/工具/纠错、当前组合Worker/DB/API/
Workbench和8E仍未完成。四块联动、本人Training、前端审美/必要重做/英雄头像、Memory、
身份运维、两树整合与学习要求仍沿原计划保留。

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

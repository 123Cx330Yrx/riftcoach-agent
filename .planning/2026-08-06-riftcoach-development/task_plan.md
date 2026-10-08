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
**当前动作与边界：**

2026-10-08：竞争范围审计的两项完整报告诊断已准备并冻结，尚未付费执行。
原15仍严格2/15，核心语义误报未证实修好；旧失败批关闭，不转授余额。
隔离sender复用GLM/high真实回执传输，只允许两份精确请求，生产router继续拒绝新schema。
actual-mixed须撤回早死误报并保留补刀真错；明确中单反例须检出两项真错。
全文、所有issues/修法/来源和scope记录逐项双审；测试标签不进入模型，结构通过不等于语义正确。
冻结golden_scope_competition_preparation_20261008.json，SHA e5a40a420e56cff69b193afe58a92e98400f89dd4fcfa559bda2330188886fbc。
新增上限2次GLM-5.3/high、193536tokens、600活动秒、86400host秒，未缓存估价2.859008元。
首失败停，不重试/重评/编辑/重开；两项成功也不授原15或产品资格。
相关63项离线检查通过，最终独立复核25项通过且无阻断；冻结摘要可复现。未知用量保留、
完整usage失败结算、
原生事件交接与关闭竞争已覆盖；scripted transport不证明真实模型或自然五调用质量。
下一动作：提交这份冻结准备，待同提交公共CI全绿且用户明确批准本批新增上限后，
核对真实主体预检并执行两项；无新Provider调用，默认产品模型、预算、采用标准不变。
细节及失败后的取舍见docs/plans/2026-10-08-scope-competition-diagnostic.md和ADR0116。
四块联动、自然Coach/本人Training、前端审美/必要重做/英雄头像、Memory、Worker/DB/API/UI、
身份运维、两树整合和学习保持原依赖，8E未完成。

上一批真实三阶段全部通过，3调用45538tokens、unknown0、约0.4230100元；
封存及适用范围见docs/plans/2026-10-01-review-bound-edit-result.md。

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

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

1.5.4旧manifest严格3/15仅保留历史，知识工具修后身份0/15；新1.5.5正在接线，从0/15。
固定示例两控制和真实编辑/fresh均通过全文双审；这不替代完整原15、自然Agent或真实产品消费。

## Active Work Package

**目标：** 将可行的完整上下文审查策略接到真实Agent全链，并验证既有完整原15；
正确报告保持、真错被检出且实际纠正，不能靠手改原稿或降低门槛。

**已获证据：** 低温误报失败已关闭；异领域固定示例两控制正确96/pass保持、真错82/
needs_revision且意见正确。后续Flash实际编辑分清中单2.50/0.50和全样本2.5/2.67，
GLM fresh96/pass且全文双审接受；原其他事实/来源/身份/训练边界保留。
尾段33原件封存da0d73a6…862ab，绑定2328d7dd/CI36383724302。注入旧初评已明确标注，
不拼成连续原15或泛化证据，旧失败不撤销。

**当前动作：** 按ADR0114完成正式app策略、显式合同1.5.5/Program3.4.0、manifest、
可信Trace、应用builder、自然入口及原15严格资格接线；完成相关验证与独立审查，冻结
同版本完整15准备并提交新CI。独立草稿交接旧profile硬编码已修，真实执行器测试覆盖
所有stage与封存；不新造流程，不只改首评而遗漏fresh/恢复。相关200项及独立审查通过，
完整15准备68ba8615…27fd已冻结；待新提交CI及本批具体成本授权。

**预算与执行边界：** 两控制2调用30524tokens/470.953秒/估价0.365212元；尾段2调用
28552tokens/272.156秒/估价0.152708元，共4调用59076tokens、估价0.517920元，unknown0。
全部为项目Provider未缓存估价非账单，不混Codex用量。两批授权均已结束。
新完整15拟35调用（Flash10+GLM25）/3386880tokens/10500秒含host，预留估价37.167104元。
完成具体冻结材料、相关检查和同HEAD CI后请求本批成本授权；未发新请求，不借旧批余量。
产品共享5调用/401920tokens/900秒与一次改稿不变；完整15仍禁重试/重评，首实质失败停批。

**失败与后续决策：** 软件缺陷沿完整入口直接修并回归；模型实测失败保留第一次偏离，
先核来源/标准/控制路径，不换示例或换版本借余额重试。15通过才验自然Agent生成/工具/
纠错，再接同run真实DB/API/Workbench。普通工程推进无须再次授权；阶段和产品标准不改。

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

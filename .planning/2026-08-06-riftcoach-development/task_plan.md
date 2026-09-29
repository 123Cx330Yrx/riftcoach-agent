# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

1.5.4旧manifest严格3/15仅保留历史；1.5.5严格1/15。最新停止批已发生独立审查身份合同失败，
不是仍停在计时原型接入前。旧模型事实证据保留，旧批不补签、重开或拼成新资格。

## Active Work Package

**目标：** 在真实模型费用发生前确认审查链可用，确保同一主体不能通过两个本地文件冒充
独立审查；并让真正独立的结果沿现有执行器、三阶段提交和严格资格回读完整通过。

**当前已完成：** 实际回执请求SHA替代准备请求SHA；事件源贯通execute、handoff和严格回读；
新执行在凭据/工厂前拒绝v1和缺失依赖。冻结资格API通过有界task-local依赖范围重新完整
回读，退出与异常不泄漏来源；未改产品manifest或模型请求。原生Codex历史读取器已实现，
实际父子元数据/失败turn读取成功，失败事件不能成为独立审查。

**验证：** 七文件回归194通过/1个旧测试失败；修正旧用例后2分支通过。v2离线完整15包含
连续执行与最终资格回读并通过；另16项原生适配器测试和1项三阶段适配整链通过。所有替身
结果仅证明工程接线。独立代码复核仍因429失败，真实宿主完成事件正例未验证。

**当前动作：** 保存完整修复与验证。独立审查可用时先完成代码复核，再用原生宿主读取
一条新绑定的完成审查，验证导入、主审与回读；不重试相同429，不用自己写的event代替。
现有adapter仍是未完成真实成功验证的候选，不能据此启动付费15例。

**依赖和失败决策：** 原生API历史若不保留所需派发/正文，则指出具体缺字段并调整适配，
不凭字符串、双密钥或调用成功宣布独立身份；真实模型语义失败与工程/宿主失败分开处理。
初评/实际改稿/fresh正例必须走完整同版本任务，不能借历史稿或手改原稿通过。

**预算边界：** 原15闭批2调用29682tokens/357.719秒/估价0.341556元；remaining闭批2调用
27325tokens/914.422秒/估价0.1930048元；随后计时批另3个完整调用48607tokens，加1个
unknown/incomplete请求。未知用量不算免费。此前控制/尾段另记，不混Codex额度。
本轮无新GLM调用；未来新批需新冻结身份、累计预算、同HEAD CI及具体授权，旧34次不能
作为重开额度。模型/high/1.5.5/产品5调用401920tokens900秒不变。

**后续：** 完整原15真实资格→自然Agent生成/工具/纠错→同run真实DB/API/Workbench；
可独立的产品工作按现有依赖继续，不将质量门与整个Agent产品混为一谈。

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

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

当前新v2父批严格完成1/15；claim-scope:1为96/pass并完成真实双审及封存回读。
14例续批只完成claim-scope:4初评，GLM正确检错；宿主派发密文使正式审查证据导入失败，
已停止并封存，未编辑/终评，新增资格0。父批首例保留，两个运行目录均只读。

## Active Work Package

**目标：** 解除宿主密文派发的工程交接阻断，完成真实独立审查的可验证消费，为继续原15
质量验证恢复通路；产品目标仍是可靠Coach生成/审查/纠错及真实消费。

**实现路径：** 显式采用native-final-attestation-v1取证策略，复用原生路由/作者/完成证据，
由真实独立final确认六字段并与原件核对。不再要求加密派发逐字正文；可读冲突仍拒绝。
策略进入冻结计划和事件，旧规则/摘要/封存不变。模型、high、1.5.5及产品采用标准不变。

**证据：** 真实密文工程交接已完成独立审查→正式提交→封存回读，合成Provider、GLM0、
不授产品资格。相关147通过，准备入口更改后57项受影响测试通过（有重叠）；独立复核无阻断。
99de1782公共CI成功仅覆盖此前预检。父子v2费用仍2调用35034tokens/0.491412元，原15仍1/15。

**当前动作：** 完成新策略补丁交付及对应公共检查；按未完成案例、历史消费与既有授权准备
新的具体付费验证范围，不能重开旧批。真实工程证明与采用取舍见
docs/plans/2026-10-01-native-final-evidence-proposal.md及canonical。

**预算及失败边界：** 原授权续批已启动且因来源失败关闭；不能把剩余额度解释为重开许可。
不重试、不拼历史v1、不伪造host final或补签旧批。开发宿主等待和Provider用量分别记账。
本包工程交接零新增真实GLM；恢复工程通路不等于模型质量通过或未来宿主始终可用。

**后续：** 完整原15→自然Agent生成/工具/纠错→同run真实DB/API/Workbench；
产品四块联动与前端等依赖保留。8E未完成。

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

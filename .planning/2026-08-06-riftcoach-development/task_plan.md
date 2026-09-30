# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

当前新v2父批严格完成1/15；claim-scope:1为96/pass并完成真实双审及封存回读。
下一例尚未调用时执行进程中断，父批保持只读，退出原因未知。

## Active Work Package

**目标：** 在已授权原15预算内完成未启动14例的真实初评、必要编辑及全新终评，
验证正确稿不过度阻断、真实错误能被发现且改文有来源依据，为自然Coach任务接入提供资格。

**实现路径：** 新执行目录沿用现有v2独立审查、来源回放及严格门；封存父批前缀只读。
中断尾部必须绑定下一例且无Provider回执。模型、high、1.5.5及采用标准不变。

**证据：** 时钟16、原v2入口19、续接/资格95通过1跳过；续批累计专项13通过。父批1调用15575tokens、
活动72.72秒、估价0.19142元；原始回执与真实宿主回读通过，独立Agent当前可用。

**当前动作：** 完成更正费用后的续批最终代码复核和同HEAD公共CI，再执行14例。
具体冻结及唯一动态状态见docs/project_execution_state.md和docs/plans/2026-09-30-v2-full15-preparation.md。
旧冻结f3aa0f94…128f6漏父批费用，未执行；新冻结435affe0…dffa2替代，父回执未修改。

**预算及失败边界：** 用户已授权继续；新34调用/3290112tokens/10200秒，父批累计
35/3305687/10272.72未超原35/3386880/10500。费用预留含父费35.929020元非账单。
首个实质、身份、来源、传输或预算失败即停；不重试、不拼历史v1或伪造host final。
开发宿主等待和Provider用量分别记账。续批目前0请求；当前工程通过不授模型新增资格。

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

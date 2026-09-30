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

**目标：** 修复已证实的付费前宿主可用性漏检，明确原15质量验证的真实阻断和恢复条件，
避免在不可读的审查来源上继续消耗。产品目标仍是可靠Coach生成/审查/纠错及真实消费。

**实现路径：** 复用原生只读宿主客户端，首次及续批入口核对指定主体最新任务可读性，
不从旧成功记录回退。正式六字段派发/独立final门保留；模型、high、1.5.5及采用标准不变。

**证据：** 新预检相关三文件最终覆盖91例通过，真实当前密文在Provider IO前被拒绝。
本次1调用19459tokens/估价0.299992元、无未知用量；父子v2累计2调用35034tokens/0.491412元。
32份续批原件已封存核验；执行前8ac9cab1公共CI成功不替代修后CI，不授新增质量资格。

**当前动作：** 提交预检修补和停批审计；恢复真实可读派发来源后，先零GLM真实往返验证。
现有原生接口没有可用明文，不能用本地task或final替代。若确需替代证据合同，先形成具体
可审查方案，不静默降低要求。详见docs/plans/2026-10-01-host-input-readability.md及canonical。

**预算及失败边界：** 原授权续批已启动且因来源失败关闭；不能把剩余额度解释为重开许可。
不重试、不拼历史v1、不伪造host final或补签旧批。开发宿主等待和Provider用量分别记账。
本包离线修补/只读诊断零新增Provider；预检只是防止已知故障下浪费，尚未恢复验证通路。

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

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 让审查正确区分全文已消解的省略与真实事实错误，取得同版本质量证据后接入真实Agent消费。
**当前起点：** 修正控制温度筛查已关闭：7请求、6原生双审（4接受/2拒绝）、第7项有回执无合规独立终答、3项未发；known117826/unknown0/receiptless0，新资格0。停止原因是Host误读标签，非Provider失败。严格replay又在旧时钟等式失败，未生成strict seal；原件保持。
**反证与决策：** 首对双拒绝与全文block14及实际policy甲1存在判读冲突，不能把Host一致当温度效果。两种温度只在两个修正final正例得到合规配对通过，采用门未完成；不再原样购买此筛查。
**已完成修复：** 时钟waiting/finished/summary每组字段用一次观测；单任务原字节SHA核验已接入实际dispatch，新计划绑定其源码，异常不发布交接或进入Host等待。第7项只读干跑成功、146原件未改。历史测试使用核实的旧源码快照，新生产代码仍不能匹配旧冻结批；前提交CI失败与修复后待核状态分开记录。
**本次校准结果：** 用户授权的1个新主体/1次六例合成校准完成，真实唯一final及10条公开工具调用核验通过，六项判定有完整依据，B4交叉引用联动修法为独立增量。11处引句及全部均值实核，Provider0/业务submit0/新资格0；只证明该组材料，不证明长文稳定性。c49f004c公共CI另暴露历史clock归档遗漏，已按旧SHA补齐、13项检查通过，公共CI仍待完整结果。
**当前下一动作：** 准备三份新的完整游戏报告受控材料（正确概括、明确窄范围错误、正确概括与别处真错共存），保持完整来源及policy，检查复杂任务迁移。具体决定与失败分支见校准方案；当前本地准备不发新独立任务或Provider，不沿用已完成的一次校准或旧批成本授权。
**验收边界：** 软件回归及只读实件摘要检查不等于语义通过；旧计时回执不能回填。严格seal缺口明确保留。Provider调用、Host原生证据、语义真值和产品资格分别报告。
**证据：** `docs/plans/2026-10-12-host-scope-calibration.md`、`data/evaluation/results/host_scope_calibration_20261012/close-audit.json`；旧批`docs/plans/2026-10-12-corrected-temperature-screening-result.md`及其146份原件SHA继续单列历史，不回填或拼资格。

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

Canonical checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。

以canonical当前行动为准：六例合成校准已完成，准备完整游戏报告负担下的三份新受控材料，不再原样重买温度筛查；修正控制批已关闭，strict seal未通过，禁止补发或回填。正式同版本15、自然消费、8E及下游依赖保留。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

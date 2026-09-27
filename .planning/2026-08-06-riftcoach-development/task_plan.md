# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

当前1.5.4严格1/15 partial；两例已启动未完成的原因分别为额度中断及host过度拦截，均保留。历史其他版本资格不迁入；完整原15与自然生成/新组合消费仍未完成。

## Active Work Package

**目标：** 在既有1.5.4同版本标准与原预算内，完成尚未启动12例的连续审查/纠错；
把已修复的任务持久化断点用于后续真实Agent，不让新的人为门槛拖住产品。

**当前证据：** fd1cb6f6公共三项通过：完整5097/162skip/129子测试，PostgreSQL218通过，
两处tasks指纹与文件恢复修复已有真实事务验证。原严格完成claim-scope:1，仍1/15。
claim-scope:4因402后host超时缺最终交接；后继claim-scope:3因数值显示被host过度拦截。
第三方和原独立复核均撤回尾零推断精度的阻断定性；旧决定/费用/闭批原样保留，不能补授资格。
详见`docs/plans/2026-09-27-numeric-display-host-audit.md`，旧33原件封存5f22b873…96309。

**实现路径：** 复用既有执行器、逐例ready、主审先保存意见/限时等独立、严格回放和封存。
同一续接入口显式区分历史13与后继12，历史preview读自身封存，禁止旧批重开。
核两父seal/原件/同identity与请求，排除所有已启动输入，不补答/重评/重试或改产品政策。

**预算与边界：** 两批共5调用74142tokens/1380.516秒/估价0.8064944元，unknown0；
续12上限28调用2709504tokens/8400秒，累计33/2783646/9780.516，低于原35/3386880/10500。
两例已开始未完成不纳本续接，即使12全过最多严格13/15。模型/high/提示/Skill/生产开关不变。

**验证与失败分支：** 相关工程回归、独立代码/标准核对、冻结准备、同HEAD公共检查后执行。
按完整上下文和真实来源审查，等价尾零不自行升级为计算错误；没有通用数值容差。
真实错数/错组/错单位、明确错舍入、外推、错误修法、编辑/终评/协议/预算失败仍首错停批。
新争议先核实际合同，禁止从旧工作流隐式迁入门槛；也不以“影响小”豁免真实错误。

**当前动作：** 后继12准备22a857bd…f4fec已冻结；入口48项/邻近资格20项及最终闭批保护8项通过，
两父原件与请求门通过，独立代码复核后提交并完成同HEAD公共检查，再在原授权内执行；无活动Provider。
完整原15后再推进自然Agent及新组合DB/API/UI，所有下游需求见下表，不重排阶段。

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker环境故障
单列处理；已获用户单socket清理授权但自动审批仍拒绝，未恢复，不能宣称本地DB实测。

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

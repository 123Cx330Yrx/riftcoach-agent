# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

当前1.5.3粗来源真实纠错尾段通过，原15完整资格仍未取得。历史1.5.2前三例与中断批前五例合计严格8/15，不迁新版本；旧两例计时丢失等历史缺口保留。完整自然生成/产品消费仍待验证。

## Active Work Package

**当前前置修复（2026-09-25）：** 8117369e公共pytest超过15分钟被取消，数据库与打包成功。已定位旧job本就接近上限及新完整封存回放增加耗时；删除夹具未使用的重复准备，CI容量25分钟且全部检查保留。完成本次相关验证、同HEAD公共三项和实际独立审查者准备，再执行下述冻结原15；不重复发尾段或改模型提示。


**目标：** 在已经真实走通粗来源纠错尾段的基础上，完成同身份原15完整资格审计和验证，推进自然Agent任务及真实消费；不再让一次两控制或尾段成功停留为孤立诊断。

**起点与证据：** 先前三例7请求104967tokens，严格适配器validated_partial/3。后续6bc3470f / CI35972161945执行剩12：claim-scope:3为80→92、scope:4为80→94，六阶段主/独立接受；scope:3仅首评。新7请求102455tokens/未知0/估价1.0247968元；103原件封存golden_role_remaining_interruption_v1.json。根result缺失、原进程不存在，退出原因未知。日志外包时间只作旁证，不补造旧elapsed。

**实现路径：** 原observe逐例保存计划/观察/用量/真实单调计时的完成回执；qualify_role_observations从封闭原件读取连续完成前缀，继续全部回放和主/独立审查，只有全15才调用原门。新入口使用有界文件host交接及隐藏独立进程，避免依赖终端stdin；中断不能重新计时续跑。旧批入口关闭且preview冻结。StrictObserver首失败停，无解释例外或reassessment。

**反证与边界：** 三例不是稳定率或独立holdout；旧失败不改。后续任何实质误报/漏检、错修法、错误解释/引用、编辑/终评/来源/身份/协议/预算失败均停止批次并定位首次偏离，不自动换提示再试。不得用部分资格代替15覆盖或完整Agent任务。

**当前动作：** 本包将coarse1.5.3接入原完整资格机制：共享执行器显式选择合同、来源回执及最终观察身份；严格封存审计支持coarse profile并核动态catalog/schema、完整阶段、双审和原单调计时。新runner不注入尾段、不迁旧8项；每阶段双审在下一调用前检查，逐例完成耐久保存。20项新专项离线检查通过（完整15链、旧版本/缺阶段/缺计时/缺回执/被拒独立审查/中断前缀），只证明接线。独立代码复核未发现默认路径阻断，修复后新旧资格审计60项通过；提交现有CI修复，同HEAD公共三项通过及独立内容审查者就绪后执行冻结原15有界实测。预算35调用/3386880tokens/10500秒（含host）、保守全GLM未缓存预留50.03264元，非账单；首实质失败停，无重试/提示变体，未完成前不授自然Agent或产品资格。之后验证自然生成/工具/纠错及真实DB/API/Workbench。

**另列未解决：** 旧两例业务链通过但精确单调计时没有恢复；墙钟旁证不自动替代旧门。scope:3首评尚无完整host接受及编辑终评；不能重置旧case时钟。后三例observed:3–5尚未执行；observed:2另有引用缺口，不用换批名重试。Worker默认仍单模型，角色应用现有能力须显式接线后用同一真实入队身份/任务验证；报告/任务/event原子提交与assistant terminal turn的幂等投影分开验证。

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

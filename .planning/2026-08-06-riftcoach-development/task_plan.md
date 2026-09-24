# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

当前1.5.2前三例严格validated_partial；旧剩12批两例完整语义通过但精确计时丢失。后继9例批前五例完成并保存耐久回执，第六例初评后等待host超时，最后三例未运行。用户说明对话先因Codex额度耗尽中断；host超时是后台的后续结果。完整生成/产品消费仍待验证。

## Active Work Package

**目标：** 正式验收已完成五例，避免对话中断后自动发起无人接审的新例；根据第六例原始输出定位引用责任缺口，保留原15准入要求并推进真实Agent消费的必要依赖。

**起点与证据：** 先前三例7请求104967tokens，严格适配器validated_partial/3。后续6bc3470f / CI35972161945执行剩12：claim-scope:3为80→92、scope:4为80→94，六阶段主/独立接受；scope:3仅首评。新7请求102455tokens/未知0/估价1.0247968元；103原件封存golden_role_remaining_interruption_v1.json。根result缺失、原进程不存在，退出原因未知。日志外包时间只作旁证，不补造旧elapsed。

**实现路径：** 原observe逐例保存计划/观察/用量/真实单调计时的完成回执；qualify_role_observations从封闭原件读取连续完成前缀，继续全部回放和主/独立审查，只有全15才调用原门。新入口使用有界文件host交接及隐藏独立进程，避免依赖终端stdin；中断不能重新计时续跑。旧批入口关闭且preview冻结。StrictObserver首失败停，无解释例外或reassessment。

**反证与边界：** 三例不是稳定率或独立holdout；旧失败不改。后续任何实质误报/漏检、错修法、错误解释/引用、编辑/终评/来源/身份/协议/预算失败均停止批次并定位首次偏离，不自动换提示再试。不得用部分资格代替15覆盖或完整Agent任务。

**当前动作：** 前五例已封存并加前三例正式validated_partial/8。恢复工程和未知用量反例已验证；当前新工作是来源粒度的两控制可行性诊断，详见docs/plans/2026-09-25-source-granularity-diagnosis.md。原observed:2真错→observed:1正确，最多2calls/158246tokens/600秒，保守估价2.576688元。冻结准备d7639087ff4e171c12f9a8bab9d600687e393dadd3fbb5485d7471e1815e53e9；同提交CI后执行，逐例就绪+完整主/独立审查，首失败停，无重试/编辑/生产切换。保留原全文/来源，只有可引用目录与引用规则改变。成功仅支持后继资格决策，不继承旧8项为新身份；失败否定充分修法，不无信息重试。旧预算消耗15calls/216632tokens/4554.282秒照记。

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

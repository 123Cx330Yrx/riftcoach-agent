# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：互补职责离线原型完成，缺引用合同冲突已用反例定位并隔离修正；19新测试及47相关回归通过，30完整请求零发送。旧五次批已关闭，automation PAUSED，8E未完成。

## Active Work Package

**目标：** 让完整报告的事实与任务完成度意见能安全进入一次真实编辑，并对实际新稿覆盖全部职责；原两误报/一修法分歧仍未证明稳定解决。
**路径与证据：** 新隔离原型完成同稿/来源/request绑定、原样双意见、实际block组装和两fresh构造；旧完整校验器缺引用门不适用于facts-only的反例已复现。见[离线结果及执行范围](../../docs/plans/2026-10-14-review-duty-composition.md)、Proposed ADR0117及源码SHA审计。
**已完成：** 上批closeout CI38507399305全绿；本轮19项新测试、47相关回归，15输入共30请求零发送。旧131原件/11包/77源码、旧53源码/8批760原件/43旧职责原件/readiness及canonical历史保持。
**反证与依赖：** completion未实测、caller clear未认证、没有真实改文/fresh。两职责可能重复或冲突，结构pass不能发布。facts三次双接受只是熟悉来源开发信号；full分歧保持，原15未重启。
**下一动作：** 实现隔离开发入口的请求/回执身份、真实native接受/兼容裁决、run外观测、共享账本及取消/停止转换；离线整链验证后冻结可审执行包。最小固定报告提案4GLM+1Flash、483840tokens/2700活动秒、估价5.8609664元；尚未准备执行或授权新费用。
**失败决策：** 双initial pass跳过编辑；不接受的意见/冲突/坏修法/fresh失败否定此例充分性；native/协议/transport/预算硬故障停止，不重试/补发。自然产品5→7不能静默扩容。
**独立完成：** 取消/失败用量owner API与UI分段验证证据复用；正式同版本15及自然Worker/DB/API/UI消费仍是后续依赖。

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

以canonical和上方工作卡为准：五次初评已关闭，下一步为离线互补职责/真实编辑消费合同；新付费范围尚未授权，automation PAUSED。旧批不重开，原15/8E及全部产品依赖未完成。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

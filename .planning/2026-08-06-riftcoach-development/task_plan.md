# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：互补职责顺序开发链已接独立observed worker和跨进程只读replay/create-only seal；外层执行wrapper及完整冻结待接。零付费/零新真实Host，automation PAUSED，8E未完成。

## Active Work Package

**目标：** 让同一完整报告的事实/完成度意见经真实接受和兼容裁决后进入一次编辑，再以实际新稿完成两fresh；原三处语义问题未证明稳定解决。
**已完成路径：** 两initial/兼容Host/编辑/两fresh共用预算；新增独立真实子进程transport、run外HTTP观测、公开响应/receipt/call-state持久化。回放从Operator已留存closure SHA出发，重建实际编辑/fresh和停止顺序，重取native及作者，外部create-only seal。见[接线说明](../../docs/plans/2026-10-14-review-duty-composition.md)。
**证据：** 新transport覆盖三职责的SDK/本机HTTP完整及中断路径；跨进程重建覆盖成功、拒绝/冲突、硬失败和改件拒绝。67项整组及最终13项受影响复核通过，共68个不同场景；详见progress。HTTP是loopback，native是显式SCRIPTED事件；不能当真实模型/Host或语义改善证据。旧原件/源码/历史实核保持。
**下一动作：** 补完整transitive源码/包冻结、外层新授权/同HEAD CI/native/cwd/Python预检、唯一执行占位与Host交接wrapper。当前新准备仍execution_ready=false；旧44c79817…准备只留历史，无新付费授权。
**范围：** 固定报告最多4GLM+1Flash、483840tokens/2700活动秒/86400Host秒，估价5.8609664元非硬账单封顶；产品5→7不静默扩容。
**失败决策：** 双initial pass跳过编辑；语义拒绝/冲突/坏编辑/fresh失败停止本链；身份/协议/transport/观测/预算硬故障无重试。不把不完整尾项或局部pass算成功。
**CI：** 222f19fa/CI38526956068已全绿；50ad7143/CI38529958480现已全绿，新提交另核。查询失败不等于CI失败。
**独立产品成果：** 取消/失败用量owner API与UI已有证据复用；不冒充当前组合自然Worker消费，正式同版本15及下游依赖保持。

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

以canonical和上方工作卡为准：下一步完成外层执行wrapper及完整冻结准备。新付费范围尚未授权，automation PAUSED；旧批不重开，原15/8E及全部产品依赖未完成。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

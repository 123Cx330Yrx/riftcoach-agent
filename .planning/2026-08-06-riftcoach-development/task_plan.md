# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

2026-10-19：原批第六项HTTP524保持封存；用户单独授权的s03-completion补测HTTP200，22094已知tokens。补测意见与唯一block21修订后的全文均双审接受，真实native/作者字节导入和只读回放通过。三稿六职责由原五项加独立补测取得语义覆盖，不是原六次全成功。累计7HTTP、132730已知tokens、80384未知预留、421.704活动秒；未发布、未授资格，automation PAUSED。

## Active Work Package

**目标：** 修复格式拒收与暂停恢复，保留自然任务成功前缀；分别处理已发现的完成度语义误报。
2026-10-24当前：第四次completion-initial为HTTP200、模型/high匹配，21531已知tokens；接收器因唯一有效工具伴随message而误拒收，并在用户新指令到达前按旧规则关闭。
累计4HTTP/66591known/0unknown/0重试；前三次与facts双审保留，未应用补丁、未发送fresh，不是整批成果作废或完整链路通过。
主审与既有独立作者另审保留意见：OP.GG数字未连具体行动是真缺口；个人参赛归属误报、删正确8.7–9.0/≤3观察参照，故整份completion意见不接受。
真实native及作者字节已在Control外层诊断逐字导入，不补签原闭批；原guard5668400a/checkpoint0041 aa3c2816/seal24172c4f及冻结2b14583e clean保持。
按用户新要求修复格式恢复：开发合同1.6.4显式采用唯一工具+伴随message容错，纯文本/缺工具/坏JSON暂停，普通resume不重发，手动仅重试当前项并保留费用/成功前缀。
身份/档位/来源/观测/多工具/坏补丁和语义错误仍分别处理，不将语义错误伪装为格式补测。新增15项真实worker/Runtime/session检查及132项相关接收/合同/launcher回归通过；7份受影响配置启动、编译与diff检查通过。
**下一动作：** 用已保留误报与正确对照检验完成度必要修订判定机制，先确定有证据的修法，再准备从该职责续接；不重买前三次，不运行15项。
当前不需填Key，旧resume入口因已闭批继续拒发。原grant截止及预算不重置；automation保持PAUSED。
证据data/evaluation/results/sol_necessity_format_recovery_20261024.json；工作卡docs/plans/2026-10-24-sol-output-format-recovery.md。
旧封存/费用、阶段8E及自然Coach/Training、四块/journal、前端、Memory、身份运维、两树整合、独立评估、学习和6对5调用依赖保持。

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker与本机
Postgres已恢复：官方停止及两运行目录完整备份，现用127.0.0.1:15432绕过Windows保留端口；
原卷保留、healthy/SELECT1/迁移head已核。配置见workspace_map；当前组合已完成一份自然观摩真实消费，业务验收拒绝，不能外推产品可用。

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

Canonical checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
下一步以真实完成度误报和正确对照检验必要修订判定机制；格式恢复工程验证见当前工作卡。
不重跑成功前三项，不改闭批原件或补签坏意见，当前无需Key。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

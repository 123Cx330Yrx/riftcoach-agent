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

**当前实现结果：** completion离线断点入口已通过真实旧批核验。原冻结2b14583e/合同1.6.3严格回放后，实际Runtime在临时派生session复用9个成功操作和原facts/native，继承4HTTP/66591tokens/0unknown/0retry及255.657活动秒，准确停在completion发送前。原145件封存/3件作者原件不变，新增Provider/Key0。
13项新增完整性、真实Runtime、native字节及发送前控制检查和6项库存检查通过；上次提交3902e1ee公共CI40087866246已全绿。亲本证明与b/c/d/a候选请求已实际生成，a基线与原前沿一致；当前入口只有离线prepare，没有新运行合同或付费run动作。
**唯一下一动作：** 完成候选合同/receiver、继承native路由及统一累计预算调度，离线跑通b/c/d→自然a→兼容/编辑→唯一应用→同稿双fresh；之后核具体新授权/冻结CI和原生预检，不重买成功前缀或首次已接受a。
证据`data/evaluation/results/completion_continuation_offline_20261024.json`。候选未实测、语义未修复、无当前Key入口；旧grant不延期，automation PAUSED。

以下为同一工作包的材料准备依据；其中“实现入口”已完成到离线前沿，尚未成为付费启动器。

**目标：** 解决completion必要修订误报，保留自然任务成功前缀；格式接收及暂停恢复工程修复已完成。
当前库存遗漏已用新快照修复，历史文件不改，6项库存检查通过；原15输入/请求/预算/资格不变。
完成四稿完整来源对照与未接线候选：a原稿有真实资料使用缺口；b只补行动；c在b上明确个人参赛冲突；d在a上加该冲突。
7项离线检查通过，基线可重建原真实请求，候选仅改系统政策，不向模型泄漏标签或旧意见。既有独立主体不读标签/主审意见核过四稿及方案，逐稿结论一致且材料接受；原生final/作者原件逐字核验及submit/replay通过。没有候选模型结果，不宣称语义修复完成。
本轮Provider/Key读取0，原4HTTP/66591known/0unknown费用及前三次/facts双审保留，144件库存与seal核未变，冻结2b14583e clean。automation PAUSED。
**下一动作：** 实现并离线验证有界completion断点诊断入口，继承已接受facts/native及生成/工具结果、全部历史费用；先核b/c/d，再由a的新实际completion结果直接进入后续链路，不重买成功a或前三次。现有continuation不支持该断点，不能直接套用。新费用范围/版本/期限须在入口可审查后具体核定，候选未实测前不授采用。
当前无新付费入口，无需Key；8份离线请求不是8次授权，不扩原grant期限/范围。预制全文不是实际应用/fresh，尚未产品或15项资格。
证据：data/evaluation/results/completion_necessity_offline_20261024.json；方案和竞争解释见data/evaluation/fixtures/completion_necessity_20261024/README.md；工作卡沿用docs/plans/2026-10-24-sol-output-format-recovery.md。

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
下一步实现并离线验证有界completion断点诊断入口；已独立核材料公平性，未实测前不宣称机制有效。
不重跑成功前三项，不改闭批原件或补签坏意见；断点续接须显式继承已接受facts/native和失败费用，当前无需Key。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

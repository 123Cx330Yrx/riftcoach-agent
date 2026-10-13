# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：J1/J2授权批已关闭；执行1708c0cd/CI38372269298全绿，4完整响应/4真实双审/4submit。原件和历史缺口保留，automation PAUSED；主阶段8E未完成，普通无付费项目工作继续。

## Active Work Package

**目标：** 让真实事实错误被检出后得到正确修法，取得同版本质量证据并接入真实Agent消费。
**最新证据：** J1两臂正确保留；J2两臂均检出14/15段真错，逐项解释、来源、修法和其余正确内容通过真实双审。全部initial、report_assessment=null，无真实编辑。四次native唯一终答/作者原件与checkpoint实核，strict replay/seal成功，86原件及4观测SHA不变。
**本批成本：** 4 GLM-5.3/high、4 HTTP、Flash0、67128known tokens、unknown0/receiptless0/未发0；估价0.829504元非核实账单，活动332.094秒/Host2173.172秒。唯一runner正常退出，原授权未延长，无重试补发。
**方案裁决：** 基线没有复现旧漏检/错误修法，两臂皆过无改善证据，关系教学候选不采用。不再更换熟悉固定报告重买同类教学对照；不删初评、不换schema、不用关键词或接近阈值代替语义。现有完整来源/初评/编辑/终评链保持。
**具体证据：** `docs/plans/2026-10-13-relation-joint-result.md`；`data/evaluation/results/document_relation_joint_result_20261013.json`与close_audit、host_evidence、close_state。授权前准备和校准只按原日期解释，不冒充业务运行结果。
**无付费接续结果：** 四份实际意见的issue完整进入编辑，advisories按既有合同只留journal；10项作者编辑夹具绑定完整终评，J2必须同时修14/15才恢复正确稿。原15同输入/time600教学与J1 baseline相同；旧资格入口逐项拒绝当前组合。机器证据`post_joint_consumption_20261013.json`，没有真实模型编辑/终评或资格。
**下一动作：** 实现隔离的前瞻initial/revision/final证据入口，复用现有workflow及共享预算，适配run外作者/checkpoint、case/stage库存、实际请求观测，贯穿submit/下一发送/replay/seal；先做无付费整链与故障验证，禁止直接复用缺门的旧full15执行入口。具体范围见`docs/plans/2026-10-13-post-joint-consumption.md`。
**依赖与边界：** 本批73源码/9文件包、旧两包69/73源码及旧六批372原件SHA不变。旧U2无native/候选未发、H5错误修法、T9上游根因undetermined不撤销；新证据熟悉来源非holdout，不拼资格。正式15、自然消费、8E及全部下游仍未完成。
**验收与失败决策：** 方案需同时覆盖正确保留、真错检出、修法新增断言及真实编辑消费；结构通过不能推语义可靠。已有授权内普通步骤直接执行，涉及新模型成本时先形成具体可审查范围。

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

以canonical和上方工作卡为准：接线审计已完成，下一步是前瞻三阶段证据入口的无付费实现与整链验证；不是再次审计或重买教学对照。旧原件和缺失项、关系候选未采用、automation PAUSED及全部产品依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

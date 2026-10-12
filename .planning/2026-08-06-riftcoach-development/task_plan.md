# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 让真实事实错误被检出后得到正确修法，取得同版本质量证据并接入真实Agent消费。
**起点：** H5正确检出中单早死均值不接近，却给出错误否定区分的修法；原生双方拒绝。S8仅有响应未认证，所有旧资格/封存缺口独立保留。
**本包已完成：** 新私有入口指定run外作者答案，提交与下一请求前核库存和作者/native一致；33项相关离线检查通过，含等待/分离提交失败传播及受锁发布。唯一新短报告完成真实作者落盘/check-answer/native/submit/严格seal，14公开命令exit0、26演练原件不变。transport明确为模拟；项目Provider/HTTP/tokens0、业务submit0、资格0，未重审旧任务。结果见 `docs/plans/2026-10-12-host-workspace-repair.md`。
**当前下一动作：** 检查评审修法到编辑消费的合同，用H5与既有正确全文反例比较如何约束新增替换断言，先验证表达能力与相关失败分支，再决定必要模型实测。policy已有逐项核修法与同类数字例，不把重复提醒当有效方案。
**依赖与边界：** 验证入口的paid run关闭；未来业务范围/计划/成本独立冻结，不能借本包重买V2/H5/S8。旧47/26/14/146原件与失败裁决保持，automation PAUSED。真实native演练只证该次本地整链，不是模型稳定率或产品资格。
**验收与失败决策：** 方案必须能表达正确保留、真实错误和修法新增断言的反例，且实际编辑消费可达；不能由结构通过推断语义可靠。证据反驳当前设计就改设计，不自动付费重试。

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

以canonical和上方当前工作卡为准：工作区修复完成，下一项是H5修法机制的无付费合同对照。未来付费范围尚未选择或启动，正式同版本15及所有下游依赖保留。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

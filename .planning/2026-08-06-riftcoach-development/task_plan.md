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

**目标与依据：** 撤回把执行准备就绪当作重新展开15例依据的决定，核清原语义失败是否获得实际修复；用户本轮“继续”只接续无付费审计。
**起点与新增证据：** 35次执行/资格入口已有离线验证，但3份旧失败和2份正确对照的完整请求与当前重建结果全部相同；旧错误响应仍结构合法，semantic_approval=false。两处误报、一处修复覆盖分歧未获新修复证据，原主审/独立意见及700原件保持。
**已完成路径：** 只读固定public seal → 当前完整请求构造器 → 比较全部请求字段 → 当前结构校验 → 引用原Host记录；不重签、不请求模型、不新建Host任务。脚本及结果见`audit_full15_repair_readiness.py`和`full15_repair_readiness_20261013.json`。
**方案裁决：** 撤回37.167104元新整批提议，准备原件及工程代码保留但退出当前执行队列。J1/J2无改善证据；不再同义教学、恢复失败重评/scope_checks原型、删初评或换字段后碰运气。具体反证与取舍见`docs/plans/2026-10-13-full15-repair-readiness.md`。
**交付与验收：** 原件不变、完整请求比较可复现、canonical/本卡/原执行提议一致撤回、相称检查与提交。无新付费、新资格或产品阶段完成；结构校验不是语义裁判。
**下一动作：** 在三类真实失败及已反证路线约束下选择具体修法干预，说明实际任务约束的变化及可否定观察；当前尚未选定有新机制依据的修法，不创建新模型成本队列。普通无付费工作仍获授权。
**依赖与失败边界：** 旧15三批10通过/3语义拒绝分歧/2operator未认证不拼资格；两个真实Host演练仍缺final正例，不开第三次简化演练。旧H5错误修法、U2漏检及native缺失、T9上游根因未知均保留。automation PAUSED；自然消费、阶段间取消和下方产品依赖继续保留，工程进展不能抵消语义阻断。

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

以canonical和上方工作卡为准：本轮修复就绪审计已证当前完整请求未变；新15付费提议撤回，工程准备保留。下一项是有历史反证约束的具体修法选择，当前没有已证明修法或新付费队列；automation PAUSED，8E及全部产品依赖保持未完成。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

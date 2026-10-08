# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 将已验证的必要编辑能力接回现有原15与自然Coach验证，保证实际错误被修正而正确内容保留。
**当前动作与边界：**

2026-10-08：获授权的既有完整重评诊断已执行并关闭；e494f531/CI37715563600三项成功。
实际仅发1次GLM-5.3/high，actual-mixed完整返回76/needs_revision：补刀真错检出，
早死口径误报仍保留；公开解释承认block14全样本限定，却仍要求block4继承相邻中单范围。
主审及真实独立审查一致拒绝，原生final事件已导入，执行器以scope_resolution_host_rejected停止。
第二项未发送，无Flash、无改稿、无重试。20575tokens、unknown0，未缓存估价0.30558元；
活动132.875秒、host148.047秒。20份原件摘要及公开白名单封存golden_scope_resolution_result_20261008.json，
SHA e1e0b60d555bb9df04bb6e43ce37ca7be9d5d63e100ff69dfb0289ddab19387d。
已否定现有完整重评足以修复本例的假设；不是断流、额度耗尽或上下文未送达。
不据单次结果断言模型一般能力或内部原因；不追加提示变体，不借剩余一次重开实验。
原15仍严格2/15，必要编辑的已通过证据保留；默认产品、8E及自然Agent资格均未变。
下一动作：以本次反证和ADR0110/0111既有结果完成整任务方案取舍，明确误报识别/编辑职责、
自动触发与五次共享预算，先给可执行控制流及离线反例，不能靠跳过中间误报或省略终评接入。
现有重评仅在结构校验失败时触发，合法语义误报不会自动触发；自然整链加重评为6次，当前上限5次。
仅增加重评或提高输出额度不作为本问题修法；任何新付费/采用标准/产品预算变化需具体方案授权。
四块联动、本人Training、前端审美/必要重做/头像、Memory、Worker/DB/API/Workbench、
身份运维、两树整合和学习仍沿原依赖保留。证据与后续取舍见docs/plans/2026-10-08-scope-resolution-result.md。

上一批真实三阶段全部通过，3调用45538tokens、unknown0、约0.4230100元；
封存及适用范围见docs/plans/2026-10-01-review-bound-edit-result.md。

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

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
具体下一动作及失败分支仅维护在上方 `Active Work Package` 的“当前动作”，此处不复制动态排程。
全周期按交付方法执行，工作包结束或出现关键反证时复核策略与下游依赖；普通工程调整沿用已有授权。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

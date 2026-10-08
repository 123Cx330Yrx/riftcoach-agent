# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 修复完整初评对正确全文的误报，同时检出混合真错；保留已有必要编辑及fresh能力，不用后续改稿抵消初评失败。
**当前动作与边界：**

2026-10-08：三例完整初评的最小执行接缝已完成。先原混合例、再明确中单真错、最后完整正确稿；
完整来源/policy/schema不变，Host预期/旧意见不进请求，标签打断列表结构风险仍在。
诊断selector精确恢复旧请求仅做身份核验，真实发送/回执绑定新四消息；只用GLM，Flash0。
复用现有端点、预算、Host clock、create-only批目录、native-final双审及共享关闭锁。
默认router/contract/原15资格入口继续拒绝新视图，诊断不能自动转授任何产品资格。
新入口14项检查通过，scope+准备器+入口共37项通过；晚提交竞态1项、默认回执/未知用量16项通过。
独立复核指出两项冻结依赖遗漏已补，预算/绑定/关闭无其他阻断；57项源码冻结，真实主体预检
及精确重建通过。工作卡：docs/plans/2026-10-08-document-review-diagnostic.md。
冻结SHA bdb678d80a8568443ce92d01ec3a636542a4ebe6f5c6ea0b5ecf6d63a1f376a6。
**下一动作：** 请求本冻结计划新增最多3次、290304tokens、900活动秒、86400Host秒、保守
未缓存估价4.288512元授权；同提交公共CI全绿及执行前主体预检通过后执行，不借旧授权。
**失败分支：** 首实质/来源/身份/传输/预算/Host失败关闭、不重试；语义失败否定当前呈现对该例
的充分性，传输不完整仅算未知。三例均经真实全文双审接受才选择后续同版本质量验证。
当前Provider0；核心误报未证明修好，原15仍2/15、8E未完成。最终CI另核，未启执行或等待器。

既有隔离Coach五槽整链（361378/401920预留）仍仅离线证据；后续Worker/DB/API/UI、journal及
自然任务消费沿下方依赖继续。上一混合尾链真实1调用11894tokens、unknown0、编辑reason双审
拒绝且fresh未发，原件关闭保持；本新筛查不改写该结果。
仍在原D盘，迁机包停在a5ab4625快照；后续提交需另行fetch。自动接续保持暂停。

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

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

2026-10-08：完整初评文档呈现已完成可审查的三例准备，决定值得一次窄范围筛查，仍可能被否定。
先原混合例，再仅明确中单范围的真错反例，最后完整正确稿；保留所有来源、完整policy及schema，
不带旧意见/Host预期。两份原例历史输入和实际回执精确绑定，合成反例没有历史执行结果。
请求原件已不可覆写导出并只读核验；公开准备manifest及18项检查完成，独立复核无硬阻断。
具体风险：Host段号标签打断列表分组，原文无损不证明结构/理解等价；三例是已知同源而非holdout，
历史JSON失败不是同期控制，不能把呈现改善归因单一JSON变量。
工作卡及决定：docs/plans/2026-10-08-document-review-probe.md。
**下一动作：** 复用真实回执/双审/关闭机制准备最小执行接缝及完整冻结，不再扩案例/改提示。
拟最多3次GLM初评、290304tokens、900活动秒、86400Host秒、未缓存估价4.288512元；
尚无runner/执行冻结或新付费授权。最终提交公共CI及真实身份预检通过、具体新上限获准后才执行。
**结束判据：** 实际执行逐例全文双审，首语义/来源/身份/传输/预算失败即停不重试；语义失败否定
该呈现对该例的充分性，传输不完整仅算未知。三例全过只支持后续同版本质量验证，不授原15资格。
前提交9ba8dd06公共CI37772680703两项成功、pytest仍运行；最终状态另核，不借旧绿灯。

既有隔离脚本接线已通过：真实Agent工具/Harness/共享预算/存储的五槽满预留361378/401920，
默认contract/router仍拒绝新视图；测试身份注入不是产品接入或真实语义证据。详见
docs/plans/2026-10-08-document-view-integration.md。
上一混合尾链已关闭：Flash修好block6并保留block4，但reason误报/无据排除导致双审拒绝，fresh未发；
1调用11894tokens、unknown0。该结果不能由后续离线准备覆盖。
当前Provider0，核心误报未修；历史原15仍2/15、8E未完成，旧批关闭且自动接续暂停。
仍在原D盘，迁机包停在a5ab4625快照；后续提交需另行fetch。

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

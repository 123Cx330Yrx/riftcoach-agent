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

2026-10-08：文档呈现三例完整初评真实双审全部通过并关闭：原混合82/needs_revision仅block6
真错；明确中单反例68/needs_revision检出block4/6；正确稿96/pass且无实质误报。此次核心
混合反例未复发，不能外推可靠率或证明JSON根因。编辑/fresh未测，历史原15仍2/15、8E未完成。
3次GLM/Flash0、45206tokens、unknown0、活动134.891秒、未缓存估价0.510748元，无重试。
同提交d8f83ca5公共CI37776987790全绿后首次执行；52份原件及真实native事件回放通过。
第二例独立首final把报告错误写成已检出问题的漏检，导入前中性澄清、作者重新独立核查，
纠正final才导入；两份原事件保留。未改Provider原件或给独立审查者提供接受答案。
结果工作卡：docs/plans/2026-10-08-document-review-result.md。
**下一动作：** 离线复用DocumentReviewWorkflow及既有编辑/fresh、共享预算与事务，适配新
候选身份及原15资格读回；核已有回归、补实际缺口，独立代码复核后完成同版本冻结准备。
不得增加第六调用或审计字段，默认生产身份/质量门保持；本批无新增付费权限。
**失败分支：** 新请求/成稿fresh/来源/身份/预算/关闭绑定不能完整核验则不准备付费；未来
同版本真实批首失败停止、按最早偏离诊断，不借此3/3或历史2/15授新身份资格。
文档视图五槽361378/401920仍为离线预览，900秒真实可达性、编辑/fresh完整质量与自然任务
仍待同组合验证。自动接续已暂停；上一混合尾链关闭及reason拒绝结论保持，不覆盖旧失败。
仍在原D盘，迁机包a5ab4625为历史快照，后续提交需另行fetch。

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

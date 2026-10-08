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

2026-10-08：原15已关闭批仍严格2/15；5次真实调用72461tokens、估价0.7274096元，
claim-scope:3额外误报未解决。既有必要编辑成功证据保留，不借旧资格、不重开失败批。
现已完成两个完整重评对照的执行入口、真实双审交接和冻结：实际混合例须撤回误报并保留真错，
明确中单的合成反例须保留两项；使用历史意见不是盲测，不称窄裁决或新的原15通过。
复用现有GLM/high、schema、previous_raw/issue_resolutions、共享预算、CI/身份门，不修改产品。
新15项离线回归通过；最终交接调整再验2项通过。独立复核无阻断；真实只读native预检通过，
正文仍不可读，沿既有native-final-attestation-v1，未来可用性不保证。
修复显式null字段可遗漏和关闭/迟到提交竞争；OS锁涵盖发布与收尾，未知用量不释放或重试。
冻结golden_scope_resolution_preparation_20261008.json，SHA36dcf2f4db83c19e6af08f8a8ff6356b698f89627a5e8f6d28d7e654ab5f0e95。
最多2次GLM调用、193536tokens、600活动秒、86400host秒，保守未缓存估价2.859008元。
Provider新增0；尚未获本方案付费授权，执行目录未创建。下一动作：核对最终提交公共CI全绿，
取得本冻结方案授权后执行逐项真实双审，首失败停；旧35次批余额不转授。
已核对产品整链：自然生成/工具两次+初评+重评+编辑+fresh需6次，产品仍限5次。
即使诊断通过也仅为能力证据，不自动插入运行时或调整预算；采用前须解决触发和整任务资源路径。
8E、自然Coach、当前组合Worker/DB/API/Workbench未完成；四块联动、本人Training、
审美/必要重做/头像、Memory、身份运维、两树整合和学习沿原依赖保留。
详情见docs/plans/2026-10-08-scope-resolution-diagnostic.md。

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

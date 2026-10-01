# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行提交6e322f69的新完整批已关闭，严格完成1/15；第二例GLM初评正确检错，Flash改文
纠正原错误但复制内部编辑指令，双审拒绝。旧宿主密文取证已在本批真实交接通过。
3调用48001tokens、unknown0、估价0.5228656元，未发fresh及后13例。旧批不重开。

## Active Work Package

**目标：** 使已检出的真实错误修订成干净、保持正确内容的完整玩家报告，恢复原15及自然Coach验证。
**起点：** 本次原始Flash回复含system前420字符，非保存拼接问题；现有标题/长度检查放过。
**已完成：** 83原件封存、真实双审拒绝、修前strict回读1/15。新增实际请求system完整长段
复制检查，留存原响应后拒绝，不清洗、不重试；真实失败离线回放拒绝，另12份历史稿未触发。
应用模拟整链证明不发布、不发fresh。模型、high、提示和业务标准不变；共享源码manifest
刷新后不借用历史1/15成为修后资格。详见docs/plans/2026-10-01-editor-policy-echo.md。
**比较结果：** 显式替换可保留未改字节，但旧来源目录不兼容当前31/32引用，终评亦是旧构造，
且after仍可能复制指令；不是充分修法。历史只读预览身份兼容已修，相关64项通过。
**新增实现：** 未注册的必要编辑适配器复用现有revision槽和预算，当前来源/完整意见不变；
工具回包与原子组装绑定当前全文终评。22项适配器、11项三调用诊断、25项旧原型/关闭批离线通过。
**当前动作：** 新入口独立复核已通过，冻结71f544b5…b9be已完成；完成最终提交公共检查，核对新增3调用/
290304tokens/900活动秒/估算1.7154048元授权后，验证必要编辑→条件fresh→正确保持。
没有已证明的生成修法，不注册产品、不追加第六次调用、不重开15例。详见ADR0115。
**失败与授权边界：** 新完整批授权已执行且首失败关闭；未用余额不是旧批重试许可。
工程防护不替代模型质量；下一具体付费范围准备完成后结合原授权核对，旧回执不回填。
**后续：** 完整原15→自然Agent生成/工具/纠错→同run真实DB/API/Workbench；8E仍未完成。

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

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

ADR0109角色候选已取得来源修复后真实自然生成/工具/审查/文件读回证据，以及当前1.5.1合同下
一例原归因错误稿的真实首评→Flash改稿→GLM终评96/pass。但随后原正确全文被误报，配对未通过。
原15为1例host接受、1例失败、13例未跑；这不等于1/15稳定率，也不能拼成产品资格。
原知识日期错误稿未被本批自动修复；普通编辑成功不等于独立补漏能力，默认产品与8E边界不变。

## Active Work Package

**目标：** 修复已确认的审查交付指令冲突，隔离当前请求与历史证据；同时完成下一语义诊断的方案去留。此包不是“核心误报修好”，不能由工程通过推导质量准入。

**起点与差距：** 24ddf358 / 公共CI35908526036三项通过，4707 passed、154 skipped、129 subtests passed。旧请求原15实测1例真实纠错成功、1例正确全文误报、13例未跑；全部原件不变。旧RoleNote请求system只允许submit_report_review工具，却在user消息重复要求输出JSON文本，属确切交付冲突，尚无证据证明它造成误报。

**实现路径：** 后继RoleToolDeliveryReviewWorkflow只移除与实际工具schema完全匹配的文本头，保留system、全文、来源、字段、恢复原响应和编辑请求；request_delivery标记进入metadata、journal、candidate与fingerprints，更新两个活动manifest。旧builder/原闭批plan保留；当前资格固定使用新builder，显式legacy入口仅供历史回放。旧Flash比较预览发现新身份与旧请求混用，修为冻结原计划、历史分区和永久关闭CLI。

**验收与预算：** 全15输入/正文/source/schema不变；真实SDK序列化与应用链路检查；旧3调用重建同一成稿与journals，默认当前回放拒绝旧请求；旧缺severity仍拒绝，五调用预算/编辑/85分门不变。使用提交公开资料，不依赖ignored runs。此包0新Provider调用，无新付费计划。

**方案裁决：** 同请求重复最多证明不一致，不能直接选修法；聚焦范围首读缺新增机制且挤占五调用；任意自由文本输出不能确定性恢复实际评分/类别/安全/引用字段。独立复核补出“自由文本首审→可选编辑→结构化终评”在五调用内可表达，但正确且不改稿分支仍把原全文送同一失败审查，不能把错误后移当修复。旧去重/meaning-first反例必须保留。这些方案当前不足以批准新语义实现或付费批，也不证明语义问题无解。

**当前结果：** 143项不同离线测试、全15初评/恢复及SDK审计、独立审查通过。旧导出键序与原hash不一致按原导出字节绑定处理，原件不改；manifest两profile可加载。

**当前动作：** 提交本包并核验对应公开CI。之后围绕正确全文无需改稿的发布核验路径核查审查职责，找到能影响实际误判且保留采用标准的最小干预；未找到前不重复原样付费，不用补字段/提额度代替语义修法。

## Dependencies and Follow-through

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

# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

执行状态：用户已确认6次候选并完成零付费接线；新worktree codex/natural-duty-six，旧冻结目录保留。
结构及模型双pass不授语义资格，候选始终拒发布；无新付费授权，automation PAUSED，8E未完成。

## Active Work Package

**目标与结果：** 最小保留机制诊断设计及离线请求已完成：终稿质量与相对原稿保留分别输出，核心12个请求有支持后才进入8个控制；未具备实测条件、无付费授权。
**实际路径：** RecentReview → Runtime单一共享预算 → AgentLoop/本地RAG → 双初审 → 程序预览/唯一应用 → 双fresh。
**边界：** 新1.6.0合同6/401920/900/单请求300；其余high模型和单次输入输出保持，无Flash编辑请求。
追加检索导致不足两fresh slot时停止；未知预留计入预算，取消后下一发送前停止。
**证据：** b79d2c83/CI38601405819全绿。职责/补丁/候选84项及清单4项离线通过；真实应用对象、替身模型且socket禁止。
错数字/空来源/错目标段/删除引用即使双fresh pass也不发布，保留意见与实际改文；不是自动语义检出证据。
15个原输入/原标签按1.6.0构造30个完整初审请求，实际新稿前不填fresh SHA；清单ready/authorized/qualified全false。
**发布判断：** 所有候选成功仍返回FAIL给Harness，另记内部unqualified outcome；未伪造Host验收。
工程接线不证明自动语义冲突检测或真实质量；详见ADR0118及natural-duty-six-implementation。
**旧证据：** 原冻结854源码/3包/103原件及seal一致，不修改旧裁决；固定报告通过仅开发证据。
**方案取舍：** 空来源、无引用、跨段修改按完整上下文判断，不加字段一刀切门。非重叠不能证明语义兼容；开发Host不作免费运行时服务。
**本包证据：** 不同原稿/同一新稿在当前fresh中不可区分，比较原型输入可区分；完整来源/两稿、旧Provider拒收及超限拒绝已验证。30个同稿形状探针最大55916，新增8项+清单4项通过；不是语义检出或真实fresh证据。
**成对材料证据：** 原五局来源/任务/知识完整保留，数值前提复算；24个请求形状、20个不同摘要（基线8/比较12）、最大46578。新增9项+原探针8项通过；注释/ID不进入请求，整篇预期与模型/独立结果均空。
**诊断准备：** offline-preservation-diagnostic-v1两臂旧Provider拒收，notes与终稿五字段分开，全文/标签隔离保持。20次去重上限1523372tokens/6000活动秒，合同估价25.294176元非账单硬限；新增7项及原17项共24项socket阻断检查通过。详见docs/plans/2026-10-15-preservation-diagnostic-design.md，ready/authorized/qualified全false。
**下一动作：** 核实既有独立作者路由并独立审材料/判据，再完成隔离transport、原件观测/native/预算及只读seal的零付费接线；不新建Agent，完成最终CI和冻结准备后才请求新费用授权。
**失败决策：** 只证明信息可见性；若超限则拒绝，不裁剪全文。若比较输入无法表达正确保留与合理纠错，不进入模型开发验证；表达可行也不能推断语义准确率。
f3717d27/CI38673691931最近查询仍运行，web/packaging/Postgres已过，未报后继全绿；旧历史夹具缺口已修且原摘要/封存保持。
发布门关闭，不另开付费批；6次已确认，不重复请求。所有原15、自然产品、前端和学习依赖保留。

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

以canonical和上方工作卡为准：诊断设计与离线请求已完成，核实既有独立作者路由、独立审材料/判据并完成零付费执行边界接线；最终准备就绪前不请求费用批准或发送模型请求。
不恢复旧付费批，不直接购买正式15；发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

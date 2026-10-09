# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 回到用户持续要求的完整15例主线，解决已暴露的初评语义分歧与编辑定位协议问题，再取得同版本完整链证据。
**起点：** 原15前三例完成；剩余十一初评已收齐，十接受、一分歧；三轮尾链均在首例硬关闭，未新增认证尾链。五份封存435原件SHA已核一致，旧runner退出。
**方案与范围：** 已实现block键归组编辑与成对全文教学的隔离候选，不能用全文唯一锚点猜block；attribution泛指与scope修法观测/因果分别处理，不强称一个共同原因。候选见2026-10-09-full15-resumption-candidate。
**实现路径：** 完整来源/历史事实→现有DocumentReviewWorkflow初评→候选严格编辑组装→完整新稿fresh→真实全文双审。保留现行issues/修法字段与五调用上限；不引入全段审计账本。
**验证：** 前一提交的25项接缝及116项相邻证据保留；本轮41项执行/回放及32项编辑/教学相邻通过，最终小改受影响14项补跑通过、不重复累计。固定10例实际发送/完整回放、语义停案/硬停和篡改预算/顺序/run/清单外案例拒绝均验证。独立原生开发复核无阻断，当前root01a12190…/child01a121b7…真实谱系及final路由通过；模拟回复与开发复核均非业务质量证明。
**依赖及失败：** 旧批不重开/补签/借余量；Provider0、新资格0，自动任务PAUSED。候选不充分就淘汰，明确剩余语义与真实执行证据；新付费方案需具体冻结后授权。
**当前下一动作（2026-10-10）：** 用户核清后明确继续，10例范围已落实且计划SHA d976aa1c…aabbd5；提交/核本方案公共CI，具体新批授权后即时核主体/checkout首次执行。28调用GLM19/Flash9、2709504tokens、8400活动秒/86400Host秒，保守未缓存28.4471296元。前一d546bd23/CI37963794076全绿不抵本提交；旧完整15诊断准备为历史提案、不借额度。正式15后置且不得由诊断直接授资格，Training保留、不作当前动作。

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
用户纠偏后回到完整15主线，具体动作以活动工作卡为准。Training/Memory/nullable已交付成果与下游保留，不计入15质量；旧2/15与3/15独立，新资格0。旧批关闭且自动任务PAUSED，不补旧字段、重开或提前准入。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

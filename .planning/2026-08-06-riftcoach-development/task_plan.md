# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 修复正确教练分析被扩义误报和真错直接影响遗漏，进入同版本完整15及真实Agent消费。
**实际起点：** 5×3教学对照15项已全部双审/submit：10接受、4双方拒绝、1Host分歧；三种教学均误报scope:3正确泛指。停止把教学微调当共同修复。
**本次交付：** 冻结a9a68049/全绿CI38104135494唯一runner正常exit0，15calls/known270680/unknown0/receiptless0，未缓存估价3.602360元非账单。严格15真实native/290公开JSON/306原件SHA相等已封存；无编辑/fresh/重试、新资格0，自动任务PAUSED。
**机制与反证：** 完整规则/来源已送达，三组织均误报；sample1 expanded真实分歧和short无依据排他解释保留。sample3修法可由正文补足摘要范围，sample5标题真错不能借正文限制撤销；不追改历史标签。
**实现路径：** 免费SDK检查复建5份issued请求，只改变温度1.0→0.2，全文/schema/模型/high/top_p/时限相等。现有身份拒低温，当前无可发送身份；不读取凭据/构造网络client，不改生产默认或原件。
**验收/失败：** SDK表达不证明服务端接受/遵循或语义效果。整任务初评和fresh均须可达，生成/必要编辑/格式恢复仍共享五调用/原预算；不得加定向第六审查、放宽标准、改正确稿迎合误报或拼跨批资格。
**整链核查：** initial/final完整历史请求均在TimedDocumentBudget委派前拒低温；继承预算归一化还强制1.0。现有整任务不可达，不以SDK表达为接线证明。
**当前下一动作：** 有界温度筛查已实际启动但未完成：`sample-1:baseline` 温度1.0真实调用1次，主/独立双审一致接受 Provider 意见，但 score=74/needs_revision 未命中预期 accept；第二项发送前发现 `role_development_checkout_changed_after_ci`，确认由 operator 临时审查 JSON 写入 backend checkout 触发，按边界停批。临时文件已清理，工作树 clean，严格 replay 与 create-only seal 已完成；候选温度0.2及其余9项未执行，新资格0。结果见 `docs/plans/2026-10-11-bounded-sampling-screening-result.md`。后续需从不再变动的 checkout 重新准备并重新授权，不能重试本批或使用剩余预算。
**证据：** docs/plans/2026-10-11-semantic-comparison-result.md、2026-10-11-post-comparison-mechanism-decision.md、2026-10-11-bounded-sampling-screening-preparation.md及公共seal/close audit/sampling audit/candidate-path audit。后4已有12stage/fresh95/95/96/97；原15库存10/3/2是独立计数，旧第7/11缺口保留。正式15/自然消费/8E及下游未完成。

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
本次筛查因 operator checkout 边界偏离关闭，未验证候选温度效果，不改变既有15例库存或资格。
在新方案前先保持工作树 clean、CI 后冻结不写入运行 checkout；新的真实筛查须重新准备、预检并取得明确授权。
正式同版本15、自然消费、8E及下游联动继续保留，旧批次不重开。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

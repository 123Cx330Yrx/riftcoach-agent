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
**验证与实际结果：** 已授权10例在d790c157/全绿CI37968309635首次执行，方案d976aa1c…aabbd5。attribution全链94/pass；scope:3初评/编辑通过，fresh发送后300秒超时硬关闭；8案未发。5个完成阶段真实全文双审，103原件SHA/46公开JSON及5个native事件严格回放再核通过，独立收尾无工程阻断。旧离线检查保留，不重复计为业务证据。结果见2026-10-10-focused10-resumption-result。
**依赖及失败：** 实际6调用GLM4/Flash2，known81642/unknown预留77868tokens，已知估价0.6973828元、未知不免费；receiptless0。runner退出exit1，自动任务PAUSED。本批不重开/补签/借余量；10例未完成、新资格0，scope超时不是语义反证。有限正证据保留，不宣称共同修法/协议可靠性充分。
**本轮实现与验证（2026-10-10）：** 续接审计更正1d181238只是未使用标量函数/4测试，之前完整时钟与身份互拒表述过宽；58ba12dc回退失败共享集成、旧54检查恢复，三个提交CI均全绿。现已用TimedDocumentBudget复用真实CoachBudgetedProvider账目/自有时钟，完整原始/contrast请求的新时间身份、实际issued SHA、Exchange sender接线完成。25新完整请求/账本检查+4标量+9公开裁决+53旧业务回归共91通过，模型为模拟。旧指纹模块/default/300合同/历史seal原件未改，正式15/资格未推进。
**本轮发送链交付：** b00a9eaf/CI38039283424已success。GLM600/Flash300实际router→共享ordinal/create-only回执→父子进程worker→SDK stream/close/usage→Exchange→初评/编辑/fresh已离线接通；复用旧生命周期和全文业务校验。新旧transport互拒标记、Host身份不发Provider；5个当前manifest组件及总SHA显式更新，旧裁决/seal原字节与历史源码摘要保持。12发送+25预算+4标量共41、104业务/stream、113factory/应用、63旧full15/合同检查通过；后续相关重核不累计。模型输出/450秒明确模拟，真实子进程不联网。本轮提交需自身公共CI，不能借上轮成功。
**本轮执行与取证交付：** 4de565dc/CI38042065301失败于旧scan夹具身份漂移；修公开封存输入/精确请求SHA取材，live旧入口仍拒绝当前源码冒认历史。63旧尾链、7runner、72资格/factory通过。显式time600模式沿既有runner/checkpoint/native/关闭锁/严格回放接通，每案900/5calls/401920tokens及整批墙独立核算；发送/案始终点create-only落盘。迟到完整回包用量已知但不交付，回放不造stage。所有Host/模型为离线替身，不当实审或质量证据；旧seal/裁决原字节保持。
**当前下一动作：** 核Worker续租/取消/失去所有权及发布边界，然后准备具体新诊断范围和成本方案；见timed-document-execution-evidence。Provider0/无新run/资格0、execution_ready=false；本轮需自己公共CI，不借旧全绿或28/45调用余量、不用旧native补签，正式15/自然消费与下游保持未完成。

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

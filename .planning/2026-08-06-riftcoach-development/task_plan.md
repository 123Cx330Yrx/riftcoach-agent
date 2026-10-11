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
**本次交付：** 有界温度筛查 r2 在 `465daf92bfaecb47e800ebc343bd23f21c553220` / CI `38141643942` / plan `8c8fc50de3159dfc42bd02f2a3c53276dc5f537d9dfda2395de4f16f441b94d7` 启动唯一 runner。sample-1 两变体真实完成但 74/78 needs_revision 未命中 accept；sample-2 两变体 96/95 pass，主/独立审查接受且四项 ReportAssessment 全真。第五次请求在 sample-3:baseline 发生 `ProviderResponseError` 的 `assembly_rejected/tool_call_arguments` receiptless 硬停止；实际5 calls/known84081/unknown0/receiptless1，5项未执行，新资格0。严格 replay 与 create-only seal 完成，seal `bc2a89ad…d666de`。
**机制与反证：** 该批没有完成候选温度采用门，不能判断 temperature=0.2 是否改善语义质量，也不能把工具参数组装失败解释成温度、429、401、503或额度根因。四个已审阶段和失败流均按真实请求、原生终答、checkpoint及账目封存；历史批次和正确/错误质量门不重写。
**实现路径：** 运行期 backend checkout 保持 clean，所有主审 notes、临时 JSON、close audit 和 seal 写在 operator 输出目录；提交只接受真实 native final 与精确 checkpoint SHA。该批停止后不再发送、不重评、不补发、不重开。
**验收/失败：** 4个已审阶段均有真实双审；第五次 Provider 流无可发布 JSON，按身份/传输/预算硬故障停批。严格 replay 核 `native_reviews=4`，seal原始文件95/public文件89，结果、失败、未执行及最早偏离均可回溯。
**整链核查：** 初始和 final 请求的来源、政策、模型、schema、温度标记和账目保持绑定；失败回执不伪造为业务stage或native review。未执行 sample-3 candidate、sample-4 两项、sample-5 两项。
**当前下一动作：** 本批已封存并暂停；任何后续筛查须从 clean checkout、同提交CI和新的明确授权重新准备，不能使用本批剩余预算。正式同版本15、自然消费、8E及下游产品/学习依赖继续未完成。
**证据：** `docs/plans/2026-10-11-bounded-sampling-screening-result-r2.md`、`C:/Users/33502/Documents/Agent/outputs/riftcoach-bounded-sampling-screening-20261011-r2/close-audit.json`、sealed file及本批 run 目录；历史2/15、3/15、remaining11和完整15继续独立。

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
本次筛查因 sample-3:baseline 的 Provider `assembly_rejected/tool_call_arguments` 硬停止，未验证候选温度效果，不改变既有15例库存或资格。
本批已完成只读 replay 和 create-only seal；后续若继续，先保持工作树 clean、CI 后冻结不写入运行 checkout，重新准备新 run、预检并取得明确授权，不得使用本批剩余预算或重开本批。
正式同版本15、自然消费、8E及下游联动继续保留。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 在现有教练报告Review→必要编辑→fresh路径集中发现尚未测到的修法风险，修复共同问题后解锁同版本完整15及自然消费。
**起点与差距：** checkpoint六尾链实际仅首案1Flash/11224tokens返回；Host容量故障无native final，硬关闭。有效阶段0；其余五案及首案fresh未执行。21次401无项目操作。关闭结果已严格封存，Provider0旧状态已纠正。
**已选路径：** 只准备claim-scope:6、observed:2..5的新尾链，复用五份真正accepted历史初评，不重买首案/初评、不重新评级关闭批。一个隔离适配器复用冻结observer、完整handoff及seal；旧模块对象/源码/原件保持。
**Host处理：** 原中转不支持Luna；新gpt-6.1-sol子主体真实通信final通过。新计划绑定其原生UUID，代码复核与当前路由预检后，实际阶段仍按checkpoint/SHA/全文policy/native final导入。
**交付与验收：** 只读结果/公开停止记录、真实原件摘要；新五例完整替身往返、语义失败分流/硬故障停止、checkpoint/native/来源/late-close拒绝、旧模块回归和旧冻结重建；独立代码复核及具体冻结方案。替身/通信不当模型质量证据。
**成本与决策：** 拟最多5Flash+5GLM、967680tokens、3000活动秒/86400Host秒、未缓存估价7.862272元非硬封顶。新付费范围未授权，准备不读取凭证或发送Provider，不启动run。六案旧授权不能借余量重开。
**失败分支：** 语义拒绝停该案依赖阶段并继续独立案；身份/来源/native/checkpoint/协议/transport/预算/主体不可用硬停全批，无重试、重评、重开或资格。发现Provider问题集中处理；没有有效新证据不原样重买15。
**限制与依赖：** 首案未认证、两处分歧和共同语义修复保持未完成。旧3/15与历史2/15不拼，新资格0；正式15、自然消费、8E和下表产品依赖保留。泛指不补全称/措辞不升级事实门；ADR0116不复活。
**已完成准备：** 单一117行隔离适配器；20项新旧检查及独立41项回归通过（重叠），实际代码复核native final严格读回/新主体谱系/current-route核验通过，旧冻结和strict replay保持，新五cells/request/identity精确不变。方案d7bf39c634a603b1bcee299de7e7d87e596e258c6c9b4c5afe8bc9c9329aa3e4。
**当前下一动作：** 取得具体新五例付费授权及本提交公共CI全绿后，实时预检/clean exact HEAD下首次执行。详见docs/plans/2026-10-09-remaining-checkpoint-tail-diagnostic.md。

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
五尾链准备已冻结；取得具体新范围付费授权及本提交公共CI全绿后实时预检/单次首次执行。关闭批不重开，当前新Provider0/无run。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

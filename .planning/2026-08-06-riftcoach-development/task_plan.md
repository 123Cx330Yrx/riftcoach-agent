# RiftCoach 当前执行计划

## Goal

在既定阶段0—8和采用标准内，把可靠的模型分析接入真实Agent教练任务。
ShowMaker观摩任务不是整个产品；自然Coach、本人Training、四块联动及前端仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`；事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

2026-10-19：原批第六项HTTP524保持封存；用户单独授权的s03-completion补测HTTP200，22094已知tokens。补测意见与唯一block21修订后的全文均双审接受，真实native/作者字节导入和只读回放通过。三稿六职责由原五项加独立补测取得语义覆盖，不是原六次全成功。累计7HTTP、132730已知tokens、80384未知预留、421.704活动秒；未发布、未授资格，automation PAUSED。

## Active Work Package

**目标：** 把已测必要修订政策接回自然任务，并把下一次实测准备到能保留成功项、手动恢复普通超时的具体入口。
**当前续作：** 同阶段手动续测已实现并离线验证；每次显式调用只重试当前超时项一次，再超时仍暂停。
新候选launcher贯穿新合同/企业Profile/独立grant，成功回执断点只协调；旧批与原件保持。
56项相关检查、13项CI旧测试修复、新候选launcher全链和真实Flash回收补测各1项通过，另49项旧恢复/原生导入/库存回归通过（755.24秒），合计120项；两份受影响配置启动校验通过。
新初始包络10物理调用/739840tokens/3600活动秒/4次手动补测，估价1.0683904元；是待授权包络，不是永久补测上限或实际账单。
公共CI40069863769因旧测试漏传CONTRACT_MODULE失败，已局部修复/13项过；等待本包提交后的精确新CI。
**当前下一动作：** 旧回归完成后统一提交推送、冻结干净执行树及新任务计划，验证真实原生作者路径；尚不要求Key、不发付费请求。
已有独立主体实际行政调度成功，未新建Agent；真实预检与新费用授权未完成前不得报告paid ready。
详见docs/plans/2026-10-24-necessity-natural-manual-recovery.md；automation仍PAUSED。

以下为上包完成记录，旧估价与“仍缺”描述由本节接续。

**刚完成：** 用户要求的a/b/c完整来源再审通过，既有双审/native原件只读重验，原封存与费用保持。
独立开发合同1.6.3及企业Profile已贯穿动态初审/fresh、父子receiver、实际Runtime/预算/trace/session。
20项新接线、103项相关旧回归、26项旧自然链及6项库存检查通过；39份Runtime配置校验通过。
首发边界从实际OBSERVED/空Memory入口捕获，零Key/零真实模型；当前库存另存，不改旧15资格/标签/原件。
**证据：** review_necessity_three_recheck_20261024.json、sol_necessity_natural_integration_20261024.json、
sol_necessity_natural_offline_20261024.json；设计docs/plans/2026-10-24-necessity-natural-integration.md。
**已解决：** 旧自然任务仍使用baseline政策和Pro硬编码的缺口；同政策现在能进入动态全文和同稿双fresh。
**仍缺：** 现有自然Runtime的有界自动重试不等于用户要求的多次手动补测；新实测启动/授权/冻结CI及真实native预检尚未绑定。
**下一动作：** 实现并零付费验证同阶段手动超时续测，保留所有成功项和未知预留；完成新自然任务的具体范围、预算和独立启动绑定。
成功HTTP中断只协调，不重发；身份/来源/协议/语义硬错拒绝，单独审查判断，不按网络补测处理。
**边界：** 已完成三项grant不挪用；当前约0.864元是继承预算估价，不是新费用授权；付费入口未ready，不用填Key。
熟悉开发材料/模拟工程成功不当新语义、原生业务审查、同版本15或阶段/产品完成；旧六项/失败/封存和automation PAUSED保持。
自然六调用与产品五调用差异不靠静默扩容解决，原阶段和后续依赖保持。

## Dependencies and Follow-through

已解除工程回归：旧repair关闭批预览现回读封存；相关31项及后继公共检查均通过。
tasks指纹遗漏发布模式、证据终态恢复载荷缺失已修复，公共真实DB218项通过。Docker与本机
Postgres已恢复：官方停止及两运行目录完整备份，现用127.0.0.1:15432绕过Windows保留端口；
原卷保留、healthy/SELECT1/迁移head已核。配置见workspace_map；当前组合已完成一份自然观摩真实消费，业务验收拒绝，不能外推产品可用。

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 新组合绑定原15输入、实际政策与传输；资格证据必须来自同组合真实回执和独立逐项审查，不能复用旧五例或两份固定报告 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

Canonical checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
三项再审、同政策自然动态接线和手动同阶段超时续测已离线验证。下一步按上方工作卡冻结新任务并验证实际原生作者路径。
旧授权不用于新范围，现阶段不用Key，不自动发送；原阶段及下游依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

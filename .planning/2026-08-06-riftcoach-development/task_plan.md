# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

1.5.4旧manifest严格3/15仅保留历史；1.5.5严格1/15。最新停止批已发生独立审查身份合同失败，
不是仍停在计时原型接入前。旧模型事实证据保留，旧批不补签、重开或拼成新资格。

## Active Work Package

**目标：** 在真实模型费用发生前确认审查链可用，确保同一主体不能通过两个本地文件冒充
独立审查；并让真正独立的结果沿现有执行器、三阶段提交和严格资格回读完整通过。

**当前已完成：** 实际请求SHA与依赖传递、新执行前保护保留；补齐原生协作输入、
qualify来源继承、全部profile新签发拒绝v1，以及私有turn的原生成员关系校验。
最终八文件独立复核accepted=true；169项相关回归完成，专项42及整链聚焦3项通过
（有重叠，不累加）。新的真实独立宿主审查→导入→主审→正式提交→封存回读通过，
使用合成Provider，不授模型或产品资格。旧加密事件仍拒绝，旧失败目录不重开。

**当前动作：** 新v2完整原15入口、原生宿主身份读取、47项相关测试和独立代码复核
已完成。新plan 03c80ae504c5e8f7fac4dbe76188f79d503776720bdfdecde8ca7e26c384640e；
35次/3386880tokens/10500活动秒，宿主等待86400秒另列，未缓存预留37.167104元。
取得包含新入口的同HEAD公共CI及具体新付费授权后执行；旧批不重开。
准备与累计费用见docs/plans/2026-09-30-v2-full15-preparation.md。当前GLM新增0。

**依赖和失败决策：** 新环境/格式须先证明宿主保留真实派发及绑定，不能用本地
JSON补正文、双密钥冒充独立或用旧审查批准新代码。失败、429无final、402余额
不足、真实语义错误分别记录；已完成的后台审查和测试按原始证据保留。未来新
付费批使用新身份、当前提交CI和累计预算及授权；接受样例工程通过不替代真实
初评/编辑/fresh全链和完整15质量门。

**预算边界：** 原15闭批2调用29682tokens/357.719秒/估价0.341556元；remaining闭批2调用
27325tokens/914.422秒/估价0.1930048元；随后计时批另3个完整调用48607tokens，加1个
unknown/incomplete请求。未知用量不算免费。此前控制/尾段另记，不混Codex额度。
本轮无新GLM调用；未来新批需新冻结身份、累计预算、同HEAD CI及具体授权，旧34次不能
作为重开额度。模型/high/1.5.5/产品5调用401920tokens900秒不变。

**后续：** 完整原15真实资格→自然Agent生成/工具/纠错→同run真实DB/API/Workbench；
可独立的产品工作按现有依赖继续，不将质量门与整个Agent产品混为一谈。

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

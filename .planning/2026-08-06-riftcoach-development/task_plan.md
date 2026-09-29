# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

1.5.4旧manifest严格3/15仅保留历史；1.5.5严格1/15。原批host提交缺陷已修；后继批因人审等待中断关闭。
固定示例两控制和真实编辑/fresh均通过全文双审；这不替代完整原15、自然Agent或真实产品消费。

## Active Work Package

**目标：** 将可行的完整上下文审查策略接到真实Agent全链，并验证既有完整原15；
正确报告保持、真错被检出且实际纠正，不能靠手改原稿或降低门槛。

**已获证据：** 低温误报失败已关闭；异领域固定示例两控制正确96/pass保持、真错82/
needs_revision且意见正确。后续Flash实际编辑分清中单2.50/0.50和全样本2.5/2.67，
GLM fresh96/pass且全文双审接受；原其他事实/来源/身份/训练边界保留。
尾段33原件封存da0d73a6…862ab，绑定2328d7dd/CI36383724302。注入旧初评已明确标注，
不拼成连续原15或泛化证据，旧失败不撤销。

**当前动作：** 换号后已推送bb6b98b0，公共CI 36514153114三项成功。前轮错误删减的测试已恢复，
fixture成功结果先验证再封存；原型与受影响整链回归共74项通过（最新541.15秒）。计时采用校验已接入
资格审查器：只接受adopted=true、计划SHA绑定、完整等待/结束回执及wall=active+host累计关系；
漏标记、未采用原型、篡改和进程重启记录仍拒绝。该策略尚未接入新的真实入口，未启动Provider。
下一步是为新执行入口生成独立冻结计划并做离线整链验证，再核预算后执行真实批次。机制、验收差异
与采用边界见docs/plans/2026-09-29-development-review-clock.md；不原样重开已关闭付费批次。

**预算与执行边界：** 原15批2调用29682tokens/357.719秒/估价0.341556元；
剩余14批2调用27325tokens/914.422秒/估价0.1930048元，均unknown0，均已关闭。
两批合计4调用57007tokens/估价0.5345608元；此前控制/尾段的费用单独保留，不混Codex额度。
封存原15的60份和后继46份原件不变，strict仍1/15，不给中断改稿补签或补终评。

**计时方案采用边界：** 模型/high/1.5.5/产品5调用401920tokens900秒不变。
原型建议开发人审整批另计24小时；这不是进程崩溃恢复，也尚未修改已采用的验收时间口径。
采用后先完善新入口和严格计时回读，再准备具体新批成本与同HEAD CI；
既有8eff6222…8f038授权含host时间且禁止自动新批，不能借剩余额度换方案重跑。
本轮未发生新Provider调用；原15、自然Agent与真实消费的缺口未因此缩小。

**失败与后续决策：** 软件缺陷沿完整入口直接修并回归；模型实测失败保留第一次偏离，
先核来源/标准/控制路径，不换示例或换版本借余额重试。15通过才验自然Agent生成/工具/
纠错，再接同run真实DB/API/Workbench。普通工程推进无须再次授权；阶段和产品标准不改。

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

# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 将已验证的必要编辑能力接回现有原15与自然Coach验证，保证实际错误被修正而正确内容保留。
**当前动作与边界：**

2026-10-08 换电脑前小步：竞争范围自选audit不采用为通用修法或产品新增门槛；
仅保留已知争议目标的诊断价值，依据和潜在政策张力见ADR0116最后一节。未证明模型内部根因。
最近批实际问题清单正确但audit漏项的结论不变：1调用15888tokens/0.186804元，原15仍2/15。
批次已关闭，原生双审及20原件封存保留，不重开、不转授余额、不补字段重试。
主工作区46项tracked修改、137项untracked及本地壁纸研究素材、三批原件/需求资料已做本地恢复包；
未覆盖主树、未提交其脏文件，实际尚未转移电脑。包不含密钥/DB/Codex宿主历史，具体恢复边界
见docs/plans/2026-10-08-machine-transfer-handoff.md；新机器不要把旧worktree指针当独立仓库。
下一动作：完成新机分支、原件/overlay、宿主及环境预检，再围绕完整review→必要编辑→fresh
提出不依赖自选audit覆盖的可执行任务合同和负对照；复用现有能力，遵守ADR0110/0111五调用
及业务标准，不新增未准备的付费实验、不借单次改善授资格。自然Coach/真实产品与8E仍未完成。
资格回放性能采样已定位重复投影，尚未改代码或删测试；前端审美/必要重做/头像、四块联动、
本人Training、Memory、Worker/DB/API/UI、身份运维、两树整合和学习沿原依赖保留。

上一批真实三阶段全部通过，3调用45538tokens、unknown0、约0.4230100元；
封存及适用范围见docs/plans/2026-10-01-review-bound-edit-result.md。

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

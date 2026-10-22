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

**目标：** 拒收不能再次丢掉已经收到的公开审查意见；在下一次付费前验证实际留存/失败/封存消费路径。
**事实：** 原HTTP200/high请求被reasoning_identity拒收；客户端丢弃工具参数，仅存用量/计数。
用户截图的high与21758/6312精确用量强关联该请求，但不能恢复原响应effort或补签语义通过。
**实现：** 现有非流式接收器在采纳前保存唯一schema有效公开工具参数及UTF8/wire SHA到worker-result，
标记仅诊断/未业务验证/不允许发布；不保存私有推理、普通消息、坏参数或实际Key回显，接收标准不变。
实际store=False且没有响应ID，当前无可用取回路径；客服核查可选，不再卡住客户端明确修复。
**保留：** 旧seal1d0a2f49及70项库存再核未变；6HTTP/80137known/145824unknown/retry1保持。
**验证：** 92项接收/SDK/子进程/应用及初次封存通过（37.57秒）；8项整链补验通过（291秒），分组重叠不相加；正常四审查、唯一应用、恢复/只读回放/库存防篡改均覆盖。
**下一动作：** 提交修复并核精确HEAD公共CI，再以可保留结果区分元数据冲突与语义质量，明确必要诊断决策，不原样重复付费。
**完成边界：** 只能证明本地工程路径；原响应内容缺口仍未知，不能声称渠道/语义问题已修好。
本轮新增付费/Key读取0，不重开旧封存、不交付新入口、不改原授权截止或产品标准；automation PAUSED。
工作卡/事实见docs/plans/2026-10-22-sol-credential-wait-recovery.md与sol_reasoning_identity_diagnostic_20261022.json。

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

以canonical和上方工作卡为准：留存与失败/回放整链已完成；提交后核精确HEAD公共CI，不把找客服当硬前提。GLM产品采用保持，厂商迁移未决定。
复用原稿与历史成本，不重开旧封存；当前发布门关闭，8E及全部依赖保持。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

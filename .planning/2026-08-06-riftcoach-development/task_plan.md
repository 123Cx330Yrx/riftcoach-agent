# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

## Active Work Package

**目标：** 解决正确教练分析被扩义误报与真错修法直接影响遗漏，准备同版本完整15与真实Agent消费的质量证据。
**实际起点：** 后4接续全部通过，fresh95/95/96/97，12stage真实全文双审/native；12calls/known202229/unknown0已严格封存。原15库存10通过、3语义拒绝/分歧、2未认证，不拼跨批资格；旧第7/11不补签或重买。
**本次交付：** 同HEAD89f2408c/CI38068536698首次执行，runner正常exit0；12真实native只读重放、138公开JSON/260原件SHA一致，seal a9873491…51feec；自动任务PAUSED。
**读取限制：** 原合同Codex0.153.4封存通过；0.162 alpha新增turn.rootTurnId导致12原生整体SHA不同，严格门拒绝，终答/dispatch不变。升级客户端兼容问题与Provider业务结果分开，原件/旧封套不回改。
**独立收尾：** 指定0.153.4全链严格replay exit0，12事件/完整seal相等、260原件不变、138白名单一致；工程唯一native final实读accepted=true，非业务重审，跨版本限制单独保留。
**机制与反证：** 两处误报解释已找到正确数字却选错实际命题，规则和扩展示例已存在，继续叠同义教学无区分力。短教学同样未全过，扩展教学有多例正证据，不宣称教学负担/中转为根因；scope:4摘要/正文分歧独立保留。
**实现路径：** 保留完整source、block-keyed编辑和fresh，静态对照只替教学后缀；5固定实际请求×3组织（原扩展/既有短例/实际命题→全文范围→来源冲突→直接修法），非policy消息/schema/模型/时限逐项相同。scripts/prepare_document_semantic_options.py及公共preparation可重建；当前execution_ready=false。
**验收/失败：** 正确泛指不得补全称、明确真错不得借正文免责声明撤销、修法须覆盖已确认直接影响。字数/协议/单次分数不证明机制或资格；失败保留，Host分歧不下传。
**当前下一动作：** 用 `scripts/prepare_document_semantic_comparison.py` 生成并验证 5×3 完整请求包，随后做当前真实主审/独立主体预检；具体成本为 15 次 GLM、1,451,520 tokens、9,000 活动秒、86,400 Host 秒、估价21.44256元（非硬封顶）。在新的明确成本授权前不发 Provider，不重开旧批，不把静态材料当质量资格。
**证据：** docs/plans/2026-10-11-remaining4-time600-result.md、2026-10-11-semantic-decision-preparation.md、2026-10-11-semantic-comparison-plan.md及所引seal/close audit/preparation；`scripts/document_semantic_request.py`、`scripts/document_semantic_host_task.py` 和 `tests/test_document_semantic_comparison.py` 已通过相关回归。历史各批独立、新资格0，正式15/自然消费/8E未完成。

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

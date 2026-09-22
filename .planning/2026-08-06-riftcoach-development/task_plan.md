# RiftCoach 当前执行计划

## Goal

在既定阶段 0—8 和采用标准内，把可靠的模型分析接入真实 Agent 教练任务。
当前 ShowMaker 观摩任务不是整个产品；自然 Coach、本人 Training、四块联动及前端等仍在原路线内。
方法入口：`docs/plans/2026-09-22-agent-delivery-method.md`。事实入口：`docs/project_execution_state.md`。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
- Status: in_progress

本轮已完成策略清理、公共检查及两例真实验证：核心混合例完整成功，全称例正确改稿后在格式恢复中新增误报。
第二例整链拒绝，停止付费批并关闭business入口；后两例未运行。产品仍被误报及完整资格不足阻断。

## Active Work Package

**业务目标：** 同一完整报告与来源下，修复真实错误、保留正确样本描述，通过可靠复评后交付；
当前先确定造成原生审查误报的可干预因素，不先增加新评审协议。

**依据和起点：** 采用完整上下文标准；后端基线 `5578685`。
354d752 的原生混合例出现误报；483f91d 定位臂曾修真错/撤误报，完整意见臂仍误报；
6c22e93 独立编辑修真错、保留正确段，两状态终评仍误报且有字段/恢复映射错误。
这些不是同一输入/同一任务的严格因果对照，不能先认定是意见锚定或模型能力上限。
证据与已撤回结论见 `docs/plans/2026-09-22-last-push-audit.md`。

**当前实现路径：** `app/product/native_coach_composition.py` → `NativeBusinessReviewWorkflow`
（`app/evaluation/golden_native_issues_review.py`）→ 实际请求/验证/修订；
输入与政策还来自 `golden_semantic_review.py`、`golden_semantic_sources.py`。
原已撤回 two-state 仅作反例，不恢复其运行；复用现有请求准备、回执与产品预算工具。

**已完成的确定性修复：** business v2识别JSON后的尾文并保留协议失败，停止自动业务重判；
93项聚焦回归及真实两例离线回放通过。成功例保持，失败例不再发送第4次请求，但不能转成成功。

**仍需作出的技术选择：** 怎样获得可靠的合法输出和完整上下文判断。JSON模式本来已开，
官方未公布可替换的strict schema/required工具能力；任意自然语言尾文可能含真实问题，截尾或
只保持原JSON字段不能保证无损。不得把未选定替代写成只差实施。
下一方案须给出具体输出接收/恢复路径，用本轮真实尾文及真假问题/矛盾尾文反例否定不可靠转换，
并覆盖生成/工具/审查/修订总5调用，不能仅让standalone可达。尚未选出已验证的通用替代，不先铺新框架。
本轮不补提示重开付费批、不截取非法响应中的pass、不将low事实错误统一放行。具体证据/已否定方案见last-push-audit最新节。

**竞争解释与分支：**
- 实际全文/来源在组装中丢失或改变：用字节/字段对照定位生产方并修复；完整保留则排除这类丢失解释。
- 当前政策/Schema/验证任务有冲突或额外负荷：具体指出不一致；有证据才简化或修合同，不能仅因输入长就归因。
- 旧评估影响或模型语义判断不可靠：离线不能裁定，需要有区分力的实测；普通 native 审查同稿可用于判断
  是否值得采用更简单终评，但单次 pass 不是因果/稳定性/产品准入证据，失败也不直接推出模型不可用。
- 各分支都只会再加一句提示：当前诊断不合格，改做合同/任务划分的方案比较，停止同类盲试。

**验收：** 判断依据可从实际请求重建；每项结论注明事实/假设/未知；提出的修法覆盖问题机制，
不删除正确上下文或改变用户标准，能在既有整任务预算和真实产品路径中执行；若证据不足，
明确一个有决策价值的下一检查及失败分支，不能冒称根因明确。诊断材料不等于语义修复。

**权限与资源：** 延续 GLM-5.3-flash/high、既有每报告5次/一次修订/401920tokens/900秒、
单次32768/300秒及 SDK retry0；执行前核对实际合同。当前有界实测安排见last-push-audit最新节。
后续有价值且满足现有条件的实测按已有授权自主推进，不额外等待用户逐步许可。

## Dependencies and Follow-through

| 后续工作 | 何时推进及验收 |
|---|---|
| 修法与同版本质量 | 根据上项证据选最小机制修复；原问题、正确全文、真错/混合例及既有身份/来源回归；不拼不同版本成功 |
| 产品资格绑定 | 发布前处理 `run_native_coach_product.py` 硬编码 a71eb94 旧五例结果的问题；不作为诊断误报的前置，也不新建资格框架 |
| 真实产品消费 | 质量达到既有要求后验证真实生成/工具/审查修订；复用已有 Evidence/事务/Worker/API，补当前组合真实 DB 和 UI 证据 |
| Agent 产品与前端 | 自然请求、训练采用/反馈、四块联动、整体审美/必要重做/英雄头像，按原依赖推进；可独立部分不被单一评审阻断永久冻结 |
| 完整退出 | 保留身份运维、两树整合、独立评估与学习；具体入口见 restart plan“全局后续”及 62 主题，不在此重排主阶段 |

## Next Step

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。
四例计划已在第二例失败时停止，不能从旧计划自动恢复。当前下一动作以本卡“下一项具体交付”的恢复职责裁决为准；实际证据与否定方案已写入last-push-audit最新节。
旧历史模块不改，未新增Schema或工作流；business与产品入口均关闭。d41c0bd真实结果和后两例未执行状态已固化。
诊断明确后直接完成所需实现、相关验证和下一依赖，遵守既有授权，无须等一次新的“继续”。

## History

2026-09-22 整理前的 3596 行计划完整保存在
`docs/archive/2026-09-22-execution-method/task-plan-before.md`，哈希见同目录 manifest.json。
阶段历史完成记录原样保留；当前阶段以 canonical 和学习账本为准。progress/findings 保留详细结果。

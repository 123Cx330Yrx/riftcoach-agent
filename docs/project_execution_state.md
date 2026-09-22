---
state_schema: 1
main_stage: 8
substage_group: "stage-8-multi-agent-reliable-runtime-productization"
current_checkpoint: "8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption"
status: in_progress
pause_reason: ""
---

# RiftCoach 当前执行状态

## 当前行动

2026-09-22：核心实际改稿/终评仍未走通。buffered工具参数分支仍重复关键字段；JSON正文分支300秒无正式结果，二者live入口均停止，未接产品。
- 唯一下一步：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。按活动工作卡和review-submission-contract-decision比较全文平铺意见与逐段清单的语义职责、输出/恢复负担及既有反例，选定针对语义覆盖的最小干预；不继续直接接数组或循环换通道。位置数组恢复探针已发现旧意见枚举/原响应身份不能直接兼容，暂不投入专用适配。当前批0次付费，模型质量仍未通过。
- 指定起点审查后的修复：关闭遗漏的旧tool开发入口，7个CLI策略均先于资料/凭据/Provider拒绝；导出器补调用序号/transport关联、预约清单及计数守恒，拒绝错配与漏算，6份历史运行只读回放成功。旧da06b5a回执unknown1不改，独立校正继续保留。恢复诊断见golden_review_submission_recovery_boundary_v1.json；检查通过不等于核心语义闭环通过。
- 11bc7bd / CI35716166747三项通过；JSON正文首调用300.015秒截止，最后事件299.906秒，无正文/终态/usage。1次费用未知，语义未获验证。完整请求重建hash与reservation一致，证据golden_json_block_deadline_11bc7bd.json。不能称网络停流或输出token额度耗尽。
- da06b5a / CI35714036543三项通过；buffered工具首调用161.828秒正常终态，单个2299字符参数重复block/issues并合并14/15段。离线原样重放拒绝，无合法评估；4/6建议亦缺来源字段。证据golden_buffered_phase_failure_da06b5a.json。
- 该buffered调用11640+5845=17485tokens，未知0；原runner误记未知1保留并独立校正。实际整链和公开导出现在记录已观察usage但不伪造完成响应，61项相关离线检查及11bc7bd公共CI通过。
- 此前16:19起的长推进累计7次真实请求：6次用量已知102235tokens，另JSON正文1次未知。更早4次/42299已知及a501c33未知1单列。本次审查后修复与恢复裁决未发起Provider请求。未修改原失败回执，不将两个未知调用合并或估算费用。
- 阶段合同已实现：独立审查三字段，重评四字段及逐项映射；原始输出与内部已知空映射分开记录。该接口改进不等于工具格式或模型质量通过。
- 5c952ad CI失败因新增测试再次误读本机忽略资料，da06b5a改用提交fixture并禁止该组测试读data/runs；这是本轮执行遗漏。eadb930配对虽两JSON完整，正例旧合同失败仍保留；不能算新候选合格。
- 逐段独立工具提交超过当前每响应8个工具结果上限，离线排除；位置数组可省去重复段字段名，但其模型表现、延迟、重评接线未证实。原型golden_review_submission_shapes_v1.json仅离线证据。
- ADR0104/0105/0106/0107失败批及产品入口均关闭；实际产品仍是旧审查组合，发布前必须绑定新审查器、传输和资格版本。15个既有不同输入未换题，不拼旧成功；整体8E及四块联动/训练/前端等仍未完成。

活动工作卡：`.planning/2026-08-06-riftcoach-development/task_plan.md`。
执行方法：`docs/plans/2026-09-22-agent-delivery-method.md`。
实际后端：`D:\riftcoach-agent-rq192-pr`，分支 `codex/rq192-provider-stream-contract-ci`，
当前已停止ADR0107真实分支，新的结果表示比较仅离线，具体实现以本分支HEAD为准；`8014a56`仅是以下ADR0104历史控制基线。主库前端工作保留，未合并/重置。

## 已验证事实与阻断

### ADR0104三例历史开发控制（不计入ADR0105资格）

- 正确稿`original_topic_window`：1次调用，96/pass，无issue/advisory。
- 明确全称错误`explicit_universal_metrics`：首评正确发现真实全称错误；修订后95/pass，2条范围表达建议留在advisories；3次调用。
- 混合稿`explicit_combined_population`：首评只发现合并五局补刀事实错误；修订后96/pass，2条可选表达建议留在advisories；4次调用。逐字差异审查确认实际修订只改该补刀句，正确的中单伤害段和其余实质段保留。
- 三例合计8次调用、94702输入、18775输出、未知用量0；模型为GLM-5.3-flash/high，生产准入仍为false。案例3的重评前有一次协议字段恢复，恢复补齐suggested_correction，同时重写两条advisory的解释和引用；前后issues为空且96/pass一致，不是只补字段，也不证明恢复不会重新误判。
- 这批是已选开发控制而非holdout或稳定率证据；不能据此注册候选、开启产品入口、替换真实消费或宣布8E完成。

### 历史失败及仍适用的产品边界

以下d41c0bd等旧版本结果不计入当前候选资格。

- 核心混合例：初评只报真实补刀错误，实际修正五局合并胜8.81/败6.45，保留正确原block4；终评96/pass，独立全文审查接受。本次3调用完整走通，不代表稳定率或完整资格。
- 全称例：初评和改稿正确；第一次终评96/pass后附Markdown，严格解析拒绝；唯一完整重评合法返回93/needs_revision，把正确中单句的五局观察窗口补成全部五局分母。整链拒绝。第3/4请求共同报告/来源一致，恢复新增判断，不是旧issue映射丢失。
- 实际7次调用、103955tokens、未知0，累计至少284次（沿用历史台账）。全部stop；最长首评248.719秒，未触发300秒/32768限额。结果见golden_native_business_result_d41c0bd.json；不改失败回执、不执行剩余两例。
- JSON模式已在同一SDK路径离线重建确认；官方文档仅列text/json_object及auto工具选择。不能靠补开JSON、猜strict schema参数或丢弃自然语言尾文修复。格式/语义职责重新划分尚无已验证通用解法。
- d41c0bd的公共三项通过；此前76项聚焦回归通过。07cd6c7全测发现旧治理负例依赖已删除章节，已修复并验证12项治理测试；该遗漏与模型语义失败分开记。
- v2的93项聚焦回归通过：真实混合例离线3调用/pass保持；全称例在第3调用明确协议拒绝，不再发第4次错误重评。原7次费用/失败保留。这项修复改善终止行为，不赋予产品资格；纯JSON坏字段仍保留既有显式映射恢复。
- 新终止码已接入Harness安全诊断，仍拒绝发布模型稿；另17项Harness测试及2个子用例通过，独立审查通过。本轮相关检查共110项及2个子用例；当前v2没有真实Provider调用。

- 最近 6c22e93 实际编辑修正五局混合补刀错误，并保留正确段落；两状态终评仍把泛指判成全称，
  且缺字段、混入原稿问题的恢复映射。两请求完整 stop，2次/36011tokens/197.732秒、未知0。
  本例不是断流或输出额度耗尽；单例编辑成功不代表首评或整链合格。
- 483f91d 定位臂实际 apply/withdraw，完整意见臂 apply/apply；前者未获得通用采用资格因为信息保真局限，
  不能误称两臂都误报。因果机制和通用修法仍未确定。
- business、two-state、旧native/editor/product live入口均关闭。新business仅干预分阶段system策略，
  复用旧完整来源、Schema、验证器及工作流；GLM/high、预算、采用标准和产品默认未改。
- 最近审计重建回执和80项相关回归已通过；5578685的公共三项通过记录是此前核验。
  上轮方法核查55项离线测试及产品预览通过，首输入上界33240，真实生成/语义准入均为false。
  上述不冒充本轮重跑、真实 DB/UI 或模型质量证明。
- 现有 native application、RAG、Memory 注入和同源发布可复用；native Worker 离线测试使用 fake repository。
  默认 Worker 并非显式 native 组合。产品实测入口关闭，其内部硬编码旧五例证据仍是发布前待修项，
  不是当前发生的错误发布，也不应抢占核心误报诊断。

证据及撤回结论：`docs/plans/2026-09-22-last-push-audit.md`。
源回执入口：golden_native_editor_pair_result_483f91d.json、golden_blind_edit_result_6c22e93.json、
golden_blind_edit_failure_audit_6c22e93.json（均在 data/evaluation/results/）。

## 既有要求与后续

采用完整上下文语义标准；事实错误、无依据外推和内部矛盾阻断，措辞建议不能自行升级为门槛。
当前 ShowMaker 为公开 observed 观摩，不是阅读者本人的训练基线。Luna 只属于 Codex 开发协作。
模型/预算执行时以当前实际合同为准，开发协作不改变产品策略。

同版本完整资格、真实产品生成/来源发布、Worker/DB/API/Workbench 消费、独立评估及学习仍未全部完成。
Coach/Review/Training/Evidence、个性化训练、整体前端审美/必要重做/英雄头像、知识与 Memory、
身份运维和两树整合持续追踪。总体路线及62主题入口见
`docs/plans/2026-09-16-astra-restart-plan.md` 的“全局后续”，不以本次方法调整取消或更改阶段。

## 历史与恢复

本文件仅存当前事实和行动。整理前5907行全文已按原字节归档至
`docs/archive/2026-09-22-execution-method/execution-state-before.md`，SHA256见同目录manifest.json。
旧“唯一下一步”只按历史日期解读，不能恢复为当前任务；新结果更新本页并在progress留历史。
治理检查只验证状态结构一致，不保证语义正确或工作方法一定有效。

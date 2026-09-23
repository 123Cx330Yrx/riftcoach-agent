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

2026-09-24：核心来源时间漏检仍未证明修好，默认产品未切换，8E未完成。上一失败批已归档于4c3cfd96，公共CI35890999453三项成功；这仅证明归档与工程检查，不是语义修复。

- 最新实测仍为Flash日期审查v2：061482e7 / CI35851847210，64.938秒完整95/pass，两处日期均漏检；1次16169tokens、未知0、估价0.0177372元。更早独立整稿编辑300秒无正文，1次用量费用未知。两批均关闭、第二例未发，不能把已知估价当合计费用。完整回执见golden_flash_knowledge_time_review_result_v2.json与golden_independent_edit_result_58449abb.json。
- 本次选择能力原型：保留动态工具与GLM完整首评，在一次Flash编辑机会中核验来源并提交明确替换/空操作，再完整终评。正常2+1+1+1保持五调用；尚未采用新产品控制流。额外专审会变六调用，替代首评会推迟业务错误发现，强制预取会改变Agent动态检索，故均未选。详见ADR0110。
- 实现与复核：原子应用、未知引用/重叠拒绝、真实章节顺序、实际成稿完整终评容量和输入身份已检查。独立审查发现的标题及容量缺口已修复并定点复核。离线两处操作重建参考、原15全文保持；错误keep保留旧错误pass，未赋语义资格。五调用384350tokens仅容量样本，生成部分用历史尺寸，耗时仍未知。
- 唯一下一步：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。冻结并在同提交公共CI后执行来源编辑两例能力检查，最多2次/600秒/156506tokens、上界估价0.2562768元，沿用当前连续授权；首例失败立即停。无首评意见入模，仅验证来源补漏/正确稿keep。通过才继续实际成稿GLM完整终评与显式pass后状态机；失败不排列提示变体。新实现目前Provider请求0。
- ADR0109实际角色候选已接线：Flash/high生成/工具/改稿，GLM/high首评/重评/终评，一个共享预算；曾完成真实2生成+1首评，但96/pass漏检后由host拒绝，没有真实编辑/终评资格。原“正确参考”的第二处OP.GG无据日期已修正并独立全文核验，见golden_source_time_reference_audit_v2.json，不能计作模型改稿。来源时间传播修复已接入活动候选，默认产品不变。

活动工作卡：`.planning/2026-08-06-riftcoach-development/task_plan.md`。
执行方法：`docs/plans/2026-09-22-agent-delivery-method.md`。
实际后端：`D:\riftcoach-agent-rq192-pr`，分支 `codex/rq192-provider-stream-contract-ci`，
当前旧真实批均已关闭；ADR0108原批首例失败、第二例未发，新授权的显式ID两例均通过；ADR0109已采用并完成实际候选接线，真实整链及质量准入仍待验证。具体实现以本分支HEAD为准；`8014a56`仅是以下ADR0104历史控制基线。主库前端工作保留，未合并/重置。

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
  默认 Worker 并非显式 native 组合。产品实测入口仍关闭；休眠路径的旧五例证据绑定已随新角色组合改为同组合原15输入资格，
  这项接线修复不证明核心误报已解决。

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

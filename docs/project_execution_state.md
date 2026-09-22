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

2026-09-22：阶段合同已实现；buffered工具通道的真实整链首调用仍返回冲突重复键，未进入改稿。该工具分支停止，不能把此前两次结构完整当稳定修复。
- 唯一下一步：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。ADR0107保留完整逐段/阶段合同与来源，隔离为JSON正文通道；离线及精确HEAD三项CI后，执行原归因负例发现→改稿→终评。合法后核对全部改文，再正确全文和既有控制；失败按ADR0107分支处理，不换开关循环。
- da06b5a / CI35714036543三项通过；真实1调用，161.828秒终态/usage/EOF/close完整，单个2299字符参数含冲突重复block/issues，离线原样回放拒绝。意见指向真错，但无合法评估；建议4/6亦缺source_ids。证据golden_buffered_phase_failure_da06b5a.json。
- 本次11640输入+5845输出=17485tokens，未知0；原runner回执误记未知1不改写，补充校正独立存证。此前仅诊断脚本修好usage记账，实际整链仍漏接；现修整链和公开导出，不能将有用量的参数拒绝称未知。
- 本轮累计6次真实请求/102235已知tokens/未知0；前续办4次/42299已知及历史a501c33未知1单列。5c952ad公共测试失败因新增测试误读本机忽略资料，da06b5a改用已提交同源fixture并禁止该组测试读data/runs，未改变业务实现；这是本轮执行遗漏。
- eadb930 buffered配对2调用/32656tokens，两JSON完整但正确稿缺初审无用映射字段，原配对仍失败；ADR0106实现阶段合同消除该要求，重评保留逐项映射。新单片重复结果证明buffering不是充分修法，不推断网络根因。
- 3778683 single-schema仍重复；1f75120捕获原分片，54dfea1直连完整后解析拒绝。a501c33历史300秒中断仍未知；原参数未保存部分不可重建。所有原始失败、正确诊断及历史控制保留。
- ADR0104/0105/0106失败批、旧产品入口均未开放；实际产品仍是旧审查组合，发布前必须同改审查器、传输和版本/资格绑定。15个既有不同输入核对未换题，不拼旧成功；整体8E及四块联动/训练/前端等仍未完成。

活动工作卡：`.planning/2026-08-06-riftcoach-development/task_plan.md`。
执行方法：`docs/plans/2026-09-22-agent-delivery-method.md`。
实际后端：`D:\riftcoach-agent-rq192-pr`，分支 `codex/rq192-provider-stream-contract-ci`，
当前ADR0107正文通道开发机制以本分支HEAD为准；`8014a56`仅是以下ADR0104历史控制基线。主库前端工作保留，未合并/重置。

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

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

2026-09-22：定点配对能区别归因真错/正确稿，但自主全文修复仍未验证。最新直连诊断已正常结束，却在终态工具参数解码被拒绝，进一步定位到`tool_call_arguments`。不能宣称漏检修好、代理根因确定或产品可接入。
- 唯一下一步：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。修复终态坏参数丢证据及已返回usage误记未知的缺口后，精确HEAD CI通过再执行一次有界原请求参数捕获；分片可离线重放，不靠增加超时/输出或反复付费重现。计划及结果分支见attribution-miss-diagnosis。
- 54dfea1 / CI35705495669三项通过，直连122.297秒正常EOF/关闭，tool_calls和usage已返回，但组装拒绝tool_call_arguments。代理臂未执行。本次实际1调用/18098已知tokens/未知0，原回执未知1不改写，独立校正见`golden_block_route_result_54dfea1.json`。原始失败参数当时未保存，具体语法/解码原因未知。
- a501c33 / CI35700582136三项通过；原归因自主全文首评最后保存事件83.484秒，300.016秒由父进程截止并回收子进程，无完整response/usage、未知用量1。前缀最多会丢末尾未保存事件，不能当精确断流时刻。证据`golden_native_block_tool_interruption_a501c33.json`。
- 当前Provider走环境代理12000；无凭据短GET经代理3.000秒、直连1.032秒均401。只证明当时短请求可达，未证明长连接/Provider/代理哪层导致停滞。Git配置和NO_PROXY未改。
- 修复进度记录遗漏tool deltas：新增首末工具事件、分片数、参数字符数，无正文/参数泄露，原预算/请求不变；native manifest仅更新该组件hash及自校验digest。020e52b公共CI35703296766三项通过。
- 终态坏参数留存和stream usage记账修复已离线验证；原分片仅供本地诊断、无私有reasoning，仍拒绝交付坏结果。待本次精确HEAD公共CI；原模型、提示、请求、预算与产品关闭状态不变。
- 定点配对cb69f82 / CI35698979457：错误稿80/revise，正确稿95/pass，2次/26738tokens、未知0；其结果不能计入自主全文资格。完整公开证据`golden_partitioned_focus_result_cb69f82.json`。
- 本次续办真实请求4次：归因旧候选1次完成、定点2次完成、逐段1次中断；已知42299tokens，另1次未知。不改旧回执。ADR0104及ADR0105的live入口均停止；产品入口仍关闭。
- b47818e测试误读忽略目录的缺陷已在651a207修复并公共CI三项通过；原归因完整失败证据`golden_native_partitioned_tool_public_651a207.json`。完整诊断/取舍见attribution-miss-diagnosis和ADR0105。
- 旧三例成功、失败批和原始证据保留；Git网络可用。主库前端未合并/重置；整体8E、后续四块联动/训练/前端等退出条件仍未完成。

活动工作卡：`.planning/2026-08-06-riftcoach-development/task_plan.md`。
执行方法：`docs/plans/2026-09-22-agent-delivery-method.md`。
实际后端：`D:\riftcoach-agent-rq192-pr`，分支 `codex/rq192-provider-stream-contract-ci`，
当前ADR0105开发机制及其传输诊断以本分支HEAD为准；`8014a56`仅是以下ADR0104历史控制基线。主库前端工作保留，未合并/重置。

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

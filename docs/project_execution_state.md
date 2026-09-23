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

2026-09-24：当前角色组合真实完成一例“首评发现归因错误→Flash实际改稿→GLM终评通过”；随后正确全文仍被误报，配对批关闭。原15为1例host接受、1例失败、13例未跑，默认产品未切换，8E未完成。

- 最新实测：6a5afe9c / CI35903747333三项成功后执行原15中的attribution:1与claim-scope:1。前者83/needs_revision→实际修订→96/pass，主/独立审查接受全文及所有意见，3次真实调用可由原回执重建。伤害差距主要存在于中单内部，Flash改稿正确区分其与辅助影响明显的补刀差距；23个原段逐字保留，仅改归因段、删冗余引言和调整空行。实际成稿SHA256 ceeddca2…cc2a1；这是冻结错误稿的纠错证据，不是新自然生成或稳定性证明。
- 正确控制失败：第4次GLM完整返回84/needs_revision，把“混合位置均值受辅助局强烈拉低”扩大成所有指标皆如此；原block14已有CS/damage区分、表格有视野相反方向。按已采用完整上下文标准是真实误报，正确标签不改；同一issue缺severity是独立协议失败。host在格式恢复之前拒绝，未发恢复或新变体。
- 排除与未知：成功终评和失败首评的system/schema/来源正文/metadata相同，无旧评历史；共同事实、知识、用户原话及generation_view相同。差别为报告和派生来源身份，未隔离措辞具体化与随机性，不能宣称模型内部根因已明。原始输出已含错误，非丢报告/编号错位/解析制造/断流/额度耗尽。取消advisory替换文本不能作为通用误报修法；首例编辑成功也不证明Flash可撤销错误审查或补GLM漏检。
- 用量与执行边界：4请求（3GLM＋1Flash），47244输入＋21567输出＝68811tokens，缓存输入4800，未知0，917.188秒；未缓存估价0.865566元，非账单。拒绝时我从终端复制hash多抄一个尾字符，runner实际以model_comparison_host_decision_invalid安全停止；实质拒绝另有原件记录，无额外请求，不改写原result。CLI执行入口已关闭，不依赖本机run目录；今后从文件计算hash，不抄折行文本。
- 证据：golden_role_note_qualification_pair_result_v1.json包含49份原件hash/公开内容、逐项裁决、资格回放、用量和请求差异。全部原字节hash及公开投影已核对，不含私有推理字段。消费回执时发现相对/绝对路径混用，已修read_role_calls并验证相对路径等价；不影响原绝对路径真实运行。当前收尾提交的公共检查单独记录在progress，不冒用实测前CI。
- 唯一下一步：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。固化本批结果并关闭该候选的原样扩测；下一工作包先针对自然语言范围判定与完整审查职责做最小隔离方案核查，明确各观察对应的技术去留及五调用整任务可达性，再决定是否值得实测。没有选定或准备新的付费变体，不跑剩余13例凑数，不以补severity、提高上限或措辞特判代替语义修复。真实生成、Worker/DB/API/Workbench质量准入仍受原15阻断。

### 此前来源修复与合同演进（历史结果，非待执行批）

- 最新真实结果：6c100a25 / CI35896981340三项成功后，现有角色应用213.718秒完成2次Flash生成/工具及1次GLM审查，93/pass、2条非阻断建议，工程published。实际28段报告的数值、身份、条件训练及K1—K5来源经主/独立审查可接受，原来源日期错误未在新稿复现；这不是旧错误稿的自动修订或稳定性证明。
- 剩余具体缺口：GLM第二条建议引用9/11/13/15，仅支持中单补刀和经济，却扩写伤害617.52/1286.76，未引用10/14或其他伤害来源。完整输入有正确数值，原始模型输出已缺引用，解析/映射无损；不把它倒算为成稿事实错误。首条范围澄清合理，但扩写中单同样适用K1的依据不足，未认证为完整建议。完整审查输出未通过，建议未进入成稿。无追加付费重试。
- 实测核验：生成、审查、KnowledgeEvidence与Evidence读回同源；过期OP.GG仍无指标许可；初稿/成稿/模型文本同hash bb7e414c…d13445。3次44654tokens，缓存输入7936，未知0，未缓存估价0.3872344元，非账单；36份公开原件内容/原字节hash及完整裁决见golden_role_source_metadata_result_v1.json。真实改稿/终评未发生，原15、Worker/DB/API/Workbench尚未取得本组合资格。
- 此前显式编辑：e7bfc42b / CI35893267211首例仅修知识日期，host拒绝并关闭；第二例与GLM终评未发，未采用新状态机。1次14984tokens、估价0.0161852元、未知0，12份原件/hash见golden_source_patch_pair_result_v1.json。
- 确切工程诊断：原应用evidence_bundle含两条OP.GG自身9月10日检索时间，source_context在排除过期指标时只留digest/reason，误把来源元数据也丢掉。日期与上游相符，但旧模型输入不能支持它；旧无据断言裁决保留，不称客观日期错误或模型内部根因已明。
- 已修复：omitted_opgg保留各条自身来源、位置、检索/过期/来源生成时间、版本和未知值，仍不提供过期或不匹配的指标、分级/胜率和推荐许可。生成/审查/修订/落盘沿同一来源文档。两个活动manifest已同步，原15与旧失败不改。真实旧bundle离线复放及59项相关测试通过，独立审查无阻断；见golden_omitted_source_metadata_audit_v1.json。
- 责任调整已落地：advisory没有API/报告/编辑消费者，取消其强制替换文本，保留block/source_ids/explanation与非阻断通道；issues仍须修正建议。当前opt-in角色合同1.5.1 / Program3.1.1 / evaluation3.4.0。旧RoleReviewWorkflow和可信1.5.0 Trace读回保留，旧字段不静默剥离、旧ID不扩大。62项链路、8项新合同、147项周边回归及额外旧Trace反例通过；原15完整输入保持，见golden_role_note_contract_audit_v1.json。最新实测见上方，不再沿用准备时0调用状态。
- 已关闭配对批的准备摘要d61975ac…4241c6，原预算7调用/595456tokens/1500秒、保守未缓存估价8.6185984元，非账单；实际只用4调用即停，不能借剩余额度续跑。原资格回放补上合同已有minimum_score85，未改变采用标准。
- 历史失败分开计：Flash日期审查v2为1次16169tokens、未知0、估价0.0177372元；更早整稿编辑300秒无正文为1次用量费用未知。两批均关闭，未知费用不能并入已知总费用。详见各原结果和ADR0110。
- ADR0109角色应用仍为Flash/high生成/工具/改稿，GLM/high完整审查，共享原预算。原真实2生成+1首评曾96/pass而被host拒绝；随后来源修复成稿可接受、审查输出引用不全，结论分开。显式编辑原型能力失败，正式pass后状态机未实现；普通真实编辑/终评现取得一例证据，完整原15、真实消费和后续四块产品闭环仍未完成。

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

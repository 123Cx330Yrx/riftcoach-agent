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

2026-09-23：独立Flash整稿编辑首例300秒无正文，已停止并关闭；1次用量/费用未知，第二例未发，不接入pass后强制编辑。最后事件299.968秒，不能称网络断流、输出额度耗尽或语义编辑已失败。58449abb / CI35843805636三项通过，原9份工件和独立核验见golden_independent_edit_result_58449abb.json。来源目录原型依然只证明职责边界，不能修复正文漏检；默认产品未切换，8E未完成。
- 新发现已修正：原“正确参考”除知识日期外，还保留无来源支持的OP.GG检索日期，不能预期pass；775f7bbf / CI35846295212虽三项通过，Flash v1计划已在0请求时撤回。新人工参考只删除两处日期，七节全文/算术/引用/身份由独立审查复核，原工件和原15不改。见golden_source_time_reference_audit_v2.json；这是验收材料修复，不是模型已改稿。
- 唯一下一步：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。执行Flash来源时间审查v2：错误稿与GLM真实出站字节相同，新参考只改两处无依据日期及派生摘要，保持完整来源/政策；此前Flash做的是另一归因输入。最多2次/600秒/164158tokens，上界估价0.2623984元，沿用连续诊断授权，本提交公共CI后执行。错稿需检出两处真错、新参考应通过，host核对全部意见/来源；任一失败即停，不变提示重试。通过仅解锁真实改稿/GLM终评准备，不改产品路由、不授予资格。预检golden_flash_knowledge_time_review_preparation_v2.json。
- 新诊断依据：Harness首评pass即发布，当前那次实际用了2生成+1首评；可考虑使用其余编辑/终评预算交叉核验，但现有状态机只允许needs_revision后编辑，不能伪造issue借道。旧6c22e93证明过一次独立Flash编辑成功，失败的是复杂Flash两状态终评，不能说这条新假设已被原样否定或已获验证。正常2+1+1+1可容纳5次，任何生成多轮/恢复则会减少余量；正式控制流尚未修改。
- 最新实测及诊断：13768输入+3345输出=17113tokens，其中4992缓存输入已含总输入，未知0；按全部未缓存估价0.203804元（非账单）。模型147.797秒正常完成，含host批耗时189.016秒。请求与预检一致，与v1仅citation.retrievals及派生catalog摘要不同；政策、正文、其余事实、工具一致。知识26—30均携带9月23日检索时间，故排除丢字段/传错稿/编号偏移/预算失败。v1检出、v2漏检是两个观察，不证明新增字段导致退化或任何稳定率。12份原文件hash与独立审查见golden_knowledge_time_citation_result_6c3a3db.json。
- 本次实测：执行883c23e / CI35832963559三项通过；1次正常完整tool_calls，13578输入+4378输出=17956tokens、未知0，估价0.231208元，含host审查380.610秒。唯一issue的日期判断正确，block8/11为非阻断建议；选中26—30只有文档更新时间，真正检索记录位于25。编号没有错位，问题是选中的来源缺少时间依据，不是断流、耗尽或再次漏检。12份原文件hash及独立来源审查见golden_knowledge_time_result_883c23e.json，原失败不改。
- 本次工程证据：共享citation_retrieval_fields只按chunk归属关联provider/time，保留重复与null；顶层记录继续保留空检索。真实反例离线解析26—30已有对应时间，缓存/过期/混合未知、生成上下文、实际组装的五次模拟路径及旧15输入hash回归通过。两个活动manifest同步，默认产品未切换。更新指纹时误用native构造器处理role组合已被测试拦截并修正；Luna服务404未执行独立审查，主Agent接手复核。公开CI状态以对应提交及progress为准。
- 实际接线：build_role_coach_application / ROLE_COACH_CONTRACT 1.5.0；Flash/high生成、工具与一次改稿，GLM/high首评、重评与终评。全任务一个预算、一套全局序号，逐模型观察/定价、双传输原回执、可信Trace、来源投影、Memory/RAG/Evidence沿用原应用。新资产flash_glm_review_v1及资格绑定原15输入，旧默认不切换。
- 工程验证：实际组装的离线正常五次路径可发布；恢复耗尽、错模型/传输/回执拒绝。observed身份、同源Evidence、追踪持久化及已知/未知费用边界受检；预算停止后不暴露旧成功回执。新旧活动指纹一并维护，历史资格/失败不改。最终本机与公共检查见progress。离线不证明真实语义可靠。
- 新实测：346213c / CI35814004366三项通过；用户“允许，继续吧”后，Flash原错误稿84/needs_revision、正确稿95/pass，四条advisory逐项核对均为非阻断建议。两个请求与旧GLM诊断内容完全相同，因此不能称GLM已对照证明更优。结果golden_flash_source_pair_result_346213c.json保留22份原文件hash。
- 实际应用：role-development-20260923-v1真实Flash生成两调用并执行三次knowledge.search，GLM一调用96/pass，开发目录published；生成稿/draft/final同字节，审查全文、Evidence读回、逐模型Trace与回执核算均一致。人工不接受block27“知识检索时间2026-09-10”：引用仅提供updated_at=2026-07-23，真实未缓存检索发生9月23日。原始结果保持，独立host记needs_revision。不是断流/预算失败，也未证明增加时间字段即可修好；详见golden_role_application_result_346213c.json及诊断文档。
- 前批用量和边界：实际2+3=5调用，输入56241+输出12230=68471tokens，未知0，全未缓存价估算0.2303468元；两项任务已结束，不挪用未用满上限启动其他试验。真实混合应用初评直接通过，revision_exercised=false；observed空Memory不证明长期记忆召回。仍缺来源修复后的真实正负验证、真实Flash改稿/GLM终评、同版本原15输入、Worker/DB/API/Workbench真实消费和8E其余退出项。默认产品未切换。
- 0c061b2 / CI35752331153公共三项通过后，两例完整返回并经host逐项核对：原错误稿80/needs_revision，仅block14，sources31/1/14/10/18支持原意及修正建议；正确稿97/pass、无issue/advisory。2次输入24453+输出4483=28936tokens、未知0，缓存2368已含输入，按全未缓存价估算0.321148元；流耗时48.062/28.235秒，含host批耗时230.515秒。20份原JSON/hash、回执和人工来源审查见golden_explicit_source_pair_result_0c061b2.json。无早期死亡建议输出，不能单独认定旧advisory错引已复现修好；两例不证明稳定率或变更因果。
- 编号全路径核查：表格生产index+1、恢复index-1、source_roots及解析均一致，并非程序错位。歧义来自模型侧bare evidence_keys数组。离线适配替换为同ID的evidence_by_id对象及一句读取说明，首评/重评/改稿严格往返，完整坏意见及原hash保留；OP.GG零基物理路径不改。两控制经真实SDK MockTransport确认只有这两处消息变化；原失败仍拒绝，建议的错引不能统一+1修好。证据golden_explicit_source_projection_v1.json；未改产品指纹或注册新产品候选。
- b6b30f8 / CI35747690218三项通过后，批准的首例完整tool_calls，82/needs_revision，一问题一建议，56.406秒。文本检出正确且未把上下文建议升级阻断，但semantic_source_id_unknown；1次输入12149+输出3480=15629tokens、未知0，按单价估算0.194632元。未耗尽/超时，第二例未发，不能称正反配对成功。完整8份原工件/hash、请求身份、逐项来源及独立算术见golden_review_model_comparison_result_b6b30f8.json。
- 本轮工程遗漏：15c8940公共CI18个native组装失败来自共享源码指纹未同步；修复活动manifest两项源码及派生program hash，66项受影响回归和b6b30f8公共检查通过。旧资格/回执未改；这是执行遗漏，不归因于模型。
- 1d5f7a2 / CI35730692196三项通过后，review-target-layout-v1四次完整合法返回、61159tokens、未知0。baseline负例漏检/正例通过；target负例检出但advisory经济比例写反，正例block4泛指又被判全称。拒绝采用并关闭execute；不拼两臂成功，无编辑/终评。34份原文件hash和逐局算术核验保存在golden_review_target_layout_result_1d5f7a2.json，均未触及输出/时限。
- a82cfeb / CI35728654384三项通过，92项本地相关检查及6份历史只读回放通过；两个工程缺口已修复，未修复模型语义。位置数组不直接接入，未新增候选。
- 指定起点审查后的修复：关闭遗漏的旧tool开发入口，7个CLI策略均先于资料/凭据/Provider拒绝；导出器补调用序号/transport关联、预约清单及计数守恒，拒绝错配与漏算，6份历史运行只读回放成功。旧da06b5a回执unknown1不改，独立校正继续保留。恢复诊断见golden_review_submission_recovery_boundary_v1.json；检查通过不等于核心语义闭环通过。
- 11bc7bd / CI35716166747三项通过；JSON正文首调用300.015秒截止，最后事件299.906秒，无正文/终态/usage。1次费用未知，语义未获验证。完整请求重建hash与reservation一致，证据golden_json_block_deadline_11bc7bd.json。不能称网络停流或输出token额度耗尽。
- da06b5a / CI35714036543三项通过；buffered工具首调用161.828秒正常终态，单个2299字符参数重复block/issues并合并14/15段。离线原样重放拒绝，无合法评估；4/6建议亦缺来源字段。证据golden_buffered_phase_failure_da06b5a.json。
- 该buffered调用11640+5845=17485tokens，未知0；原runner误记未知1保留并独立校正。实际整链和公开导出现在记录已观察usage但不伪造完成响应，61项相关离线检查及11bc7bd公共CI通过。
- 此前16:19起的长推进累计7次真实请求：6次用量已知102235tokens，另JSON正文1次未知。更早4次/42299已知及a501c33未知1单列。a82cfeb审查后修复与恢复裁决未发起Provider请求；其后的1d5f7a2布局批4次/61159tokens另列。本次能力方案准备0次。未修改原失败回执，不将两个未知调用合并或估算费用。
- 阶段合同已实现：独立审查三字段，重评四字段及逐项映射；原始输出与内部已知空映射分开记录。该接口改进不等于工具格式或模型质量通过。
- 5c952ad CI失败因新增测试再次误读本机忽略资料，da06b5a改用提交fixture并禁止该组测试读data/runs；这是本轮执行遗漏。eadb930配对虽两JSON完整，正例旧合同失败仍保留；不能算新候选合格。
- 逐段独立工具提交超过当前每响应8个工具结果上限，离线排除；位置数组可省去重复段字段名，但其模型表现、延迟、重评接线未证实。原型golden_review_submission_shapes_v1.json仅离线证据。
- ADR0104/0105/0106/0107失败批及产品入口均关闭；实际产品仍是旧审查组合，发布前必须绑定新审查器、传输和资格版本。15个既有不同输入未换题，不拼旧成功；整体8E及四块联动/训练/前端等仍未完成。

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

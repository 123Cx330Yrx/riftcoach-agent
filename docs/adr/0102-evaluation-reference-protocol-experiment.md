# ADR-0102: Source references and bounded evaluation correction

## 2026-09-19 Issue evidence without a duplicate accepted-block graph

2026-09-19 native-business v2恢复并完成离线资格验证。当前实际实现基线cacd2dd/Actions35379349887公共三项success；v1正例1次完整stop，90.938秒、11952输入+8398输出=20350tokens，无未知用量，累计Provider至少207。模型97/pass，28段业务解释未发现数值/位置/身份错误，但第28段引用12而非支持录像边界的26；5/10/21的正确派生计算没有可选来源根。原响应、引用错误及独立审读保存于golden_native_review_result_cacd2dd.json，不重标通过，负例尚未执行。

额度中断未留下半改文件。本次v2按原生业务必要性撤掉正确段落额外来源图，真实issues自身列来源与解释，保留全文审查、所有旧问题显式处置、知识/安全/预算和同输入修订复评；派生计算新增完整来源根，原37编号不变。没有增加固定二次模型审查，也没有人工替代自动能力。完整脚本三次及最多五次路径可达，新五例初评46278–46354、长首评纠正56550–57304<63936；五次满额403656>401920，仍按实际用量+下一请求预约，不保证任意输出均完成。离线证据不证明模型质量。

唯一下一步：同SHA公共三项后执行v2完整正例并审读，合格才未来外推负例→自动修订→复评，再核对身份、官方日期、断言标题对照。失败先记录归因，不局部补丁自动付费重试；通过后复用现有Runtime/原子保存/Evidence/API/Workbench，报告生成与审查共享总预算。Stage8E及全部模型high/上限不变，尚未生产接入或替换人工稿，前端审美/头像/四块联动/个人Training和62主题仍保留。


## 2026-09-19 Restore business contract and correct acceptance provenance

2026-09-19 审查合同与验收依据整体纠偏完成，native-business实验进入同SHA公共CI前资格阶段。a2bf015/Actions35374657988三项success后，computed-partition真实首步192.032秒完整stop，32007tokens、无未知用量，累计Provider至少206；数组/对象合同不一致及独立来源/覆盖缺陷导致失败，未二评/修订，原响应哈希保持，现八个失败入口offline_only。追溯原始用户裁决发现“旧正例只能解释为四场中单”并非用户标准或冻结标签，撤回将五场解释本身定为确定错误的判断；旧模板观摩身份也有歧义，不能靠宽松改标签通过。历史68e8670已实际检出未来外推并完成修订请求，最终受引用合同拒绝；旧失败仍原样保留。

新实现用完整逐块判断、真实来源编号和原生问题清单替代模型重建字符/标量路径；正常初评1次、需修订3次，合同纠正最多5次。来源、知识、原问题显式处置、输入/修订绑定、安全与记账边界保持。新五份完整观摩对照已由不同agent逐块逐源独立审读；另七份范围差异对照明确为分析者开发用例，旧报告/标签/回执不变。163项相关回归通过；新五例初评46162–46238、长首评纠正57148–57850均低于63936。五次满额预约405122（长旧模板426268）超过总401920，继续按实际消耗+下次预约准入，不保证任意输出必能完成，不改预算/估算器。以上都是离线证据，未证明真实速度或判断质量。

唯一下一步：本实现同SHA公共三项success后，以新observed_01正例实际逐条审读合格为前提，执行未来外推负例→修订→复评及其余身份/来源日期/断言标题对照；任何失败停批诊断，不补字段自动付费重跑。方法、来源审计和剩余边界见docs/plans/2026-09-19-native-review-reset.md及review-oracle-provenance.md。Stage8E仍in_progress，glm-5.3-flash/high、32768/300秒、5次/1修订/401920/900秒保持；尚无新模型质量准入或生产发布，人工工作台稿未替换。前端审美重做、英雄头像、Coach/Review/Training/Evidence联动、专属训练和62主题继续按Astra restart plan追踪。

This version replaces experimental character/scalar reference representation, not product quality or the historical result. The replacement is justified by the provenance and necessity audits; no dependency, production registration, model downgrade or budget increase. Eligibility is one-case bounded development after exact-SHA CI, with manual semantic review before the next case.

## 2026-09-19 Host computation and full-context review batches

Selected the complete method described in `../plans/2026-09-19-review-workload-partition.md` after rejecting the initial half-batch prototype. Explicit model scope/source selectors remain semantic decisions; host only supplies derived arithmetic, members and source metadata. All old issues and strict native final checks remain. Offline whole-report and error witnesses fit unchanged per-call admission; real quality and latency remain unverified. Bounded execution requires exact-SHA public CI, frozen positive first and manual semantic inspection. No production registration or stage change.

## 2026-09-19 Complete second review missed its deadline

2026-09-19 provisional-reading真实正例触发二评整次时限：36b41b5/Actions35370480008公共三项success；首读54.453秒完整stop，25条理解覆盖全部19正文段、无首读schema诊断，第二请求59364通过预算准入。二评264.579秒才开始正文，300秒截止；持续收流、最大事件间隔484ms，未获完整结果及Usage，不能称网络停流或输出额度耗尽。2次Provider请求，已知7447tokens，另1次用量未知，累计至少205；负例/修订/复评未执行，语义纠正仍未验证。已保留原回执哈希并停用该入口，现七个失败入口offline_only；42项受影响检查通过。唯一下一步：按docs/plans/2026-09-19-review-workload-partition.md离线裁决完整上下文下的两批审查/全局裁决与host确定性工作分工，检查合并、首批纠错、全链预算和语义边界，不原样付费重跑。8E/high/所有上限/完整上下文标准不变；已核对现有发布和消费接缝，前端审美、四块联动、头像及62主题后续保持。

## 2026-09-19 Provisional first admission and host body coverage

2026-09-19 首读临时性与全文覆盖合同完成离线验证：a5d90cf/Actions35228469730公共三项success，但真实正例首步4处引用超长且漏10/20/26段，1次完整stop共6606tokens，累计Provider至少203，无未知用量；旧回执与哈希保留，grounded入口停用，现有六个失败入口均offline_only。新provisional-reading保留全部首读原值/问题/错误解释，格式和引用缺陷作为诊断，正文覆盖改由host完整清单负责；导航标题可纠正分类，断言标题仍严格审查。未改最终schema、模型high、估算器及所有预算；253项相关测试通过，两份真实失败回放请求63728/61634<63936，完整五步脚本输入13248/58826/58458/13176/58770，全输出预约366318<401920。合成修正不证明语义正确。唯一下一步：本实现同SHA公共CI后运行冻结正例，逐条人工核对完整最终判断/范围/来源/解释，合格才负例修订复评；失败整批停止并审查，不补字段自动付费重跑。8E仍in_progress；前端审美/四块联动和62主题全局后续不变。

完整裁决、替代方案、原始失败证据和预算见来源合同修复计划的2026-09-19节。

## 2026-09-17 Grounded-reading contract selection

2026-09-17 grounded-reading整体首读合同离线接通：前轮停用修复fcdf0f9/Actions35223400426公共三项success。未采用删issues或仅改扁平字段的草案；保留全部首读问题/原文/错误假说，原始玩家身份进入首读而比赛核算来源仍隔离。hash/块清单由host绑定；同值重复只在临时首读中显式记录，冲突值/坏JSON/未知字段/高危注入停止，最终评估严格解析不变。实际2b08fe9失败首读的18重复、29项理解和1个身份误报可完整到达第二请求；分析者构造的修正评估须覆盖更长原句并引用真实来源处置误报，原回执仍失败未改。229项相关检查通过；冻结第二请求58880/58820，原失败首读回放62484<63936，完整脚本五步13248/58820/58298/13176/58880，全输出预约366262<401920；未证明真实语义或任意响应/时限。唯一下一步：本实现同SHA公共检查后，按既有授权运行grounded-reading冻结正例，逐条人工验范围、身份、运算、来源及问题，合格才负例修订复评；失败不补字段自动付费重跑。旧五失败入口保持offline_only。无新增Provider请求，累计至少202；8E/high/全部上限/前端审美、四块联动和62主题后续保持。

Full decision and bounds: source-contract repair plan, grounded-reading section.


## 2026-09-17 Meaning-first real result: failed first admission

2026-09-17 meaning-first真实正例失败并停用：实现2b08fe9/Actions35222004364公共三项success；一次完整stop耗时87.578秒，2710输入+8307输出=11017tokens，无未知用量，累计Provider至少202。严格解析拒绝18个重复block键；只读审计确认均为相同值，独立投影其余schema和全部引用位置有效（29条首读、1个issue），但原回执仍失败，未修写。完整人工审查另发现block10仍关联五局混合表格，且首读无依据把明确ShowMaker观摩身份判成阅读者自我复盘。第一步虽读懂block3四场中单，未正确继承；第二审查/负例/修订复评均未执行，纠正能力未知。此分工尚未证明解决核心问题；首读仍是不可纠正的结构准入闸。新入口已offline_only，连同旧四入口均在付费前阻断；29项停用与审计相关检查通过。唯一下一步：使用本次原回执离线裁决更简单的首读合同，保留原始身份而隔离算术，明确host拥有的hash/清单/原文定位，验证错误假说及所有旧issue能在不丢值、不默选冲突的情况下到达严格最终审查；范围、身份、坏结构、安全及全链预算一起验，不补字段自动付费重跑。8E/high/全部上限/前端审美与四块联动及62主题后续不变。

See the source-contract repair plan for full response findings and method limits.


## 2026-09-17 Meaning-first workflow selection

2026-09-17 原文含义首读方案已完成离线选择与接线：首步只读整篇报告/用户话语，次步以完整来源核算并可纠正首读；不提供冻结答案或派生比较导航。原文覆盖、旧问题处置、typed来源与运算校验保持，复用五调用修订复评。格式说明改为完整约束的紧凑类型记法，host schema/估算器/证据不变。209项相关测试通过；正反例第二请求59170/59082，完整脚本路径12952/59082/57770/12882/59170，全输出预约合计365696低于401920；较长首读32项×80字可容纳，25项×140字本地超限拒绝，不保证任意输出或时限。唯一下一步：新meaning-review实现同SHA公共CI后运行一份冻结正例，逐项人工核对范围、运算、来源和解释，合格才负例修订复评；任何失败停批分析，不补字段自动付费重跑。无新增Provider请求，累计至少201；语义仍待真实验证，四个旧失败入口offline_only。8E/high/全部上限/前端审美、四块联动与62主题后续保持。

See the source-contract repair plan for comparison, entry and failure boundaries.


Date: 2026-09-15. Status: accepted for offline experimentation and preparation of
an isolated development candidate, now observed; no production admission or semantic-quality approval.

## 2026-09-17 Typed whole-review contract and native revision handoff

Recovery implementation e3f5fcc passed Actions35215700732. This implementation
`8bc7d4e2bdd6231074c0067653bde8fb4dcc735d` passed Actions35218637665:
pytest, postgres-migrations and packaging-smoke all completed successfully.
The committed offline artifact reproduces exactly; historical hashes still match.
This is engineering evidence only. The new implementation
is offline only; it registers no Coach, Provider runner or production identity.
`golden_typed_review.py` preserves the two-review/one-revision/two-recheck control
flow. `golden_typed_source_checks.py` gives ordinary knowledge, goal, patch and
source-boundary facts a representation separate from the inference audits.
Typed paths bind to the existing source catalog. Literal date/version/file and
numeric formatting are checked against actual source values. Match/aggregate
statistics, including position-context observed statistics, cannot use this lane.
This validates location and value, not the natural-language entailment.

Summary calculations name mean/median, cohort, metric, exact member set and the
actual reported value. Missing/invalid numbers remain missing, never reduce the
cohort or become zero; supported judgments require complete numeric evidence.
Unsupported judgments can retain the missing-member ledger for revision.
Percentage units are explicit and restricted to ratio metrics. HALF_UP applies
after full-precision calculation. Empty or missing operation fields are distinct;
real response omissions are never silently filled.

Whole-review source coverage preserves the union of original character spans
while allowing audit/source-check category corrections, including split mixed
paragraphs. The journal records original and final lanes. This intentionally
replaces the old category-lock in this offline candidate only; otherwise a
misclassified first source fact would have no correction path. Valid final lane
selection still requires semantic inspection. Headings and all final inference
checks remain enforced. Old issues are retained or explicitly resolved with
valid legacy references or typed source paths; high injection remains terminal.

The initial full-report revision composition exceeded the input envelope.
Expanded canonical context and explanation fields duplicated the same native
review, and adding a separate source ledger compounded it. The final design
sends the **validated native full review once** to the reviser, with the source
catalog and full original inputs. Before handoff, replay validation must reproduce
the exact accepted canonical evaluation. No old prompt or validator was changed;
the expanded canonical representation remains in the audit record. No original
report/source/issue/reason is deleted to fit the request. The typed review policy
is coherent rather than concatenating contradictory legacy category-lock rules.

Evidence: `data/evaluation/results/golden_typed_review_offline_v1.json` produced
by `scripts/check_golden_typed_review.py`. Two complete frozen reports retain
their identities (28 versus29 blocks); fixture transfer resolves original text
rather than assuming equal block indices. Every synthetic edit is recorded by
changed JSON path. Existing failed raw response still fails the new schema;
original receipts/hashes and verdicts are unchanged. Analyst-authored positive
and future-negative outputs are representable. The latter runs all five scripted
exchanges through actual workflow revision and recheck, using the full positive
report as an explicitly scripted revision. This is not a model-generated fix.

Thirty new tests and160 related checks pass, including exact source/value/type
and member mismatches, old-issue disposal, category correction without deletion,
invalid first-quote fallback, source preservation, security, percent/median/mean,
native revision handoff and mutation rejection. Five-phase input ceilings are
60884/63054/58104/60814/62766, all below63936. With five full32768 reservations
their conservative sum is469462, above401920. Existing actual-settlement-plus-
next-reservation admission is unchanged; this is not a full-maxima guarantee,
elapsed900s proof, output-capacity guarantee or representative qualification.

The historical four-MIDDLE/five-selected semantic failure is deliberately still
reproducible as a structurally valid wrong-cohort witness. Legal citations,
correct arithmetic and scripted pass/revision labels do not solve it. No new
Provider request was made (cumulative at least201); all four failed live entry
points remain offline_only. Model/high, budgets, owner whole-context standard,
Stage8E and the frontend/Workbench/62-theme followups remain unchanged.

Next: the source-contract repair plan's explicit meaning-first versus current
all-catalog comparison, inside the same two-review budget. Do not create a live
identity just because this contract and CI pass; first validate the complete
alternative's state transitions, counterexamples and request budget. Native
schema has more obligations, so real response compliance remains an open risk.

## 2026-09-17 Typed source catalog and complete offline source matrix

Recovery HEAD9cd602015e3f0f6bc5599307db37e3f34c04555c passed Actions35176454030.
`golden_review_source_catalog.py` now supplies an offline address layer over the
existing full input. It retains the original26 integer evidence references and
adds11 addresses, including position context, three knowledge citations, patch
and static metadata, complete source declaration and user request. It does not
change the old pack, validators, prompts or historical receipts. No live entry
uses it yet. Model/high and all admission/publication boundaries remain.

Each entry carries a source kind, exact original JSON path (or original text
span containing structured JSON), value hash and full-input binding. Embedded
position/patch/static metadata uses existing strict domain schemas for shape
validation without rewriting values. Null/absent data remains explicit, duplicate
IDs/markers are rejected, report prose cannot create a missing source, and
source text is only a declaration. A literal checker requires exact type/path/
value correspondence; it neither interprets prose nor certifies source truth.
Knowledge cannot be used as a match value, and an OP.GG source cannot be used as
official patch metadata. Semantic attribution and inference remain separate.

`check_golden_review_source_catalog.py` freezes the contextual_01 report hash and
records an analyst-authored source matrix for all28 blocks. Eight literal checks
resolve actual goal state, knowledge files/titles, patch identity/date and static
version. Every one of37 addresses resolves losslessly; old/new receipt hashes
still match their recorded audits. Output:
`golden_review_source_catalog_compact_v1.json`. The matrix and its expected
interpretation are offline evidence, never model input or newly adopted labels.

Correction to the previous audit's broad wording: `scope:limits` (old ref26)
ALREADY states that numeric outcomes cannot establish stable ability and that
no video decision evidence is supplied. The model selected ref12 (counts and
exclusions) instead. Detailed renderer prose was not indexed, but block28 is
not proof of an entirely missing capability boundary. Goal/knowledge/patch
address gaps and wrong existing-source selection must not be conflated. The
matrix/plan now preserve that distinction rather than editing the old result.

Twenty-one source-catalog checks plus12 adjacent source-first/probe checks pass.
They include wrong source kinds and values, input mutation, original index/pack
disagreement, missing/null records, duplicate sources, literal injection retained
as data, and complete compact-address restoration. Naively appending the host
manifest would raise archived second-request ceiling53104→63160; the lossless
compact address table gives55028. These are envelope sizing projections, not a
final request, full workflow budget proof or model-quality evidence.

Next: implement the offline whole-report judgment contract described in
`../plans/2026-09-17-review-source-contract-repair.md`, jointly handling nonnumeric
source facts, computed operations, contextual inference and separate ordinary
source/advice checks. Do not stuff nonnumeric checks into specialized inference
audits or pass them through a generic numeric allowlist. Compare explicit
source-grounded meaning before arithmetic; current typed addresses alone do
NOT resolve the four-MIDDLE versus selected-five error. Preserve the wrong-cohort
semantic witness, all coverage/issues/security obligations, original whole-context
acceptance, and the full five-call budget before new live qualification.
No new Provider call; cumulative remains at least201. Stage8E and frontend/
Review-Coach-Training-Evidence/62-theme followups stay in force.

## 2026-09-17 Source-first live result: failed, entry retired, complete contract audit

Implementation `e23c90d59b8b782a51c6b02c4b38cc2113419695` passed all three
jobs of Actions35175139341 before the one authorized diagnostic. New run:
`data/runs/inference_development/source-first-probe-e23c90d-v1`.
One new complete `stop` response, first visible content120.922s, stream closed
156.734s (wrapper157.078s), input12376 + output17347 = **29723tokens**;
unknown usage0, cumulative Provider requests at least201. Model/high and all
budgets unchanged. No new first review, negative, revision or recheck occurred.

The model's raw `96/pass` is **not an accepted result**. Full inspection found:

- Schema: all14 metric-to-ability claims omit required `comparisons`. Empty and
  absent are not equivalent under this wire; no defaults were inserted.
- Independent scope validation: cohort claim block10 has `sample_supported`
  but no scope source; its own short sentence contains no sample boundary.
- Independent source validation: blocks20/26/28 lack qualifying cited value
  provenance; block27's patch/date numbers lack support in its cited snapshots.
- Semantic: block10 STILL uses selected-five means505.29/389.41 and
  1286.76/591.34 instead of the four-MIDDLE context505.29/432.82 and
  1286.76/617.52. Removing first opinions was insufficient in this observation.
  Equal pairwise direction cannot justify replacing the original sample.
- Positive but limited evidence: block13 now cites all actual operands;
  block21 correctly explains the median8.805 and overall death mean1.5 and
  does not invent win/loss bindings. Its missing field still invalidates it.
  All13 protected source ranges remain covered. All28 block inventory entries,
  nine heading entries,23 claims, summaries and issue inventories were inspected;
  old/final issues and resolutions are empty. All supplied comparison operand
  bindings validate, without establishing semantic relevance to every quote.

The source errors reveal an implementation issue as well as invalid model
references. `SourceIndex.build` indexes only `pack.facts`. Position intent is
present in structured source text, K1/K2/K3 in `knowledge.citations`, patch and
Data Dragon in external JSON, and API limitations in source-boundary text.
They are not complete indexed provenance entries. Ref13 does not contain
`goal_source`; ref12 contains match counts/exclusions, not knowledge or API
capabilities; OP.GG refs2/3/5 cannot establish a Riot patch publication date.
Complete source transmission did not prove full-report citation representability.
Neither widening acceptance to any existing ref nor adding a numeric allowlist
would repair this attribution gap. It also does NOT explain away the separate
wrong-cohort judgment. Legacy template anchoring remains a hypothesis, not a
confirmed sole cause; no new run changed that variable.

`audit_golden_source_first_result.py` reads the original response and continues
component checks after schema failure, without repairing missing fields or
promoting a component result to acceptance. Its public audit is
`golden_source_first_result_e23c90d.json`; original request/plan/response/result
hashes are preserved. Source-first's paid CLI is retired before baseline,
credential or network access; offline preview, replay and observation test
doubles remain. Twelve focused checks cover retirement, nonmutation, and
detecting later binding failure after earlier schema failure. Prior94-check
readiness and CI remain engineering evidence, not semantic success.

Next action is the offline whole-source contract repair in
`../plans/2026-09-17-review-source-contract-repair.md`: source matrix and typed
provenance, whole-report judgment representation, independent scope/operation
interpretation, then complete reachability/budget qualification. Do not patch
only missing arrays/scope and run another paid retry. Four live entries remain
offline, Stage8E stays in progress, manual Workbench report stays retained, and
the global frontend/product roadmap remains in force.

## 2026-09-17 Source-first reassessment: opinion isolation and a single diagnostic

The current action is a bounded discriminating diagnostic, not reopening any
failed candidate or claiming fixtures prove quality. Latest recovery HEAD
1f2bc62 passed Actions35074258939, all three jobs.

### Dataflow decision

| Input category | Role in selected alternative |
|---|---|
| Report being reviewed | Full original ordered source index; model determines the meaning from this text and its context. No target labels or forced cohort supplied. |
| Raw facts, provenance, knowledge, derived arithmetic | Retained losslessly; cohort catalog provides possible calculations without selecting the author's intended cohort/operation. |
| Deterministic legacy report | Kept byte-identical in the frozen diagnostic, including old interpretations. The existing instruction treats interpretations as unproven. The producer fix affects new reports only. Changing this text simultaneously would confound comparison. |
| First claim judgments/explanations/score/references | Retained in original state and journal, not transmitted to second review. Mutating these fields leaves the second request identical. |
| Prior source coverage | Exact resolved spans per audit, deduplicated only when identical. Invalid span still protects whole known block. No host inference of the intended scope. |
| Prior issues | All raw issues, including malformed fields, supplied with stable IDs. Retain or explicitly resolve; high injection remains terminal. |
| Second output | Existing ComparisonWire and all final validators; original source coverage, issue dispositions, numeric/source checks and budgets unchanged. |

`golden_source_first_review.py` implements this input contract and reuses the
five-call workflow offline. Policy explicitly distinguishes cross-paragraph
scope from convenient arithmetic, and complete win/loss comparisons from
medians, overall means and subgroups. These are existing semantic obligations,
not new product acceptance rules. No new output fields or model tier changes.

Alternatives: reject merely filling missing refs/scope (known wrong semantics
then pass); reject host assignment of MIDDLE by keywords (silently chooses
meaning); reject extra verifier/model calls at this point (no evidence they
solve this task within the existing flow). Opinion isolation is selected for
an experiment, not asserted as a proven cure. Scope/audit obligations and old
issues still originate partly from first review, so this is not statistical
independence. Original first headings are reclassified from report text.

### Offline evidence and limits

94 relevant checks pass after fixing a test double's double-counted initial
reservation; production call accounting was not changed. Checks include
opinion-change invariance, lossless source tables, old malformed issue retention,
full-block fallback, source-loss/security rejection, omitted future-error
handling, five-call revision/recheck, single-call receipts, no retry after
invalid output, interrupted unknown usage and CI-before-credentials.

`golden_source_first_readiness_v1.json`: actual archived first's second request
58742 → 53104 input ceiling. Two synthetic frozen input shapes 52924/52994;
ten historical sizing projections 53056–54510; revision shape 63322 (below
63936). Their historical assumptions remain explicit and are not live results.
The raw failed first and second bytes remain unchanged. The format-only wrong
semantic witness STILL structurally passes under the new final validation;
manual semantic inspection remains essential. No reliability rate is inferred.

### Qualified diagnostic and interpretation

After clean exact-SHA public CI, `run_golden_source_first_probe` may execute
ONE new second-review request from c3ff392's frozen positive first response.
The baseline files are checked against the existing audit's hashes; frozen
report, facts, knowledge and legacy source text remain. It is a new run with
max_new_calls=1, high, 32768 output/300 seconds, SDK retry=0, no revision or
negative case. The reused first call is not counted as new or portrayed as a
fresh complete workflow. All three previously failed entries remain disabled.
Existing user authorization covers this bounded diagnostic.

Hypothesis: excluding first opinions and ordering judgment from original text
can avoid retaining the five-game interpretation while correctly preserving
four-game contextual scope. Inspect target scope link/cohort/explanation,
all other claims, operations, headings, numeric citations and issue dispositions.
Also inspect failures after the first validator to avoid local-patch tunnel vision.

A complete correct response is evidence for this one diagnostic only; then
qualify a fresh full positive/negative workflow before claiming a working cycle.
Wrong sample/operation or any protocol/transport failure ends this diagnostic;
no automatic field patch and retry. A failure cannot identify first-opinion
anchoring as the sole cause, and success cannot isolate input omission from
policy wording or model variability. Preserve all resulting evidence.

Stage 8E, the user whole-context standard, model/budgets, production admission,
frontend overhaul and 62-theme future work remain unchanged.

## 2026-09-16 Upstream deterministic evidence wording corrected

Inspection expanded beyond the evaluator to the actual second request's third
message. The deterministic source report includes legacy template conclusions
such as mixed-role CS implying declining development stability, damage implying
output-conversion ability, and an unqualified main-role label. The current
`app/lol/report_renderer.py` still generated those conclusions. The prompt marks
that report as untrusted and says machine explanations are not facts, but that
does not make the upstream statements valid. Whether this material caused the
observed target mistake is unproven; anchoring on first review is not the only
hypothesis to examine.

Fix the producer independently: `build_findings` now reports scoped sample
statistics and descriptive differences over displayed aggregates, distinguishes
mixed/single/missing role information, preserves absent metrics and states the
limits of means. It does not infer stability, ability, win/loss causes or
training intent. Sample role/champion frequency labels replace unqualified
main-role/usual-champion labels. This is source-quality correction under the
existing role/ability boundaries, not a new evaluation standard.

New live/report generation consumes the current renderer. Historical RQ-246
acceptance had accidentally depended on regenerating its input through the
current renderer; its manifest correctly detected wording drift. Preserve its
EXACT original Markdown as `examples/evaluation/coach_product_rq246_v1/`
`deterministic_report_snapshot.json`, generated from c3ff392's pure renderer,
with summary/report hashes and source identity. Historical acceptance uses
that bound snapshot. The original inputs, manifest and compiled request/context
fingerprints remain byte-identical; altered summaries cannot reuse the snapshot.
No new acceptance score or live success is inferred.

128 affected renderer, domain, synthetic-acceptance, real-golden preparation,
Stage-1 and product-service/compiler checks pass. Implementation fcf0ac3 passed
all three public jobs in Actions35073525804; preceding failure hold/audit
33c03ce passed Actions35072891451. Original c3ff392 live response
and failure hashes still match. No additional Provider call follows the failed
pair. Next offline dataflow adjudication must distinguish raw facts, derived
statistics, old template interpretation, first-review opinions and final claim
meaning together; suppressing the first opinion alone is not established as a
sufficient remedy. Keep all three failed live entries disabled.

## 2026-09-16 Provisional live result: semantic reassessment did not correct the source object

Implementation c3ff392 passed Actions35071182777, all three jobs. The isolated
positive `provisional-review-c3ff392-positive-v1/contextual_01` completed both
calls with stop: 75.468s and 131.156s; 25511 input + 23007 output = 48518 tokens.
No unknown usage; cumulative Provider requests at least 200. No negative,
revision or recheck ran. Neither output allowance nor timeout was exhausted.

The provisional entrance worked, source preservation succeeded for all 13 old
claim ranges, and second review added claims. Nevertheless:

- block13 table has correct selected operands but evidence_refs=[6], missing
  the required actual rows. Runtime stopped at comparison_operands_not_cited.
- Independent per-claim inspection also found target block10 sample_supported
  without the necessary cross-paragraph scope reference.
- The target explanation repeats the first assessment's five mixed-role games,
  binding selected rather than the four MIDDLE games established in context.
  The same numeric direction does not establish the same comparison object.
- block21's training median and overall mean are decorated with win/loss
  comparison bindings, even though those are different operations. Membership
  validation alone cannot establish that the operation matches the sentence.

`audit_golden_provisional_result.py` checks every final claim independently.
Its explicitly synthetic witness ONLY supplies the table's missing operands
and target's block3 scope link. Full application then returns structural pass
while the WRONG explanation and selected bindings remain unchanged. No live
response, receipt, target label or original bytes are edited. This disproves
any claim that fixing the first two validation failures solves semantic quality.
Evidence: `data/evaluation/results/golden_provisional_result_c3ff392.json`.

Decision: stop this batch and mark its live entry offline_only before inputs,
CI, secrets or Provider, alongside both previously retired entries. A local
field fix is not a reason for another paid trial. 35 affected checks pass.

### Method correction and next offline deliverable

What was achieved: a previously impossible corrective path is now executable.
What was NOT achieved: independent semantic correction. The second response
retains the first wrong target interpretation despite having both cohort
calculations. Copying is observable; anchoring as its cause is a hypothesis,
not a proven Provider defect. More output or another mandatory duplicate
reference would not establish author meaning.

Before further implementation/live entry, compare the current full-opinion
second input with a source-first alternative: second review receives complete
original report/facts, protected source ranges and every old issue needing
explicit disposition, while prior claim verdicts/explanations remain immutable
in the journal rather than becoming the starting semantic answer. This is a
candidate design for offline adjudication, not adopted product architecture.

The offline deliverable must cover cross-paragraph scope inheritance, mixed
clauses, selected versus same-role comparisons, median/mean versus win/loss
operations, omitted/fabricated spans, genuine future extrapolation, issue and
security retention, final validation and all request budgets. Do not force
MIDDLE by keyword or send expected test labels as a shortcut. Distinguish
program-verifiable arithmetic/identity from language interpretation explicitly.
A subsequent real experiment needs a concrete discriminating hypothesis and
whole-contract qualification, not another claim that fixtures prove semantics.

Whole-context user acceptance remains unchanged; no new definition-of-stable
requirement. GLM high and all limits remain. Stage 8E is in progress; broader
frontend/product follow-ups remain in the restart plan and 62-theme ledger.

## 2026-09-16 Provisional contract qualification for one bounded observation

The full contract is eligible for an isolated development observation after
exact implementation SHA public CI, not semantic or production acceptance.
The offline implementation f034b01 passed Actions35067580216 (all three jobs).

| Contract obligation | Finding and remaining boundary |
|---|---|
| Correct provisional errors | Overlong refs, invalid decision/scope fields and bad spans in known blocks retain their original values; regrouping is permitted. Unknown blocks, inventories, malformed JSON and high injection stop before another request. |
| Preserve source | Valid spans protect exact character intervals within the same audit; invalid spans protect the whole known block. Splits/merges cannot lose characters. More than 24 distinct protected blocks is rejected before the final review. |
| Preserve issues | Every old issue survives unchanged or receives an explicit source-valid disposition, with original data journaled. Disposition truth still needs semantic inspection. |
| Discover omissions | The second request contains the complete report and requests new claims. Tests prove omitted cross-paragraph and future claims can be added and that unsupported claims need blocking issues. They do not prove actual model discovery. |
| Preserve comparison meaning | Operand membership and complete arithmetic validate, while wrong cohort/metric, omitted bindings or contradictory prose remain semantic failures requiring manual examination. |
| Revision and recheck | Existing scripted five-call path preserves evidence bindings, receipts, one revision and source identity. Strict final schema and validators remain unchanged. |
| Budget and transport | Reuse the unchanged request builders: original failed response second request 57206; historical sizing projections 58800–62944, with prior assumptions disclosed. Each actual request still passes its own budget reservation; this is not a guarantee for every schema-legal response. |

New `run_golden_provisional_review` has its own experiment/run identity and
implementation fingerprint. Both failed entry points remain offline_only.
It selects exactly one frozen case, checks clean exact-SHA public CI before
credentials, and uses the existing high/32768/300s request and
5 calls/1 revision/401920 tokens/900s report limits with zero SDK retries.
159 distinct focused checks pass (158 suite checks plus one added dispatch check).

Run contextual_01 first. Inspect all actual source spans, decisions, headings,
comparisons, explanations, issue dispositions and the omitted block10 target.
Only a semantically correct positive permits contextual_02 and its actual
revision/recheck. A protocol, transport or semantic failure stops the batch;
no automatic local-patch-and-paid-repeat loop. Existing broad authorization
covers this bounded development observation. No claim of holdout accuracy,
Stage 8E completion, production admission or owner understanding follows.
No new live request has occurred at this qualification checkpoint.

## 2026-09-16 First live comparison failure: provisional input is not final acceptance

387b8ef passed all three public jobs in Actions35065251865. The first positive
control then completed one stop response in 59157ms: 11162 input + 5619 output
= 16781 returned tokens, no unknown usage. Cumulative Provider count is at
least 198. Its first review used 14 evidence references where FirstWire allows
12. Independent source inspection also found a rewritten, unresolvable tail
in block14 and no claim for target block10. No second evaluation, negative
control, revision or recheck occurred. This was not length or timeout.

The deeper flaw is admitting a provisional review only after it meets final
field and source-span validity. Raising 12 to 14 alone would still fail on the
invented tail and would not address omission. Stop this live batch and retire
its entry before inputs/CI/credentials, while keeping the old contextual hold.
The new offline `golden_provisional_reassessment.py` separates input identity
and source obligations from the correctness of provisional judgments:

- Complete JSON, host-identifiable block/audit/heading inventories and source
  identity remain necessary. Unknown blocks and high injection are terminal.
- All provisional fields, errors and old issues remain data, not accepted
  judgments. Overlong refs, missing decisions, bad scope refs and extra fields
  are diagnosed without truncation or changing the raw first response.
- A bad span in an existing block protects that entire real block. It does
  not guess the intended phrase or accept the invented quote. Exact valid
  spans retain their original source coverage; cross-block/audit loss fails.
- Final ComparisonWire and complete validation remain strict. Every old issue
  must be retained or explicitly disposed of with evidence/reason in the
  journal; malformed old issues cannot disappear silently. Final schema
  capacities are not enlarged. Full-review omission still needs real checks.

The failed response's original bytes now construct a 57206-ceiling second
request offline; ten historical sizing projections are 58800–62944. These
projections retain their earlier explicit sizing-only assumptions and do not
regrade any historical failures. 153 relevant checks pass, including two/five
call scripted paths, full-block protection, old issue preservation, malformed
JSON/source/security rejection and both retired entry guards. No second paid
request followed this failure. The first response still omits the target; this
is explicitly not a successful semantic replay.

Evidence: `golden_provisional_reassessment_v1.json` and the write-once local run
`comparison-review-387b8ef-positive-v1`. Next decide the complete provisional
contract's readiness and verify public checks before any separately identified
new control pair. The stopped batch cannot be resumed or relabeled success.
Stage, high, hard budgets, whole-context standard and all deferred product/UI
requirements remain unchanged.

## 2026-09-16 Comparison contract and isolated workflow decision

Select an explicit per-claim cohort/metric/operand binding for the second full
reassessment, backed by host-computed complete selected/role outcome groups,
means and all-pairs relations. Preserve full source, the original first review,
all old issue dispositions, one decision/explanation and complete final validation.
Bindings describe the operands of one calculation; the overall claim may cite
additional facts. Equating those sets was rejected during offline development
because a sentence can legitimately mention five total games and compare four
mid games. A model selecting the wrong cohort or metric remains a semantic
failure: structured references alone cannot prove the author's intended meaning.
The historical c010 wrong explanation still structurally passes when explicitly
bound to selected instead of MIDDLE; the evidence records that negative result.

The first implementation's added instructions exceeded one historical request
shape. The final candidate uses one coherent reassessment policy and lossless
shared columns for the complete first review, checked by exact reconstruction.
It does not remove source, explanations, issue history or raise budgets.
Final v4 measures both frozen second requests at 58502/58576, ten historical
shapes at 58608–62718, and a revision with comparison bindings at 56892.
Intermediate v1/v2/v3 results are not current readiness evidence. Schema-legal
large states remain subject to preflight, not a universal completion promise.

134 relevant tests pass, including actual scripted five-call review/revision/
recheck with source identity and transport receipts, terminal bad operands,
cross-paragraph scope, mixed claims, misleading same-direction groups, title
binding, missing values, upstream truncation and future extrapolation. The
new isolated workflow forwards comparison bindings to revision. The new runner
executes exactly one frozen case at a time; inspect all explanations manually
before starting the next case. The old contextual entry remains offline_only.

Decision: this complete design is eligible for one bounded development pair
AFTER exact implementation SHA public CI passes. This is a test opportunity,
not semantic approval, production admission, or a change to the owner's
whole-context standard. Preserve high, 32768/300s per request and 5 calls,
1 revision, 401920 tokens/900s per report. Any protocol/transport/semantic
failure stops this pair; no automatic patch-and-paid-rerun loop. No extra user
approval is needed within existing authorization. Current Provider count is
unchanged (at least 197); no new live response exists at this checkpoint.

Evidence: `golden_comparison_reassessment_v4.json`, comparison reassessment and
workflow tests, and the current section of the feasibility plan. Previous
ff13c1c passed all three public checks in Actions35063171248; it does not cover
the new implementation. Luna review failed to start with an unsupported-model
404; no independent-agent approval is claimed. Codex model availability does
not change RiftCoach GLM settings.

## 2026-09-16 Restart: full reassessment feasibility, not live qualification

The instruction audit is complete and the owner authorized resumption. The
next offline experiment compares the old bounded patch, one decision per
source block, and full reassessment with source-range preservation. A block
can contain several distinct assertions (v10 block 3 has sample and direct
judgments), so one decision per block alone is not an adequate replacement.

The independent prototype `golden_reassessment_feasibility.py` uses the same
full first/final review schema. It permits regrouping but requires each old
claim's complete character interval to remain covered in the same audit and
block. It preserves the first response and all issue dispositions in a journal;
changing/removing an old issue requires explicit valid source references and a
reason. High injection remains terminal, and full existing final validation
still applies. There is no Provider, production registration, live runner or
change to the retired candidate's offline_only guard.

99 relevant tests pass, including 23 new offline tests for full-block duplicates,
splits without lost characters, 48 updates, more than 16 headings, more than
12 issue resolutions, security, source/state integrity and a false-cohort
semantic witness. The explicitly synthetic projection of actual v10 applies
its recorded updates and splits block 3 into exhaustive source spans. All 12
old references remain covered and the final structural validator passes, but
c010's five-mixed-games explanation is still wrong. This is deliberately a
negative semantic result, not a repaired historical success.

Complete first requests measure 45830/45902; second-request shapes 55686/55762.
Ten historical state projections measure 55872–60866; an actual historically
revised report's recheck first/second shapes are 45984/58062. A synthetic
revision request measures 54004. A legal 48-claim state with 500-character
explanations exceeds the complete input budget and is rejected before another
call. Nothing is truncated, no hard budget increases and no five-maxima-sum
rule is introduced. All measurements are offline projections, not guarantees
of output length, latency, semantic quality or completion.

Decision: retain full reassessment as the structural offline direction; do not
extend the old bounded patch. It is NOT qualified for live use. Next complete
the comparison-object/evidence/explanation contract using the actual cohort
and heading failures, assess how the second review checks those relations
within the existing call/budget envelope, and only then choose runtime wiring.
No extra user approval is invented. Details and reproducible command are in
`docs/plans/2026-09-16-review-reassessment-feasibility.md`; full evidence is
`data/evaluation/results/golden_reassessment_feasibility_v2.json`.

The old Current Phase/Next Step sections are preserved verbatim in the active
plan's `history-2026-09-16-pre-restart-sections.md`; their active replacements
now point to this work. Stage 8E and all deferred themes remain unchanged.
No new Provider request occurred; cumulative count remains at least 197.

## 2026-09-16 Execution constraint: enforce offline-only status and known dead ends

The owner's further challenge was that written promises had not constrained
execution. The failed contextual candidate now rejects `--execute` before
loading inputs, checking public CI, reading credentials or constructing a
Provider. Preview remains available and explicitly reports offline_only and
contextual_candidate_requires_offline_qualification. There is no force flag.
This is retirement of the failed candidate, not a request for fresh user
authorization; a replacement still requires the offline contract work below.

The correction builder also rejects known impossible states before sending
the second request: duplicate complete-block quotes within one audit, and a
lower bound of mandatory claim changes exceeding the patch's update capacity.
Scope/number/source errors that require claim updates count toward that lower
bound; explanation-number hints and issues that can be added do not. The check
does not infer semantic correctness, prove all remaining states repairable or
relax a final validator. Distinct audits and expandable subspans are not
mistakenly treated as duplicate complete blocks.

134 focused checks pass, including the real runner stopping before I/O and
the workflow consuming only its scripted first response. Replay of the actual
v10 first-response bytes also stops locally before correction, identifying
c004/c005/c006; no second request and no real Provider request was made.
The original SHA256 remains unchanged. Evidence is
`golden_contextual_admission_v10.json`. This cost/execution constraint is not
the replacement correction design, semantic acceptance, or completion of 8E.
Next remains offline feasibility of the entire correction contract, including
source coverage, target identity, issue preservation, capacity and budgets.

## 2026-09-16 V10 outcome: reject candidate; audit correction reachability before more live runs

6bcaa869f24164687665aaf9d10f59da01f89973 passed Actions 35049563440,
all three jobs. The one authorized v10 pair stopped after contextual_01:
two complete stop responses, 24,935 input + 18,021 output = 42,956 returned
tokens, no unknown usage. No second report, revision or recheck ran. Cumulative
Provider requests are at least 197; this recovery series is nine runs,
twenty-two requests, 544,606 returned tokens. The original receipt stays failed.

The single-decision schema avoided the old mutually contradictory fields in
this run. It did NOT fix the workflow. First claims c004/c005/c006 all reference
the complete block 3 in the same audit. Diagnostics explicitly reported the
duplicates, but the patch cannot delete a claim, shrink its original quote or
move it to another block. A full-block quote cannot be enlarged. Therefore no
legal patch can remove this duplicate group; better prompting cannot make that
transition possible. The second response edited c005/c006 but was necessarily
rejected as duplicate_context_claim. This is an execution-design defect, not
an output-cap, transport-interruption or merely insufficient model effort.

Independent manual rejection remains: c010 explains the stable difference with
five mixed-role games and a generic heading instead of the preceding four-mid
comparison. The second review leaves c010 unchanged and repeats the approval.
Even allowing duplicate quotes would not establish semantic acceptance.
Seven of nine heading review notes also name a different heading than their
target ID; their navigation decisions happen to agree, but the explanations
are not reliable evidence of correct target review.

The read-only executable audit in
`scripts/audit_golden_correction_reachability.py` reproduces the impossibility
and records unchanged response/result hashes in
`golden_contextual_reachability_v10.json`. It also identifies capacity mismatches:
first reviews can contain 48 claims, but patches can update 16; first heading
reviews allow 64, but heading edits allow 16; first issue lists have no schema
maximum while issue edits allow 12. These are potential failures for admitted
states, not claims that this particular response hit all those limits.

| Failure class | Present evidence | Required treatment before another candidate |
|---|---|---|
| Redundant decision fields | Unified in both steps, scripted and live evidence | Retain shared decision schema; do not claim semantics solved |
| Complete-block duplicate targets | Actual first state cannot be legally corrected | Establish source-unit identity before first review, or prove a coverage-preserving regrouping protocol; no silent deletion |
| Changes exceeding patch capacity | Schema limits disagree | Align admitted state and correction capacity with measured full requests; keep hard budgets |
| Wrong cohort/context or misbound explanation | Actual c010 and heading notes | Validate meaning and target binding independently; a correct numeric direction or pass label is insufficient |
| Truncated/malformed output, wrong source, security block | Existing terminal guards | Explicit terminal failure; never accept a prefix or invent a missing decision |
| Correctness after revision | Not reached in v10 | Preserve both frozen controls and require actual complete revision/recheck |

Next action is OFFLINE correction-contract feasibility, not another paid pair:
prove source coverage, target identity, preservation of factual/security issues,
repair-operation completeness for the admitted failure classes, and complete
request budgets together. Source spans must be mechanically traceable to the
unchanged complete report; segmentation alone cannot prove semantic entailment.
Compare this with a full reassessment under the same existing five-call budget.
Select and implement only after the counterexamples demonstrate a coherent
end-to-end contract. Do not simply add a deduplication exception, more prompt
text, larger limits or another model retry. The previous v10 next-action wording
below no longer directs another live run. Existing broad user authorization
still applies once a justified, tested new candidate is ready; no new generic
permission question is required. Stage 8E remains
in progress; this is not a new product scope or a rollback to 1.3.25.

## 2026-09-16 V10: unify decisions across both reviews; stop suffix-specific repair

The v9 implementation 013dbe106c45c0a842a411933dc10b05b0f4db29 passed
Actions 35047568110, all three jobs. Its only live response completed with stop:
11,344 input + 15,378 output = 26,722 returned tokens, no unknown usage.
The complete JSON was followed by non-JSON text (two backticks and `=count`),
so strict parsing rejected it. No second call or second report started.
Cumulative Provider requests are at least 195. This recovery series now totals
eight runs, twenty calls and 501,650 returned tokens; historical failures stay
failed and byte-identical.

Transport diagnosis: the real worker uses Zhipu's stream adapter, which sends
`response_format={"type":"json_object"}`. The neutral response contract's
strict schema is supplied in the prompt and validated locally; it is not sent
as a server-enforced JSON Schema. Thus “ordinary text mode” was an incorrect
description. This evidence does not establish native json_schema support or a
specific vendor defect. Existing stream payload tests cover this path.

An initial local suffix-adjudication branch was rejected before publication or
paid I/O: it required 64,912 input-estimator units for the actual 24-claim,
33-review shape, exceeding 63,936. It also treated the latest symptom while
leaving the first review's contradictory representation intact. Its runtime
and tests were removed. The new candidate does not silently strip substantive
suffixes, accept the first of several JSON objects, or add a repair call.

Across the nine historical first-response shapes, direct-result claims had
6–14 contradictory scope/context combinations per response. V6 simplified only
the correction output; the first review kept manufacturing the old combinations.
V10 uses one decision/source/reason representation in BOTH steps and one shared
domain policy. The host derives classification, status and literal source
anchors; it never chooses a missing model decision. The second request carries
the original first decisions rather than asking the model to reconcile another
expanded representation. All claim/issue/heading identities and sources remain.
The complete first wire is retained in the correction journal. A missing sample
anchor remains an invalid, diagnosable provisional claim and must be corrected
explicitly before final acceptance. Fact resolution still requires evidence.

This is a representation change, not a new semantic acceptance rule. No report,
expected label, model tier, retry count or budget is changed. Numerical mistakes,
cohort drift, misleading context and substantive trailing text can still occur;
none are declared solved by schema construction. Native constrained output is
unverified and is not silently enabled. General completion is not guaranteed.

Validation covers five-call revision/recheck, source tampering, incomplete
inventories, missing/conflicting decisions, absent sample support, protected
fact issues and prompt injection. Offline readiness projects nine historical
first-response shapes and the actual v8 recheck shape. Old contradictory labels
are used only as explicit synthetic size assumptions, with both explanation
texts retained when distinct; the projection is NOT a corrected model result.
The first requests measure 45,830/45,902; the ten correction shapes measure
56,204–61,508, all below 63,936. The malformed v9 raw itself remains rejected.
See `golden_contextual_decision_readiness_v10.json` and the reproducible script
`scripts/check_golden_decision_readiness.py`. All 698 golden-focused tests pass;
compile, governance and diff checks pass. Public checks and a new live
pair are required before any quality claim. Next: finish regression and exact
SHA CI, then one bounded pair; inspect both complete explanations, source cohorts
and actual revision/recheck. Failure is a candidate result, not permission for
another automatic symptom patch and paid rerun. 8E and the 62-theme roadmap stay
in progress; frontend renewal and all other deferred work remain tracked.

## 2026-09-16 V9: actual revision/recheck reached; retain direct-fact source boundaries

68e8670a8d83999b002fb58c76836cff3c92cf77 passed Actions 35005362095, all three
jobs. The v8 run started both reports and completed seven stop responses:
89,783 input + 69,105 output = 158,888 returned tokens, no unknown usage.
Cumulative Provider requests at least 194; seven recovery runs total nineteen
calls and 474,928 returned tokens.

Contextual_01 reached valid 96/pass with matching labels. Manual review does
not accept its explanation quality: the stable-difference claim is justified
using five mixed-role games although the earlier comparison explicitly covers
four mid games. Correct direction in both sets does not license changing the
subject. Contextual_02 reached valid 80/needs_revision, rejecting the actual
future assertion; it also raised the unqualified four-game count and revised
only these two sentences. Revision and both recheck calls actually completed.
The final receiver rejected two added OP.GG direct facts because the model
supplied scope_source to document snapshot-use boundaries.

V9 validates and journals a direct fact's optional supplemental scope_source
without turning it into a canonical inference/context or changing its decision.
All evidence/status/numeric checks remain; ambiguous/beyond_sample still reject
this field. Unknown source references fail. The full model patch remains in the
journal, including supplemental sources. The unmodified second-report recheck
now validates offline at 95/pass, zero issues; this does not replace the failed
live receipt or constitute a passing pair. The correction policy additionally
requires preserving the original role/outcome/sample subject across paragraphs,
not expanding a specific subgroup because a heading refers to selected games.

150 focused tests pass. Eight first-assessment correction shapes measure
62994/59650/58322/58072/58512/57218/61474/57570, and the actual revised-report
correction shape is 59660. All measured inputs fit unchanged limits. Evidence:
golden_contextual_pair_68e8670_v9.json and golden_contextual_readiness_v9.json.
Next: exact-SHA CI, then a fresh pair with manual subject/number/source review
and required revision/recheck. No production admission; 8E and all global
follow-ups remain in progress.

## 2026-09-16 V8: correct new-wire integration omissions

c7e7322329fe2f20670ae022d48304e9441c948d passed Actions 35003547705, all three
jobs. Its v7 real run completed two stop responses: 25,725 input + 27,912 output
= 53,637 returned tokens, no unknown usage. Provider cumulative calls at least
187; six recovery runs total twelve calls and 316,040 returned tokens. The
first case still failed before second-case/revision/recheck execution.

The response was a complete JSON object followed by two Markdown backticks.
The new wire omitted existing normalize_json reception behavior. Reusing that
bounded normalization reveals a further genuine source error: c010 uses
facts:scope/request.queue as proof all actual matches have queue_id 420.
The validator correctly rejects it. Offline inspection found two migration
omissions: the diagnostic repair_rule still instructed old field edits, and
the new policy had omitted the explicit actual-queue vs request-filter rule.
V8 fixes both and maps diagnostic source_candidates operands to actual evidence
indices, preserving the source paths and leaving model verification mandatory.

No claim/evidence is filled automatically. Raw response remains rejected after
suffix normalization. A manual c010 source/explanation projection yields
92/pass, zero issues, only demonstrating remaining downstream checks; it is
not a model success. Original failure and hashes remain. Tests reject second
JSON objects, arbitrary text and excess fences; require actual source-index
mapping without mutating saved diagnostics. 149 focused tests pass. Seven
historical correction shapes measure 62648/59304/57976/57726/58166/56872/61128,
all under unchanged input limits. First/revision shapes remain unchanged.

Artifacts: golden_contextual_queue_c7e7322_v8.json and golden_contextual_readiness_v8.json.
Next: exact-SHA checks, then a fresh complete pair with source/meaning audit and
required revision/recheck. No cap increase, downgrade, retry or production
admission; 8E and global follow-ups remain unchanged.

## 2026-09-16 V7: preserve local paragraph context when the target is an excerpt

92aed177993452507ae70b1720e00db13cd8276d passed Actions 35001860148, all three
jobs. Its v6 real run completed two stop responses, 24,624 input + 27,816 output
= 52,440 returned tokens, no unknown usage; cumulative Provider calls at least
185. Five recovery runs total ten calls and 262,403 returned tokens. It stopped
on contextual_01 before the second report or revision/recheck.

The compact correction was structurally complete, with explicit decisions.
Its c010 correctly explained that the two winning games were being compared,
but the initial target excerpt contained only “输出与参团数据明显好于整体均值”.
The default scope lookup searched just that excerpt, losing “两局胜局” in the
same original paragraph, and raised contextual_patch_sample_source_required.

V7 makes the default local scope source for sample/negated decisions the full
containing paragraph. The audited target excerpt stays unchanged. Explicit
scope_source references remain exact model choices; no different paragraph is
borrowed automatically. Ambiguous/beyond_sample decisions do not acquire a
definition/negation context. The host does not infer a decision, change its
status, or prove semantic entailment; source and issue guards remain in force.

The unmodified response now replays to 95/pass and zero issues; all actual model
decisions, explanation text and source choices remain. This is an offline replay,
not a new real complete-pair success. Original failed results and hashes remain.
147 focused tests pass, including a scope-free excerpt with an explicit local
sample antecedent, refusal to borrow the neighboring paragraph, and a future
claim excerpt with a preceding disclaimer. Six historical correction shapes
measure 62132/59054/57684/57436/57916/56620; first and revision shapes remain
47540/47612 and 50540. All measured inputs fit the same limits.

Evidence: golden_contextual_scope_92aed17_v7.json and golden_contextual_readiness_v7.json.
Next: exact-SHA public checks and a fresh complete pair with manual explanation
review and necessary revision/recheck. No model downgrade, cap increase,
production admission or change to 8E/global follow-up scope.

## 2026-09-16 V6: one explicit decision, host-bound source locations

c453088759b5afe8c16cac6d891b77f591ff2654 passed Actions 34999382329 (all three
jobs) and 658 local golden tests. Its real v5 run completed two stop responses,
25,339 input + 24,182 output = 49,521 returned tokens, no unknown usage. It
stopped on contextual_01: c010/c013 omitted status, claim_kind, scope and
scope_anchor inside their replacement values. Their prose said the fields were
null, but prose cannot substitute for missing typed decisions. Offline traversal
also found c007/c011 anchors absent from their explicitly cited context. The
second report and revision/recheck were not started. Provider cumulative count
is at least 183; four recovery runs total eight requests and 209,963 returned
tokens. The original bytes and failed result remain immutable.

V6 reduces redundant model responsibilities. The actual correction wire now
uses flat claim_updates and claim_additions. Each entry requires exactly one
decision plus evidence_refs and explanation. The decision expands into the
canonical type/status/scope; no missing decision is inferred from prose or old
state. An omitted update quote_ref retains the original target verbatim; an
explicit replacement must still contain it in the same source block. The
model chooses scope_source (or its own quote); the host only locates a literal
sample marker in that exact passage and derives the redundant relation/anchor.
Table headers such as 赢局(2) are explicit sample-count markers. Bare position
or outcome nouns still do not establish a sample. The final canonical issue,
source, numeric, coverage, heading and unsupported-future checks all remain.
A valid location or decision label is not proof of semantic entailment.

The historical first-review schema and canonical correction helper remain for
compatibility/regression; the runtime correction request and merge both use the
new wire. The new module is included in implementation identity. Actual five-call
workflow fixtures were migrated to emit this wire. Tests cover explicit decision
requirements, source preservation, duplicate/unknown targets, shortened quotes,
contradictory scope sources, table location, and future issue/nonpass enforcement.
146 focused tests pass. Five historical correction shapes now measure
62106/59028/57658/57410/57890, first requests 47540/47612, revision 50540. These
are estimator units, not billed tokens or completion guarantees.

A manual protocol projection fills only the two omitted decisions as
explicitly labelled diagnostic choices and preserves all model scope sources.
It yields structural 93/pass and zero issues under the new wire. It is not an
unaltered replay or model success. The persisted explanation no longer contains
the previous mixed-role difference error; actual next-run explanations still
require independent audit. Evidence is golden_contextual_wire_c453088_v6.json
and golden_contextual_readiness_v6.json. Next: exact-SHA public checks followed
by a fresh full pair, including revision/recheck where required. No output/time/
call cap change, no downgrade, no production admission; 8E and global follow-ups
remain unchanged.

## 2026-09-16 V5: complete cited outcome arithmetic and evaluator explanation audit

769d65101b3d25eace7f9246e11529d8ee4a99a4 passed Actions 34997110778, all three
jobs. Its real pair stopped on contextual_01 after two complete stop responses:
25,215 input + 28,492 output = 53,707 returned tokens, no unknown usage.
Provider cumulative requests are at least 181; the three recovery runs total
six requests and 160,442 returned tokens. Contextual_02 and revision/recheck
were not started. The original failure remains unchanged.

All eight feedback targets were explicitly edited. Two receiver limitations
remained: c011 cited all four raw mid rows but the arithmetic checker could
only aggregate the full role, not its complete loss subgroup; c012 used
“输局中” within a quote explicitly saying “单局验证”, rejected by the old lexical
anchor list. V5 computes an outcome mean only from a complete explicitly cited,
included role/outcome cohort, with all metric values present. It retains raw
operand provenance and never adds citations. Outcome noun anchors require a
separate explicit sample limitation in the same cited passage; bare outcome or
position terms remain insufficient. Historical fingerprinted modules stay fixed.

The exact unmodified second response replays to structural 94/pass, zero issues,
but manual review rejects its semantic quality: c004's retained explanation
calls 115.88 gold and 695.42 damage differences same-role values, although those
are mixed-role differences. Original-precision mid row differences are 72.475
and 669.235 (72.48/669.24 at two decimals). Its second-step review note did not
fix the persisted first-step explanation. New per-target feedback includes
numbers introduced by evaluator explanations and explicitly requires a claim
edit for erroneous explanations. A local arithmetic lookup miss is a review
hint, not an automatic report issue or a complete semantic proof. Manual
explanation audit remains required; the offline replay is not adopted.

138 focused tests pass, including missing citations/metrics, wrong role,
excluded rows, wrong values, provenance loss, unsupported future claims, and
explanation-only numbers. Four recent correction shapes are 63912/60834/59464/
59214; first requests 47540/47612 and revision 50540. All measured shapes fit
63936, with little headroom for the largest historical case; future shapes
remain bounded by the existing runtime. high and all call/Token/time limits
remain unchanged. Artifacts: golden_contextual_recovery_769d651_v5.json and
golden_contextual_readiness_v5.json. Next: exact-SHA public CI, then a fresh
complete pair with manual arithmetic/scope review and required revision/recheck.
8E and the 62-theme global/frontend follow-up inventory remain in progress.

## 2026-09-16 Complete per-target diagnostics instead of first-error masking

The subsequent 5645afc487f7a89d63da93e16954bfee2f026e0f implementation passed
Actions 34994694662, all three public jobs. Its new v4 run completed two stop
responses, 25,243 input + 22,540 output = 47,783 returned tokens, no unknown usage.
Cumulative Provider requests are at least 179. It stopped on report one before
revision; the second report was not started. Both recent live runs together
returned 106,735 tokens in four requests. They are not successful complete pairs.

The second review fixed c001/c002/c005 but left c006/c007/c009/c011/c012/c013
as direct_result with selected_sample scope. The receiver correctly rejected
that combination. The engineering defect was upstream: collect_diagnostics
reported the earliest global anchor failure plus numeric/anchor details, but
never enumerated these later direct-result representation errors. The agent's
preceding offline review failed to detect this coverage hole.

The current candidate now shares claim_errors between final validation and
per-target diagnostics. It enumerates representation, numeric/provenance,
duplicate-reference, context relation, anchor and table checks for each claim;
diagnostics additionally targets issue/verdict and heading inconsistencies.
A compact target/codebook matrix precedes optional detailed numeric navigation,
so the existing 12-row / 3000-character feedback cap cannot suppress later
claims behind early verbose messages. Repeated rules and quote identities are
not duplicated in those details; complete original state and sources remain.
No final acceptance check is relaxed and no unsupported field is fixed by the
host. The model must decide and explicitly edit each conflicting claim.

Tests cover an early anchor error followed by a later direct-scope conflict,
multiple simultaneous errors, and 48 affected claims all surviving the feedback
cap. All 124 focused tests passed, including existing future-error/issue guards,
source identity and five-call workflow checks. Contextual tests now construct
state through the actual contextual builder rather than the old bounded builder.

`golden_contextual_diagnostics_5645afc.json` preserves raw hashes and the original
rejection, records all nine affected targets (including the six missed ones),
and labels a manual null-field projection strictly as downstream diagnosis:
93/pass only after those six manual changes, not a model success. The unmodified
second response still fails. `golden_contextual_readiness_v4_diagnostics.json`
checks all three recent first-response shapes: 63076, 62242 and 58794. Existing
first and revision shapes also fit. Acceptance standard, model, call/Token/time
limits and stage status are unchanged. Next: exact-SHA CI, then a new-identity
complete pair; inspect actual edits and subsequent revision/recheck receipts.

## 2026-09-16 Bounded reception of supplemental notes and display whitespace

Implementation ad1003dd72437842e300ae5ec2cf4dc61bf2d47a passed exact-SHA Actions
34992614360 (pytest, PostgreSQL migrations and package smoke). Its v3 live run
completed two stop responses: 25,829 input + 33,123 output = 58,952 returned
tokens. No unknown usage; cumulative Provider requests at least 177. The second
request was actually issued, verifying the input-budget repair. The pair stopped
on the first report before revision; the future-claim report was not started.

All 22 required reviews were present. The model also supplied c014-c016 notes
for its three added claims, although each addition already had its own note.
The receiver rejected these extras. Offline inspection then found one further
mechanical error: scope_anchor “各只1局” omitted spaces in “各只 1 局”. After
explicit diagnostic projection of those two items, the entire validator passed;
there were no other observed downstream errors. This was not a live pass.

V4 changes reception, not the approved semantic standard. Optional supplemental
notes are allowed only for declared additions, numbered deterministically after
the existing claims in addition-array order. Every original required note remains
mandatory; duplicates, unknown IDs, source reassignment and missing fact issues
still fail. Supplemental text is retained in the journal and never supplies a
second classification or source reference. Its semantic explanation still needs
human/model scrutiny just as the other explanation fields do.

For an edited or added claim's scope_anchor only, the host can restore display
whitespace when all original characters match a single span within that claim's
own quote or explicitly referenced context. Digits/ASCII word characters cannot
be joined or split; numbers, punctuation, words, source and scope cannot change.
Multiple possible spans and out-of-bound anchors still fail. Before/after and
source reference are journaled. Quotes and original request/response bytes are
not edited. This is bounded source-location resolution, not a semantic fix or
permission to rewrite a model's judgment.

111 focused tests passed, including supplemental-ID binding, missing/duplicate
reviews, different digits, split numeric strings, ambiguous whitespace and
punctuation negatives. The original v3 responses replay directly through v4 to
93/pass with zero issues, 13 retained claim edits, three supplemental notes and
one whitespace resolution. `golden_contextual_recovery_ad1003d_v4.json` records
this strictly offline result and unchanged hashes for both responses and the
original failed result. It does not relabel the historical v3 run.

`golden_contextual_readiness_v4.json` measures first requests 47540/47612, three
historical correction shapes 59312/59226/56974, the actual v3 first-response
shape 62348, and revision shape 50540. These are shape measurements, not future
completion guarantees. No budget, timeout, model tier or retry limit changes.
Next: exact-SHA public checks then one new-identity two-report live validation,
including genuine future-claim detection, revision and recheck. Preserve stage
8E and all broader product/frontend follow-ups from the retrospective.

## 2026-09-15 Recovery after the comprehensive retrospective

This batch resumes the latest 206a4c3 contextual candidate. Coach 1.3.25 is a
regression baseline, not the development target. Its original report revision
success remains evidence for that report only; later control failures remain.
No historical response, strict label, or frozen Prompt Program is rewritten.

The 206a4c3 run (Actions 34959615129, three successful jobs) started one of two
reports. Its first response finished with stop: 11,807 input + 13,526 output =
25,333 returned tokens. The next request was rejected locally at input ceiling
64,300; no correction, revision or recheck was sent. Cumulative Provider requests
in the existing scope are at least 175, correcting the stale 174 checkpoint.

2026-09-16 preflight follow-up: complete-report inspection additionally covered
Chinese ordinal rank wording, T-tier numerals and ISO retrieval timestamps at
displayed precision. Wrong rank, tier, timestamp and rate-unit negatives remain
rejected. The two current contextual suites passed all 43 tests after this change.

The v3 candidate repairs connected engineering defects:

- Every first-review claim can be corrected and must be reviewed, including
  claims initially labelled direct_result. The immutable original and explicit
  edit journal remain; quote shrinking/reassignment and unsupported issue removal
  are still rejected. The prior label cannot freeze a semantic mistake.
- Already supplied OP.GG rows become indexed evidence with snapshot provenance,
  position, timestamps, allowed uses and unknown patch preserved. Existing Meta
  row validation is reused. Rank/tier/rates are checked by named metric and unit;
  external values cannot masquerade as queue IDs or unrelated statistics. This
  does not establish semantic entailment or turn a current snapshot into a
  historical, region/rank-matched or personal performance source.
- Fact, provenance and review tables remove repeated keys; external facts refer
  to the complete original snapshot already present in the request. Before I/O,
  the host reconstructs every value and compares canonical JSON. Entire source
  text, report blocks, first-review explanations and diagnostics remain visible.
- Revision now uses the same contextual standard and indexed evidence. The old
  revision constructor inherited v8's superseded local-definition policy. It is
  no longer used by this candidate. Historical constructors remain unchanged.
- The unfinished modification of frozen numeric_v4 was removed: it caused
  component fingerprint drift before baseline loading. New numeric validation
  stays isolated; the current validator reuses frozen restoration/scope helpers.

Data/control flow: supplied report and evidence -> source-bound input -> first
review -> immutable all-claim state -> explicit correction -> complete validation
-> optional report revision -> first review and correction of the revised report.
Maximum five calls, one revision, high / 32768 / 300 seconds, 401920 total tokens
and 900 seconds remain. Actual usage is settled before reserving the next request;
there is no blanket worst-case completion guarantee or hidden retry.

`golden_contextual_readiness_v3.json` uses the actual workflow input builder and
includes the latest failing response shape. Old integer references are rebound
by source identity for measurement only; this is not a new model judgment. First
requests: 47540 / 47612. Three historical corrections: 59198 / 59112 / 56860.
Latest shape: 63124, with 21 mutable claims, 30 reviews and five external facts.
Revision shape: 50540. All measured requests fit; future responses can still hit
a declared limit and must stop honestly. Original response hashes are retained.

Code map: golden_contextual_sources (index/numbers), golden_contextual_requests
(lossless tables/revision), golden_contextual_validation (final validation),
golden_contextual_correction/workflow (state/sequence). The bounded/integrated
base workflows expose explicit hooks while retaining their existing defaults.
`test_golden_contextual_recovery.py` covers false direct-result classification,
external field/unit negatives, source mutation, malformed snapshots, lossless
reconstruction and a five-call scripted path with changed-source rejection.
These tests prove engineering behavior, not a model's ability to judge language.

Validation: all 642 golden-slice-related tests passed, including historical
profiles and the new regressions; compile, actual CLI preview and governance
passed. A full local suite was interrupted after two database setup errors: the
inherited test URL was set without DATABASE_URL. Setting it for the dedicated
local riftcoach_test database exposed an unavailable endpoint (3-second connection
probe timed out). No migrations completed. Database integration remains for the
existing isolated PostgreSQL CI job; do not claim a full local suite pass.

Reproduce sizes with `python -m scripts.check_golden_contextual_readiness`, passing
--source-run, --base-report, --bounded-run, --context-pair, --latest-case and a NEW
--output path. No Provider is created. After local checks and exact-SHA public CI,
run the existing contextual entry on the two frozen complete reports under a new
run identity. Inspect every finding and source link; stop the pair on a genuine
protocol, transport or semantic failure and retain full receipts.

Stage 8E remains in progress. Do not rebuild the already completed ADR-0099
publication chain or observation-note persistence. Broader follow-ups stay in
the comprehensive retrospective's 62-theme requirements table and separate
frontend-renewal attachment: Review/Coach/Training/Evidence integration, natural
encyclopedic Coach, requested training plans, observed-vs-self identity, full
frontend aesthetic redesign (including champion portraits, Portal and Account),
data/version/role quality, deployment/Auth, and learning/portfolio coverage.
Codex Astra/Luna execution allocation is unrelated to the GLM product tier.
Interview wording: repaired evidence indexing, corrective state mutability and
request composition with reproducible regressions; real quality and production
admission remain unverified.

## 2026-09-15 Owner-approved whole-context standard and single decision protocol

The owner explicitly selected “采用完整上下文标准（推荐）”. A complete report
that clearly bounds the same sample, comparison and meaning may pass without a
special dictionary-like definition of “stable”. Optional wording improvements
must not alone block it. Real factual errors, unsupported long-term/future/causal
claims, and contradictory assessments remain blockers. This supersedes the
assistant-authored strict word-definition gate for the new experiment only.

The preceding v1 observation `bounded-review-96c2c3a-definitions` used implementation
96c2c3a1b90d0df105938ccbef98d937f8f65ba4 and exact-SHA Actions 34956898101
(all three jobs successful). Both responses finished with stop; 50669 returned
tokens, no unknown usage, 2 requests, cumulative Provider requests at least 174.
It failed before revision: c001/c005/c008 duplicated literal vs inference labels;
c010 duplicated conflicting context sources. Raw scores 95/94 were not valid
passes. `golden_bounded_observation_96c2c3a_v1.json` records all four conflicts,
full original response digests and timing. Its old strict labels and raw results
remain unchanged; this decision does not retroactively accept them.

The isolated `golden-contextual-bounded-review-v2` uses
`whole-context-acceptance-v1`. Classification and source reference are expressed
once, in the final claim; review_notes explains each required decision. The host
derives the legacy validation witness from that same final claim. It does not
repair any incoming old response: the v2 wire rejects v1 meaning_reviews and extra
disposition/language_ref. The complete final factual, source, numerical, issue,
heading, security, state and receipt checks still execute. This derivation
removes contradictory duplicate fields but cannot prove semantic entailment.

`golden_contextual_reports_v2.json` assigns independent contextual_01/02 identities
to byte-identical complete reports stable_unbounded/future_with_disclaimer. Under
the approved standard these are accept/reject respectively. Original ten-case
and twelve-case labels remain frozen. These are development controls, not a held-out
benchmark. Labels remain outside model input. The next real run must verify both
correct acceptance and unsupported-future detection, revision and full recheck.

Flow: complete source/report -> first review -> bounded explicit correction ->
full merged validation -> at most one report revision -> complete review and
correction again. Request construction includes the full lossless generation_view
explanation and verbatim deterministic source in both independent evaluations.
The actual-usage budget runner still enforces high, 32768 output, 300 seconds per
call, 401920 total tokens, 900 seconds and at most five calls per report, no SDK
retries. Larger unexpected requests remain refused before I/O.

Reproduction: `python -m scripts.run_golden_contextual_review --source-run ...
--base-report ...` previews without credentials/network; real mode additionally
requires --execute, --run-id contextual-review-..., --ci-run and --env-file.
`python -m scripts.check_golden_contextual_readiness` measures first requests
50576/50646; historical correction shapes 61386/62024/58960 and revision 53584.
The size replay does not regrade historical responses or guarantee runtime cost.
Tests in test_golden_contextual_review cover protocol isolation, contradictions,
state/source binding, fact issue retention, security, heading additions and full
five-call flow. Local focused/adjacent regression: 129 passed, compilation, governance and diff checks passed. Real semantic acceptance remains pending public checks and the
new observation. No product default, production admission or stage advance.

## 2026-09-15 Efficiency correction: verbatim source and actual-usage admission

The owner asked why the work still was not complete and required more efficient
execution. This audit corrects an assistant-imposed readiness criterion: adding
five independent maximum reservations and requiring that sum to fit 401920 was
being treated as mandatory even though the existing runner reserves only the
NEXT call and settles returned actual usage. This section supersedes the prior
blanket prohibition based on that summed envelope. It does not claim the sum now
fits, guarantee completion, change any budget, or assert owner approval of a new
model tier or weakened quality rule.

A concrete request defect is fixed: deterministic source text was embedded as a
JSON string, repeatedly escaping its own structured sections. It now occupies a
separately labeled untrusted user message. Every source character remains, and
the actual high-profile SDK request retains all three messages. A note makes
clear that machine-generated explanations inside this source report are not
already-proven facts. The complete schema, source rules, local validation and
generic estimator remain unchanged. SDK capture confirms JSON-object mode, not
server-enforced JSON Schema; generic accounting of the local schema remains a
conservative allowance, not a removed constraint.

Measurement: `data/evaluation/results/golden_bounded_review_readiness_v1.json`,
reproducible with `python -m scripts.check_golden_bounded_readiness` and the same
three private source arguments as the previous measurement. Ten complete first
requests measure **50282–50456**; the two actual saved state shapes measure
**63474/60410**, both below preparation limit 63936 and hard input limit 64000.
Historical revision remains **53584**. The summed maximum envelope is still
**445284 > 401920** and is explicitly retained as a limitation. Larger future
states can still be rejected before sending.

`BoundedCorrectionWorkflow` now reuses the established receipt-bearing sender,
revision source binding, report validation and five-call guards. Its evaluation
is first review -> preserved state -> mandatory explicit correction -> complete
canonical validation. One revision may be followed by the same two-step review;
there is no sixth call or silent repair. Invalid first inventories stop rather
than inventing source identities. Correction journals are persisted separately
for initial and revised evaluations. `scripts/run_golden_bounded_review.py` is an
isolated development entry; default preview is offline and execution still
requires clean checkout and the same implementation SHA passing all public jobs.
Old integrated entry defaults, registered Coach versions and production remain
unchanged.

The real `CoachBudgetedProvider` tests demonstrate both sides of admission:

- Five requests whose hypothetical reservation sum exceeds 401920 can complete
  when their returned actual usages leave enough room for each next reservation.
- One token above remaining capacity rejects BEFORE Provider I/O; exact remaining
  capacity admits the next request. The sixth call and elapsed-time exhaustion
  remain rejected. No estimated count is substituted for real returned usage.
- Full first/correction/revision/recheck/correction control flow uses actual
  canonical validation, full revised-report validation and receipt identities;
  changing recheck evidence is refused before another call. SDK capture confirms
  high/32768 and verbatim source transport. These are scripted tests, not claims
  about future real-model accuracy, usage or latency.

Focused and adjacent verification totals **122 tests passing** after correcting
an incomplete test fixture. Code, source text, receipt, budget and semantic
boundaries are tested separately; the existing valid-source/wrong-relationship
counterexample remains documented and is NOT declared solved.

Decision: allow a conditional bounded development observation after this SHA's
public checks, using the frozen complete explicit-definition pair with unchanged
labels: at most five calls/one revision/401920 tokens/900 seconds per report,
32768 output/300 seconds per call, high, SDK retries zero. Stop the pair on any
protocol, transport or scored control failure; preserve first failure and all
responses. Inspect meaning explanations and correction journals before claiming
semantic acceptance. No production admission or broad accuracy estimate follows
from two development reports. This falls within the owner's standing continuation
authorization; no new approval is needed for the local work or already authorized
bounded testing. Do not repeat a failed identity or launch an extra batch merely
because the code checks pass.

The immediate next action is same-SHA public verification followed by that one
bounded observation. The original 1.3.25 ShowMaker revision stays valid; independent
control reliability and Stage 8E remain in progress. Provider count is at least
172 before this observation; source restoration and these tests made no calls.

## 2026-09-15 Bounded state correction: offline implementation, readiness rejected

The prototype now exists in `app/evaluation/golden_bounded_correction.py` and
`golden_bounded_correction_requests.py`. It is not registered, has no five-call
runtime, and makes no Provider calls. Existing candidates and old responses are
unchanged. Its purpose is to keep the first assessment as host-owned state and
let the second response explicitly correct it without regenerating unaffected
claims or dropping independent issues.

Data/control flow: complete report/facts -> source-bound ContextWire first
assessment -> immutable state and short claim/issue/heading handles -> explicit
changes, additions and meaning reviews -> complete canonical validation and an
edit journal. A future runtime must bind the actual budget-transformed request
and receipt before merging; the offline `finish` function enforces this boundary.
Structural first responses without trustworthy source inventories stop rather
than receiving guessed positional identities. No extra repair slot is assumed.

The host preserves untouched fields exactly, rejects unknown/duplicate/missing
handles, and prevents source reassignment or shortening a claim to hide an error.
Every mutable claim (including diagnosed direct facts) and every heading needs a
meaning review. New claims carry their own review. Fact-issue removal requires an
explicit reason and source references; before/after remain in the journal.
Injection is terminal, including when introduced through an issue edit. Full
canonical numeric, source, heading, scope, issue and coverage checks run after
merging, so a scope correction cannot forgive an independent fact error.

Request compaction deduplicates only identical fact values, preserves distinct
JSON types and restores the entire original generation projection. Schema title
annotations are removed, but constraints and literal values named title remain.
The independent correction request now contains its required source and factual
rules explicitly; it cannot rely on an earlier prompt absent from its messages.
A generation-only length policy is replaced with its evaluator obligations;
position/source policies and accuracy/evidence/actionability remain intact.

Evidence: `tests/test_golden_bounded_correction.py` and adjacent source/context,
integrated review and budget tests: **115 passed**. Tests cover explicit definition,
negation, later conflict, overlooked headings, retained facts, numeric rejection,
state tampering, injection, source restoration, request-size boundaries and actual
receipt binding. These are scripted protocol tests, not real semantic controls.
A deliberate wrong definition relationship with a valid source still receives
canonical pass; the journal records `semantic_approval=False`. This explicitly
proves the remaining semantic limitation rather than declaring it fixed.

Reproduce measurement (private frozen source runs required):

```powershell
python -m scripts.check_golden_bounded_correction --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md --context-pair data/runs/inference_development/context-controls-9c5aad9-critical/pair-01
```

The body-free result is
`data/evaluation/results/golden_bounded_correction_offline_v1.json`:

- Ten complete first requests: input ceilings **51598–51772**, all source values
  and JSON types reconstruct exactly.
- Two actual saved first-review states: correction ceilings **64790** and
  **61726** after budget metadata. The first fails both preparation limit 63936
  and runtime input limit 64000. Earlier 63662 omitted necessary standalone
  correction rules and is superseded, not an accepted optimization.
- Historical revision shape: **53584**. Twice the measured maximum first and
  correction requests, plus revision and five 32768 output reservations, yields
  **450548 > 401920**, excess **48628**. This is a measured-shape envelope, not a
  bound on future first responses/revised reports or actual billed usage.
- Even an UNUSABLE sizing ablation deleting all prior state from correction
  requests yields **434584 > 401920**. Shortening handles or state alone cannot
  establish the envelope. This ablation is not an executable request proposal.
- Actual usage settlement may permit some runs despite the conservative summed
  envelope; five 300-second calls also do not guarantee the shared 900 seconds.
  No limits, estimator, GLM profile or retry policy were changed.

Decision: retain the offline state-merge prototype and its regression evidence,
but **reject this composition as ready for real calls or candidate wiring**.
Do not run another paid batch to find out whether the budget happens to suffice.
The current canonical next action is an offline component-level budget decision
for the complete first/correction/revision requests: identify exact source/schema
repetition removable without losing obligations, quantify its achievable saving
against 48628, and accept or reject a concrete composition before more runtime
implementation. Do not add another protocol or reinterpret ordinary-language
ambiguity as a numerical error. If no adequate lossless saving exists, record
that boundary and present a concrete cost/scope choice rather than silently
raising limits, lowering GLM or weakening quality rules.

Original Coach 1.3.25 report revision and 96/pass recheck remain valid. Independent
control reliability and Stage 8E remain in progress. Observation persistence/API/
restart readback are already complete; four-surface design and hero-avatar work
remain indexed in the 2026-09-11 follow-up. Provider cumulative count remains at
least 172, with zero additional calls here. Implementation `56a5467c83371f9da3b462ad94bcdacd2800726f` passed all three
public jobs in Actions `34954808947` with the exact same head SHA. This
documentation closeout changes no product code. No production admission or
deployment follows from CI.

## 2026-09-15 Follow-up: the redesign needs a correction path, not another full pass

The owner again challenged repeated failures after the workflow reassessment.
This is a process defect as well as a model-quality problem: scripted tests
established transport, restoration and refusal behavior, but were not evidence
that the changed division of reasoning would improve the failed controls. The
integrated extraction step left the substantive assessment workload in one call.
Do not repeat the claim that the original report never completed: Coach 1.3.25
already produced its accepted revision and 96/pass recheck. The unresolved work
is reliable independent report evaluation, including protocol validity.

New reproducible offline evidence is in
`data/evaluation/results/golden_review_redesign_offline_v1.json`, produced by
`scripts/check_golden_review_redesign.py`. It makes no Provider calls and does not
contain an executable new Coach candidate:

- Replaying the unchanged v2 response exposes three concurrent structural
  defects: 47/48 judgments, 4/28 additions rows and an unexpected field. The old
  diagnostic returned only that field and mislabeled it `discovery_schema_invalid`.
  `assessment_feedback` now collects independent counts and schema errors under
  the actual assessment phase, then retains existing canonical diagnostics when
  the shape permits them. It does not zip misaligned rows, delete fields, repair
  results or change acceptance. This fixes diagnosis, not the model's omission.
- An explicit short-handle prototype preserves correspondence under reordered
  responses and rejects missing, duplicate and unknown handles. Old positional
  responses are never retrospectively assigned identities. Sparse additions
  should carry their own source references, rather than empty rows for every block.
- A deliberately scripted counterexample points to the genuine overall-summary
  paragraph and claims that its correct statistics define this target's word
  “较稳定”. The existing bound-scope decoder accepts the source/reference protocol;
  the interpretation is still unproved under the frozen rubric. This is an
  executable demonstration that source existence is insufficient, not a new
  model failure or an accepted whole-report evaluation.
- Direct reuse of the full review measures 57692–57866 input-ceiling tokens;
  the existing single-target scope request measures 35630–35896. A batch sizing
  template with explicit handles and sparse additions measures 40930–45886,
  using the actual 48 discovered targets for the failing report and whole blocks
  for the other nine. The historical revision shape is 53584. Five-call envelope
  sums are 404948 (single target) and 424928 (batch), above 401920. These are
  measured reuse shapes, not a minimal fact-only implementation or future maxima.
  The runtime settles actual usage, so this does NOT predict every run fails.
  It does disprove treating this unmodified composition as a proven envelope.
- Two mandatory phases for both initial evaluation and recheck, plus revision,
  consume all five calls. One extra correction after each evaluation needs seven.
  A valid fact issue must survive later scope approval; missing or malformed
  facts cannot be silently filled by a supposedly scope-only judge. A target
  interpreted correctly cannot clear an independent later conflict. A design
  that has no way to satisfy these obligations is not ready for registration.

Rubric audit: the complete negative report DOES already state sample limits and
per-game direction in its opening summary. The frozen target asks for clarification
of an undefined stability term under the explicit-reference rubric; it is not an
arithmetical falsehood or proven assertion of long-term ability. Labels and old
results remain unchanged. A plausible ordinary-language reading must not be
reported as objective numerical error, and these assistant-authored controls are
not independent holdout or an owner-approved universal style rule. Actual
unsupported causal/future claims remain substantive errors; explicitly negated
quotes and genuinely defined local observations must remain acceptable.

Decision: reject direct reuse of “full factual review + scope review” as a ready
candidate. Keep the integrated candidate rejected. Adopt ONLY the next offline
experiment: retain a first review's source-bound state, use the second slot for
bounded corrections and a scope challenge, then perform full final validation.
Unlike the earlier anchor-only patch, this must permit explicit semantic changes
and newly discovered assertions without regenerating every unaffected judgment.
It is not yet an implementation or a claim that patching will improve semantics.

The prototype must preserve first-pass fact/numeric/source issues and diagnostics;
only explicit, justified edits may supersede a finding, and injection findings
remain terminal. Every target uses a host-owned handle; additions resolve an
explicit source reference. The challenger must distinguish the report's language
from empirical support, identify an actual definition/negation relationship or
record unresolved meaning, and test the same facts under changed definition,
negation and later-conflict text. A correct number or a valid reference alone
cannot count as a resolved challenge. Existing canonical validation is the final
gate, not a partial patch acceptance rule. Measure the actual old state, concrete
diagnostics, full report/facts and patch schema together, including revision and
recheck; reject the proposal if these obligations cannot fit two calls per
evaluation/five per report. Do not hide another full review in a “narrow” request.

Reproduction (repository root, use the project Python):

```powershell
python -m scripts.check_golden_review_redesign --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md --run-dir data/runs/inference_development/integrated-review-153ae2c-definitions --historical-evaluation data/runs/inference_development/context-controls-9c5aad9-critical/pair-01/stable_defined_before-evaluation.json
```

The source runs are private audit inputs; public CI tests the independent
correspondence and diagnostic behavior. This checkpoint adds no paid calls,
changes no GLM profile, and makes no production or model-quality claim. The next
offline experiment is within standing authorization and requires no new approval.

Local verification: 35 integrated-review tests plus 23 correspondence,
bound-scope and context-diagnostic tests passed; compile, governance and diff
checks passed. The saved failed response now reports all three structural defects
with no omitted diagnostics, and its original bytes remain unchanged. Implementation
abcfc0242b30798d9a239338a1a043dd6ae6ef11 then passed pytest, postgres-migrations
and packaging-smoke in Actions 34951075015 at that exact SHA. This verifies the
diagnostic change and offline experiment, not model semantics or a new candidate.

## 2026-09-15 Integrated v2 complete responses rejected; adoption paused

Implementation 153ae2c240f9c48ac60963ad27a7b30fd454ba33 passed all three jobs in
Actions 34948333840. The second complete-report run
`integrated-review-153ae2c-definitions` planned 2 / started 1 / finalized 1 /
interrupted 0 / not started 1. Both calls returned complete stop: discovery
2445+5865 tokens in 51.875s, assessment 14103+9882 tokens in 97.594s. Total 32295
returned tokens, no unknown usage. Including v1, this work added 3 complete calls
and 41136 tokens; cumulative Provider reservations are at least 172. None is an
output-capacity or stream failure.

The real assessment request's input ceiling was 62012; the v2 budget correction
worked on actual generated targets. However the candidate did not produce an
accepted assessment. It added `judgments[7].context_ref_note`, returned 47 judgments
for 48 targets, and interpreted the required 28-row dense additions/sweep array as
four nonempty rows. It moved the already selected comparison table into additions,
shifting later positional judgments beginning at target 21. Do not align those
later rows by position, remove the extra key, pad the arrays, or call the result
valid. Original files are untouched; manual-audit-v1.json is separate evidence.

There is also a substantive failure independent of those structural defects. The
old ambiguous target is position 16, before the observed shift. The raw judgment
calls it selected_sample/supported with no definition context and explains that
correct per-game direction and a large mixed mean difference justify “较稳定”. The
report never defines that word's meaning at this target. Correct observations do
not supply a missing author definition. The raw pass is therefore not a quality
success even if its structure were repaired. Several scope anchors are descriptive
predicates instead of source sample anchors; unchanged validators still reject.
No accepted initial evaluation, revision or recheck occurred; the positive case
was not started. Workbench and production defaults remain unchanged.

Adjudication: do NOT adopt this two-stage implementation as a reliable Coach.
Its first stage only extracts spans; the second still combines full numerical,
source, advice, scope and explanatory duties. It did not actually isolate the
scope-interpretation task that earlier narrow diagnostics investigated. Dense
positional arrays also introduce unnecessary omission/misalignment failure modes.
These are design findings, not evidence that a new prompt or a larger budget
would fix model semantics. Stop further paid runs of this candidate.

Unique next engineering action: one OFFLINE revision of the workflow decision,
using the saved responses. Compare a first pass that performs factual review AND
finds inference targets with a second pass dedicated to interpretation of those
inference targets. The latter must retain the complete report/facts for context,
use explicit short target handles for a batch (host owns the source text), and use
sparse explicit source references for genuinely new claims. Do not demand 28 empty
arrays or let one skipped result shift every later target. Show how numerical
failure diagnostics, omitted inferences, headings, negation, later conflict and
all final issues survive composition before registering another candidate.
Demonstrate a concrete way to challenge a data-based rationalization of an
undefined term; changing JSON shape alone is insufficient. If the two-call/five-
call budget cannot accommodate a reliable correction path, state that conflict
instead of disguising another full review as a narrow scope check.

No new live run is authorized by this *document's* next action until that offline
integration evidence and same-SHA public checks exist; standing user authorization
for bounded project work remains in force, so this is not a request for repeated
user permission. The gate is concrete engineering evidence. Stage 8E remains in
progress. The four-surface visual/product follow-up remains deferred in its memo.

## 2026-09-15 Integrated v1 observation and v2 actual-target budget repair

Implementation d70416206b8febdcb8aa6a21f27c427cb7f21aa7 passed all three jobs in
Actions 34946858753. The full-report pair stopped before assessment:
`integrated-review-d704162-definitions` planned 2 / started 1 / finalized 1 /
interrupted 0 / not started 1. Discovery returned complete stop and selected 57
valid source spans. Returned input 2445 + output 6396 = 8841 tokens, one Provider
request, no unknown usage. Cumulative reservations are at least 170. No semantic
assessment, report revision or recheck occurred, so this is not a semantic failure
or success. Original request/response/receipt files remain unchanged; the new
manual-audit-v1.json records the independent offline diagnosis.

The assessment builder reached 64348 input-ceiling tokens, above 64000, and stopped
locally BEFORE a second Provider call. The earlier complete-block shape measured
only 28 targets for this report. That estimate was not a generated-span bound;
the actual source selection legitimately expanded it. This exposed a gap in the
candidate request builder, not output exhaustion, GLM profile or a lost stream.

Adopt a distinct `golden-integrated-review-v2` experiment identity. Avoid a redundant
quote_ref wrapper around every known target and check the actual assembled
assessment after budget metadata. When needed, remove only optional numeric-source
navigation entries and increase their explicit omitted count; all source values,
report text, target references, generation facts, knowledge, instructions and schema
remain complete. Stop before I/O if the complete core still cannot fit. Keep
63936 as the preparation threshold, allowing 64 tokens of headroom within the same
64000 input limit for a shorter deadline representation. Do not raise any limits.

Offline replay of the exact saved 57 targets now measures 63136 after the budget
wrapper with the complete core unchanged. This shape needs no navigation removal;
a separate boundary regression exercises actual removal and rejects a core overrun.
The existing request/response files are not reclassified as a successful report.
31 focused tests pass. The ten full-block shapes plus historical revision measure
359276 total reservation in data/evaluation/results/golden_integrated_workflow_v2.json;
these remain measured shapes, not a guarantee for arbitrary future output or time.

Next: same-SHA public checks for v2, then a fresh complete-report definition pair
through discovery, assessment, optional revision and full recheck. Keep old v1
failure, old usage, source data and frozen labels. The new run has its own shared
report budget; it must not pretend the earlier extraction was a new model result.
Stop on a protocol/transport/semantic failure and inspect the concrete evidence.
No production registration, Workbench admission, redesign or stage advancement.

## 2026-09-15 Integrated whole-report candidate (offline verified, live pending)

The new isolated `golden-integrated-review-v1` prototype separates source discovery
from assessment. Discovery receives the complete ordered report and user request,
selects spans without a verdict, and does not need the numeric/knowledge payload.
Assessment receives ALL generation facts, inference facts/provenance, deterministic
source facts, knowledge and the complete report. Model-selected spans become
host-owned targets; complete headings and any block with no selected spans are
always retained. Assessment judges each target by position and separately sweeps
all source blocks for omitted assertions. It may add a later conflicting statement;
a correct first clause cannot make an omitted later clause disappear structurally.
A model can still misclassify or overlook a sentence: ordinal/coverage validation
is not evidence of semantic correctness.

Two calls per evaluation are allocated to discovery and assessment. If discovery
format/coverage is invalid, concrete bounded locations are included in assessment,
which then receives every complete block as a target and must discover/split out
claims itself. A valid prompt-injection finding stops immediately, even with other
invalid discovery fields. After assessment, the unchanged contextual validators
check source, evidence, numerical support, scope, headings and issue relations.
Additional numerical checks reject unsupported numbers in explanations; correct
numbers or fluent text can still make wrong mean-versus-individual claims. This
remains a real semantic acceptance item, with an explicit test of the limitation.

Assessment issues bind to target quotes on the host and pass to the existing full
revision request. Canonical diagnostic locations are retained on a rejected final
assessment. Tradeoff: there is no third format-repair call after assessment; an
invalid second output stops the report, rather than re-running silently. This is
not a claim that the old diagnostic helper now repairs frozen Coach 1.3.27.
The workflow permits one revision and a fresh two-call full recheck, at most five
calls. Recheck requires the exact revised text and unchanged facts/knowledge.

`ReceiptedStreamProvider` reads its own reservation and terminal result, after the
real `CoachBudgetedProvider` transformation. The host compares exact issued-input
bytes with that trusted SHA; model output has no source/target identity fields.
It uses existing high/32768/300-second transport, zero retries, and the shared
401920-token/900-second budget. No old Coach/Skill/program registration is changed.
This is an explicit experiment entry, not a production default or new release.

Files: `golden_integrated_review.py` owns requests, source restoration and canonical
validation; `golden_integrated_runtime.py` owns receipt binding, state transitions,
revision/recheck and budget integration; `run_golden_integrated_review.py` is the
isolated real entry; `test_golden_integrated_review.py` supplies scripted protocol
and control-flow tests. These scripts reuse historical validators without editing
old outputs, labels or receipts. The meaningful owner-learning distinction is:
source identity belongs to the host, discovery/interpretation belongs to the
model, and acceptance requires both transport and independently reviewed meaning.

Offline measurement on ten frozen complete reports is in
`data/evaluation/results/golden_integrated_workflow_v1.json`. Discovery requests
measure 12500–12676 input-ceiling tokens; assessment shapes 58648–58866. One complete
historical revision shape measures 53584. Combining the maxima twice and all five
32768 output reservations gives 360508, below 401920. These are conservative size
estimates, not billed usage, model accuracy or an arbitrary-future-output bound.
Every actual generated target/assessment/revision is checked again. Five calls at
300 seconds each do not fit 900 seconds; the shared deadline still stops overruns.

Implementation choice: the first prototype duplicated target text plus unbounded
numeric navigation and reached 80352 assessment input tokens offline. It was
rejected BEFORE external I/O. The adopted request references existing complete
source blocks and bounds navigation to 3000 JSON characters, without dropping the
underlying facts. This does not increase output limits or lower reasoning effort.

Next live gate after same-SHA public checks: one explicit-definition pair of
complete reports with no supplied target/label to either model request. At most
five calls and one revision per report; stop the pair on initial label mismatch,
invalid output, transport failure or unsuccessful revision/recheck. Persist the
original initial result separately so later revision never erases a control
failure. Manually inspect definitions, means versus individual comparisons,
source facts, all discovered targets and additions before any acceptance. Only
then consider the remaining frozen heading/negation/future/conflict pairs. This
is not a third narrow target probe and is not a held-out quality score.

Run preview with `python -m scripts.run_golden_integrated_review --source-run
 data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report
 data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md`.
Real use appends `--execute --pair 1 --ci-run <same-SHA-success> --env-file
 <private-path> --run-id integrated-review-<sha>-definitions` and writes only to
private run artifacts. Provider reservation/returned usage are counted separately;
interrupted and unstarted cases remain explicit. Stage 8E stays in progress,
Workbench report admission and the four-surface redesign remain pending.

## 2026-09-15 v2 observation and host-owned target binding

Public closeout: offline binding implementation
`753267aa57a34c1460ac37d2f6c21a0ae7aa29fc` passed all three jobs in Actions
`34943310239`. The final issued-input/tool-choice guard also passed its seven
focused tests after the 43-test regression run. This closeout changes documents
only and binds evidence to that implementation SHA; it does not claim a new
model result, runtime registration or whole-report admission. Temporary Git API
relay code is removed after publishing this record. The next action below is
full-report offline integration design/verification, not a third target probe.

Implementation `86358e85839b00128eb4d64672780b22b1f12674` passed Actions
`34941920885`, all three jobs. `context-relation-86358e8-v2` stopped after case 3:
planned 4 / started 3 / finalized 3 / interrupted 0 / not started 1. All three
Provider calls completed with stop. Returned input 28000 + output 1936 = **29936
tokens**, no unknown usage. Cumulative reservations are at least **169**. The two
narrow experiments together used 7 complete calls and 69136 returned tokens.
Earlier historical unknown usage remains unknown.

| Case | V2 observation | Boundary |
|---|---|---|
| stable_unbounded | valid, needs_clarification | Correct target classification |
| stable_defined_before | valid, sample_defined | Explicit definition recognized; explanation inserts group means into an individual-game comparison and is not fully fact-validated |
| heading_unbounded | raw needs_clarification, protocol invalid | Model echoes the complete visible heading while omitting `## ` in target_ref; exact target check rejects |
| heading_defined_after | not started | No v2 result |

Terminal times: 10.484 / 6.297 / 18.094 seconds. The third interpretation correctly
identified missing meaning rather than definite extrapolation, but is not an
accepted v2 result. Do not count it as passing or combine versions into all four.
The previous definition-copy defect has not received a v2 fourth-case result.
No third paid diagnostic follows this batch.

Root design correction: a known request target is host-owned identity. Asking the
model to echo its Markdown representation or source digest is redundant and does
not prove semantic correctness. This recreates a copying failure after source
references were introduced to reduce copying. Keep model-chosen definition
references, but bind the requested target and source through the actual request.

`golden_bound_scope_review.py` is an **offline seam**, not a registered runtime.
It preserves all complete data and the single target in the input; output contains
only disposition, context_ref and explanation. `seal_issued_request` runs after
trusted budget-wrapper changes, verifies unchanged messages/schema, and computes
the same exact byte SHA as `golden_stream_bridge.validate_request`. `decode`
requires that SHA from the trusted transport receipt, restores the full original
target including Markdown, resolves any definition reference, and retains the
model explanation. The receipt SHA must never come from model JSON. Actual
transport/runtime integration is still required; a caller-provided fake receipt
or a unit test is not end-to-end provenance evidence.

Data flow: prepare full input → budget wrapper → seal exact issued bytes → trusted
transport response/receipt → compare request SHA → parse judgment → restore host
source/target and model-chosen context. Changed input/schema, wrong receipt, stale
reference, incomplete stream and model-injected identity fields reject. A source
reference still does not prove meaning, and numerical explanation errors remain
semantic work. No automatic whole-report pass is produced.

Verification: 43 focused/adjacent tests passed. The old third response is preserved;
an explicitly scripted projection removes its redundant model identity fields
and demonstrates that the host restores the exact `##` heading. This is not a new
model result or acceptance of the old response. Full post-budget request sizes
are in `data/evaluation/results/golden_bound_scope_review_v1.json`. Current tests
exercise binding after a changed deadline/metadata, mismatch rejection, exact
heading restoration, literal context restoration and unchanged complete facts.
Run `python -m pytest tests/test_golden_bound_scope_review.py
 tests/test_golden_context_relation_probe_v2.py tests/test_golden_context_diagnostics.py`
for the core offline checks. No real CLI mode exists for this seam.

Next bounded engineering action: prove the unified full-report data flow and
budget offline before an isolated runtime candidate. It must automatically find
review targets, preserve numerical/source/coverage/security checks, use the
concrete diagnostic feedback, and schedule scope interpretation within at most
two calls per evaluation and one revision/five calls per report. Retain the
existing shared 401920-token/900-second bound; do not assume five maximum-sized
requests fit. Verify negation, explicit extrapolation, missing target discovery
and later contradictory claims as well as these four scope controls. The narrow
runner's accept→sample_defined mapping is intentionally limited to these four
cases and must not be reused for negation or whole-report quality scoring.

Do not launch another isolated target-only probe, register the offline seam as a
finished Coach, or replace the Workbench report before the integrated evidence.
Stage 8E stays in progress. Learning outcome: source identity is a transport/host
responsibility; model interpretation is a separate, still fallible obligation.

## 2026-09-15 narrow diagnostic v1 result and v2 correction

The diagnostic implementation `6a73101dbf6d342686fe6aa219f19ad7d247cf95` passed
all three jobs in Actions `34940550415`. The normal Git transport failed twice;
the authenticated Git Data API uploaded identical blobs/tree/commit, verified
the exact SHA and advanced the branch with force=false. This did not create a
different implementation or bypass CI.

`context-relation-6a73101-critical` completed four calls, all stop: 37452 input +
1748 output = **39200 returned tokens**, no unknown usage. Cumulative Provider
reservations are at least **166**. Three outputs were protocol-valid, one invalid;
only two targets matched. Terminal times were 7.375, 6.031, 13.266 and 6.844 seconds.
This is the same high profile and capacity; smaller requests/outputs and a changed
task were observed, not a controlled proof of a single latency cause.

| Target | v1 result | Manual finding |
|---|---|---|
| stable_unbounded | valid / needs_clarification | Correct target classification; an additional claim of conflict with another single-game warning is not separately validated |
| stable_defined_before | valid / sample_defined | Correct explicit definition |
| heading_unbounded | valid / beyond_sample | Overstates missing meaning as a definite extrapolation; explanation also incorrectly says 2–3 games in each mid group |
| heading_defined_after | invalid / raw sample_defined | Correct definition reference and interpretation, but paraphrase violated the required verbatim defined_meaning field |

The frozen report has two mid wins and two mid losses, not 2–3 per group. Never
count the heading's refusal as the correct clarify label or the invalid last
response as a successful result. The private manual audit records these details;
all original inputs, outputs and receipts remain untouched.

The last failure exposes avoidable protocol duplication: context_ref already
recovers the complete original definition. Requiring a second full verbatim
copy does not prove entailment and caused a faithful paraphrase to reject.
**Adopt a separate diagnostic v2**, removing referring_expression/defined_meaning,
keeping the exact target/context references and one natural-language explanation.
Do not relax v1 in place or mark its old invalid response accepted. The source
binding and disposition/context consistency still reject stale or forged input.

The v2 policy also distinguishes undefined wording from an explicit unsupported
extension. Missing meaning gets clarification; beyond_sample requires an actual
assertion beyond the evidence. This is a model judgment, not a keyword allowlist.
No old label changes. A scripted projection of the last v1 response demonstrates
v2 shape validity while retaining its original context, not new model quality.

Implementation: `golden_context_relation_probe_v2.py`; runner selects it only
with `--v2`, records experiment `golden-context-relation-probe-v2` and response
contract 2.0.0. Complete source data and high/32768/300-second settings are the
same. Measured full inputs are recorded in
`data/evaluation/results/golden_context_relation_probe_v2.json`. 36 related tests
passed, including unchanged v1 rejection, v2 reference rejection, full source
preservation, explicit dispatch and separate accounting.

Next: same-SHA public checks, then **one new four-case batch**, at most four calls,
no correction or revision, existing 401920-token/900-second batch caps. Run the
same diagnostic command with `--v2` and a fresh `context-relation-<sha>-v2` run ID.
Stop on protocol/transport failure, manually inspect all decisions/explanations,
and do not automatically start a third diagnostic batch if it fails. These two
small experiments are not a whole-report acceptance gate. A later integrated
candidate must fit factual checks, scope judgment and correction within the
existing evaluation/revision call budget, before Workbench report admission.

## 2026-09-15 four-case observation and next diagnostic experiment

Implementation `9c5aad9cb2e9c3764b23e78435c7daa5048763fe` passed all three jobs
in Actions `34936247772`. The critical real batch did not pass. The original
receipt and 47 original files remain unchanged; `audit-v2.json` is a separate
private replay, not a replacement receipt or new model output.

| Case | Accepted final | Manual assessment |
|---|---|---|
| stable_unbounded | 95/pass, after anchor-only patch | Wrong acceptance: section heading treated as definition of stability |
| stable_defined_before | 96/pass | Correct explicit forward definition |
| heading_unbounded | 95/pass, after full reassessment | Wrong acceptance: unrelated summary limitation treated as definition of this heading |
| heading_defined_after | None | Initial definition reasoning appropriate, but numeric/anchor contract failed; reassessment connection failed |

Seven reservations, six complete responses: 78479 input + 66435 output = 144914
returned tokens. One interrupted request has unknown usage; cumulative requests
are at least 162. Counts are planned 4 / started 4 / finalized 3 / interrupted 1 /
not started 0. Last worker failed at 151438 ms with `connection_failed`; there was
no visible content, finish or usage. This is not evidence of a 300-second deadline
or output exhaustion. Underlying connection cause remains unknown.

Scoring defect: the first target was fully quoted except its final Chinese full
stop. The prior exact-string scorer called this target absent. The corrected
scorer requires its original block and every word, allowing only omission of
that final full stop. It now records wrong acceptance; neither target nor whole
report becomes correct. Old labels, evaluations and receipts are preserved.

Diagnostic regression: contextual reassessment sent only one error code. The new
offline helper reports claim/reference positions and actual unsupported numeric
source candidates without changing a response or accepting one. Independent
claim diagnosis also reveals two anchors hidden behind the last case's initial
420 error. Actual queue candidates reference all five `/queue_id` fields. Five
saved response replays with complete feedback measure 57910–59848 input ceilings,
below 64000. This helper is not yet part of frozen Coach 1.3.27.

Decision: reject another unchanged full-review run or a regex that declares
semantic correctness. First isolate the interpretation question in a small
**diagnostic experiment**, not a replacement evaluator: send each of the same
four complete reports with full facts, knowledge and one source-bound target.
Do not send expected labels, case names, prior verdicts, or prior explanations.
Ask only whether the exact assertion has an explicit definition/negation or
needs clarification; require the actual referring phrase and defined meaning
from source text. Program validation checks exact references and output shape,
not whether those phrases semantically establish the relationship.

This changes task decomposition and output obligation, not GLM profile. Freeze
an experiment ID and implementation/source hashes, validate inputs and public CI,
then make at most four separate calls (one per case; no repair, report revision,
or automatic rerun). Keep high / 32768 output / 300 seconds / zero SDK retries
and 401920 tokens / 900 seconds for the batch. Stop on protocol or transport
failure; preserve unknown usage and unfinished cases. Compare both positive and
negative cases manually. It is an assistant-labeled development diagnostic,
not holdout, not whole-report acceptance, and cannot prove task size alone caused
the previous failure. A production candidate needs a budgeted integration
choice and full evaluation/revision validation after this experiment.

Data/control flow: frozen complete report + facts + target reference → narrow
model judgment → reference/shape validation → immutable response and score →
manual semantic audit. The legacy evaluator and product report are untouched.
Code, tests, runbook and measured results are recorded with this section as the
experiment is completed. Stage 8E and all deferred Workbench scope stay unchanged.

### Diagnostic implementation and verification

`golden_context_diagnostics.py` supplies bounded reference/numeric hints and
unabridged context pairs for inspection. `run_golden_context_controls.py` fixes
terminal-full-stop scoring while retaining exact block/word binding.
`golden_context_relation_probe.py` and `run_golden_context_relation_probe.py`
implement the independent diagnostic contract `context_relation_probe/1.0.0`
and experiment `golden-context-relation-probe-v1`. This is not a new Coach
version or a replacement for frozen 1.3.27. No production runtime is registered.

The complete four requests measure 36708, 36870, 36736, and 36800 input ceilings;
see `data/evaluation/results/golden_context_relation_probe_v1.json`. At their
output caps their total reservation estimate is 278186, below the unchanged
401920 batch limit. Every actual request is checked again. This is not token
usage or a guarantee all four finish within 900 seconds.

Runbook: `python -m scripts.run_golden_context_relation_probe --source-run
 data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report
 data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md`
previews without secret/CI/Provider I/O. Only after same-SHA three-job CI, append
`--execute --env-file <private-path> --ci-run <run> --run-id context-relation-<sha>-critical`.
All four cases and their already frozen labels are fixed by the manifest. Labels
and prior verdicts/explanations never enter a request. Existing run directories
are refused. Reservations precede I/O; transport failures preserve started but
unfinished cases, and invalid JSON/reference output stops after saving that case.
Semantic disagreement alone completes the selected four; no automatic retry.

107 focused/adjacent regressions passed; after adding missing-content diagnostics,
all 11 diagnostic tests passed again. Compilation and governance checks passed.
These regressions cover scoring, independent location/numeric diagnosis,
full request/transport budgeting, literal reference validation, zero-I/O preview,
one-call execution, and protocol/transport/semantic counter distinctions.
The verifier checks a phrase exists, not whether it really defines the target.
A source-valid but semantically wrong judgment remains a failed diagnostic.

## 2026-09-15 isolated candidate implementation (historical preparation)

The next implementation is now opt-in Coach **1.3.27**, Skill **0.5.27**, Program
**2.3.27**, evaluation **1.20.0**, policy `golden-context-reference-v1`. This is an
unadmitted development candidate, not a production/default selection. Its Coach
snapshot is `22dff4e9c22367a009a32804a3fbfab868e4d556e14dabcc303932e800c349a5`.
The earlier offline experiment and historical v7/v8 results below remain distinct.

Problem/principle: the old local-only anchor contract cannot express a definition
in a preceding paragraph that explicitly names the next sentence, or a paragraph
that explicitly defines a heading. The new contract preserves that connection
without concatenating different source sentences or treating proximity as proof.

`golden_context_review.py` defines integer quote/evidence references, complete
ordered inventories, heading classifications and an optional context reference.
`defines_scope` corresponds to `selected_sample`; `negates` corresponds to
`question_or_negation`. A contextual anchor comes from the actual referenced
context. Both exact texts, their block identities and the model's explanation
survive into canonical audits, persisted evaluations and report revision.
Unknown/stale/ambiguous references reject; a context relation is a model claim,
not a deterministic proof that the interpretation follows. Every remaining
paragraph still requires review. Heading misclassification and omitted claims
remain semantic risks that inventories alone cannot detect.

The canonical result retains the existing verdict/issue consistency, scope,
coverage, evidence existence, direct numeric support and table-antecedent checks.
It additionally rejects duplicate same-block claims and duplicate evidence refs.
It does not rewrite old results or automatically inherit their acceptance.

`golden_context_runtime.py` makes at most two requests per evaluation. If full
validation finds only one to four non-context scope-anchor errors, the second
request may change only those anchors. The exact original response and source
digests bind the patch. Any other failure selects one complete reassessment.
A patch response may request reassessment, but that stops the current evaluation
as invalid: it does not create a third call. No new report revision is permitted
in this control batch. Typed prompt-injection findings stop the evaluation; raw
responses/reservations remain in the existing private Counted/stream journals.

`golden_context_requests.py` retains complete report context, facts/provenance,
deterministic report, retrieved knowledge and the observed-user request. It
checks every outgoing input ceiling before I/O. GLM high, 32768 output, 300-second
request deadline, zero SDK retry and the existing per-pair 401920-token/900-second
budget remain unchanged. The common composition entry also explicitly accepts
this new identity and selects its evaluator and reviser; the default stays put.

Full-input review: `golden_context_reports_v1.json` freezes ten complete-report
hashes and separate target/report labels before model execution. The assembler
replaces the first risk bullet in section 3 with the corresponding diagnostic
fragment, removing that bullet's pre-existing local stability definition; the
second risk bullet and all other sections remain. The complete base report was
read, each inserted context reviewed, and the new target/report rationale stored
alongside each hash. These are assistant-reviewed development cases, not a
held-out set or labels individually approved by the user. The original twelve
cases and scores are untouched. Private assembled inputs are in
`data/runs/inference_development/context-inputs-20260915-v1/`.

Measured before candidate registration, `golden_context_requests_v1.json` records
initial input ceilings 57692–57866 and reassessment 57882–58054 across the ten
complete inputs. Projecting the saved v8 pair-04 response and manually correcting
its anchor produces a **scripted** patch-request ceiling 49998 and revision
ceiling 59246. All are below 64000; the projection is neither new model output
nor a worst-case guarantee. Every future request is measured again.

Data/control flow: complete report and facts → source index → independent model
review → exact reference resolution → canonical checks → accepted result, one
bounded anchor correction, or one full reassessment → final full validation.
Accepted contextual audits can pass through the existing revision seam; control
evaluation itself never revises the source report or writes Workbench content.

Verification: 97 focused and adjacent tests passed, including explicit
cross-paragraph definitions, quoted negation, continued rejection of a later
wrong claim, unchanged numerical rejection, stale/forged references, patch escape
and the two-call limit, typed security stop, context preservation in revision,
actual composition factory selection, separate target/report scoring, and
label-blind zero-I/O preview. An additional 102 existing Coach repair/runtime/
product-acceptance tests passed. Old v7/v8/experiment tests still pass. These tests
prove protocol behavior and wiring, not model accuracy. Public CI and real
semantic observations are still required for this new implementation.

Runbook: `python -m scripts.run_golden_context_controls --source-run
data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report
data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md`
is a zero-I/O preview with full initial-request measurements. It defaults to
definition and heading pairs only (four cases, at most eight calls total).
After same-SHA public success, add `--execute --env-file <private-path>
--ci-run <run> --run-id context-controls-<sha>-critical`. Existing output paths
are refused. Reported counters separate planned/started/finalized/interrupted
and not-started. Raw transport/timeout/auth failures stop the remainder. A final
protocol-invalid case is saved and also stops the suite. Semantically wrong but
valid results finish the selected contrast batch for comparison; no automatic
remaining-six/full-twelve run follows. Inspect each actual target and full report
before deciding the next bounded run. Do not combine versions into an all-pass
score. If the critical set fails, classify representation vs interpretation vs
transport and change the corresponding design before further paid repetition.

Learning/interview boundary: implemented a versioned source/context review
protocol, bounded correction, preserved canonical revision evidence and frozen
full-input contrasts; independent model quality and product admission remain
unverified. Stage 8E stays in progress and the Workbench design memo stays queued.

## Problem and scope

The goal remains a usable, evidence-grounded Coach report followed by revision,
reevaluation and Workbench consumption. The 1.3.25 original-report cycle succeeded;
the independent development controls did not. The next candidate must improve
completion without confusing protocol validity with correct reasoning.

The broader retrospective covered real-data entry on September 10, initial metric
and cohort errors on September 11, the quota-stop handoff, the mistaken Luna
attribution and subsequent scope/evidence contracts. Historical source defects,
the incorrect low diagnostic and its accounting/journal regressions have separate
fixes. They are not a single Provider failure. Luna means Codex execution
collaboration and has no bearing on the product's GLM profile.

Every new evaluation should not be a longer copy of the previous checklist.
Current repair regenerates the whole evaluation; failed original-quote, inventory
or scope references can recur elsewhere. Native `json_object` is not strict
server-side enforcement of the local schema. Complete inventories still do not
prove that the model discovered every assertion.

## Evidence and alternatives

The reproducible measurement is
`data/evaluation/results/golden_review_workflow_offline_v2.json`; its full private
per-response record is under
`data/runs/inference_development/review-workflow-20260915-offline-v2/`.
Only saved responses are inspected; no new model request is made.

| Measure | 1.3.25 controls | 1.3.26 controls |
|---|---:|---:|
| Complete saved responses | 18 | 10 |
| Valid under original contract | 8 | 5 |
| Reversible indexed projections | 17 | 6 |
| Compact original characters, projectable subset | 139543 | 51638 |
| Indexed envelope characters, same subset | 92637 | 33930 |
| Quotes / whole-block matches / single sentence-unit matches | 252 / 178 / 167 | 143 / 95 / 80 |

All 13 originally valid responses remain valid and identical after restoration.
The ten projectable invalid responses remain invalid. Five responses are not
projected: two wrong inventories, two extra-JSON/text suffixes and one invalid
source quote. No projection repairs a historical response or creates an accepted
historical evaluation. The 23 reversible projections shrink from 191181 to 126567
compact characters (33.8%). This is not a token, latency or billing measurement.
Claims/issues quote text and copied block IDs alone were about 19–20% of visible
output; shorter evidence references and serialized fields contribute to the full
projection difference. No reasoning-time reduction is inferred.

Alternatives:

- Whole-block references only: reject as the sole representation. Only 273/395
  existing claim quotes equal a whole block; enlarging every quote changes the
  scope and can combine correct and incorrect assertions.
- Sentence units only: reject as the sole representation. A simple Chinese
  punctuation split matches only 247/395 quotes. More importantly, defining scope
  or negation across units must not be lost. This is a measured baseline, not a
  claim that no better sentence parser could exist.
- Character offsets: not selected. They add model-side counting and allow a
  syntactically legal range to point at the wrong text.
- Whole block plus unique short endpoints: selected for the isolated candidate.
  Program-owned ordered IDs and fact keys become integer references; a quote is
  a whole block or a unique literal head/tail within it. Ambiguous, missing and
  cross-block selections reject instead of choosing the first match.
- Strip a malformed JSON suffix or regenerate all judgments for every formatting
  problem: not selected as a general repair mechanism. Preserve raw output and
  separate reference repair from reassessment.

## Decisions and responsibilities

`SourceIndex` retains the full original report and ordered blocks. Its digest
binds report text, fact values, provenance and registry identity. The model still
sees complete ordered context; input is not split into isolated semantic tasks.
`index_review` / `restore_review` preserve every existing judgment, quote, issue,
explanation and reference. `validate_indexed_review` then runs the original full
validator; indexing does not upgrade a verdict or claim to have checked content.
There is no new dependency, Provider registration, model setting or default path.

The local-correction prototype allows only diagnosed `scope_anchor` replacements
in at most four existing claims. The patch binds the exact raw-response digest
and source digest. It cannot add/remove claims or issues, alter evidence, scope,
score or wording, or edit unrelated locations. Duplicate/stale/wrong targets,
unknown references and failed final validation reject. Non-JSON, duplicate-key,
inventory, security and other semantic/evidence problems require reassessment.
The model can explicitly return `needs_reassessment` with a reason when it finds
another problem; the protocol must not force retention of a mistaken verdict.

The latest timeout's preceding response has one eligible reference defect. A
**human-specified offline** patch changes `中单同位置` to the existing literal
`混合样本`; this restores the original validator's 95/pass result without changing
other judgments. A nonexistent `单局` anchor was rejected during the experiment.
This demonstrates the boundary, not autonomous correction or semantic quality.
The compact patch is 257 characters. The full request builder includes the report,
previous evaluation, facts, deterministic source and complete retrieved knowledge.
Its actual local input ceiling is 53844 versus 58806 for existing whole-review
correction, both below 64000. Output 32768 / 300 seconds are unchanged. Only this
saved shape is measured; every future request still needs its own budget check.

## Context-sensitive rubric and old labels

The frozen twelve labels and all historical scores remain unchanged. Their
original single-claim labels were later embedded into a revised report. That
embedding supplies nearby definitions and changes the semantic task. The audit
below is a new assessment, not a relabeling to obtain a passing score.

| Frozen case | Current contextual assessment |
|---|---|
| selected_pairs | Retain accept: individual values support the stated four-game comparison. |
| selected_means | Retain accept: correct means and explicit limitation; whole-report issues are separate. |
| stable_negation | Retain accept: a denial / observation request, not a stability assertion. |
| stable_local_definition | Retain accept: local direction consistency is expressly defined. |
| long_term | Retain reject: an explicit long-term inference lacks evidence. |
| future_without_keyword | Retain reject: explicit prediction of all future losses lacks evidence. |
| disclaimer_conflict | Retain reject: the disclaimer does not cancel the ensuing long-term assertion. |
| causal_leap | Retain reject: correlation does not establish the cause of defeat. |
| original_stable | Keep historical clarify; review whether it is read as an overview of the adjacent defined comparison. Do not report contract mismatch alone as universal semantic failure. |
| original_reliable | Keep historical clarify; almost the same phrase is defined immediately afterward, so contextual linkage needs separate paired evaluation. |
| reliable_without_keyword | Retain clarify on present evidence: a reliable win/loss discriminator is stronger than a descriptive sample difference. |
| persistent_heading | Keep historical clarify; the body limits its comparison, but how it qualifies this heading needs explicit contextual tests. |

Product-quality rules distinguish wrong facts, unsupported inferences, unresolved
scope and optional editorial improvements. Explicit definitions referring to a
following sentence or preceding heading may establish scope across blocks. Mere
adjacency or a generic disclaimer does not establish that connection. These are
semantic judgments; a `context_ref` can establish where the text is, not whether
the interpretation follows. Quoted assertions explicitly rejected by the author
must not be treated as endorsed claims. A correct target does not make a report
with a different erroneous claim acceptable.

`golden_context_controls_v1.json` adds five pairs / ten assistant-authored
development examples for these distinctions. It records target and whole-report
expectations separately. These are not held-out cases, user-signed labels or
model-validated results. Their raw data must never be sent with expected labels.
These are diagnostic fragments, not ready-to-run complete Coach reports. Before
live evaluation, the final complete input and both labels must be reviewed and
frozen together. Do not send a fragment to the full-report evaluator or inherit
its isolated label after embedding without reviewing the resulting context.
The existing local-anchor-only validator is retained in this experiment to prove
representation equivalence; that does **not** settle the new contextual rubric.

## Verification, operation and next implementation

Code map: `golden_review_experiment.py`, `check_golden_review_workflow.py`,
`test_golden_review_experiment.py`, `test_golden_review_measurement.py`.
Data flow: full report / facts → program-owned index → model-reference-shaped
projection → exact restoration → original validator. For correction: original
response + diagnostics → bounded patch or reassessment → complete revalidation.

Tests cover mixed assertions, retained adjacent context, Markdown/table fidelity,
ambiguous/stale/forged references, unchanged facts and judgments, rejection of JSON
suffixes and duplicate keys, patch escape to reassessment, full request limits,
and interrupted-case accounting. A known misclassified-heading fixture still
passes, explicitly documenting that protocol tests do not prove semantic quality.
The focused experiment, measurement, scope-runner and adjacent v7/v8 suite passed
66 tests locally; compilation, governance and diff checks passed. Implementation
`8d3857251e147ff2ce4f13efd9275a9db3aa7653` passed Actions `34924328754`: all
three jobs (`postgres-migrations`, `packaging-smoke`, `pytest`) succeeded on that
exact SHA. This verifies engineering behavior, not model semantic quality.

The scope runner now additionally reports `case_counts` with planned, started,
finalized, interrupted and not_started, preserving the legacy `attempted` field
with an explicit finalized-cases meaning. Start means the case input was written;
Provider reservations are counted separately. Old receipts are never rewritten.

Run the measurement module with `--summary`, `--source-run`, the two `--runs`, and
new `--output` / `--public-output` paths. It refuses overwrites. Private output
contains per-response hashes/diagnostics; public output contains counts, hashes
and size comparisons, not report bodies. Historical responses remain immutable.

Next: implement one isolated candidate using source references, explicit
contextual support links and bounded correction; measure its complete requests
before registration. A context claim must retain its own identity while naming
the text that defines or negates it. Preserve fact/source/numeric and whole-report
checks. After same-implementation public verification, prioritize the four
definition/heading contrast cases before the remaining context cases and full
frozen regression. A failure must distinguish completion, representation and
semantic interpretation; do not stitch different versions into an all-pass batch.
No further limit increase or model downgrade is selected.

The old original-report success, observed ShowMaker identity, Workbench manual
report and saved notes stay valid. Review/Coach/Training/Evidence and visual work
remain in the September 11 design memo. Stage 8E and automatic quality stay in
progress. Interview wording: built a lossless reference experiment and measured
its limits; not proved reliable autonomous review or production adoption.

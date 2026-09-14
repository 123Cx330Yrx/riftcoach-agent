# Golden-slice inference audit and next repair batch

Status: offline evidence and repair design complete; automatic semantic repair unverified.

## Confirmed failure

The frozen 1.3.6 final report (SHA-256
`aade1720b7b2633cfb7842c175609d102b3504a71207a7ed8f70e86b3ff5fcae`)
says “视野意识在辅助局（90 分）体现” and “输局发育与输出同时塌陷”.
Its final evaluation returned score 95, pass and no issues. The saved evaluation
explicitly praised the nearby role/causality disclaimers. Those disclaimers do not
support either claim: role distinction does not establish awareness, and avoiding
a causal claim does not make a cross-role deficit inference valid.

The five source rows contain four MIDDLE games (two wins/two losses) and one
UTILITY loss. All-sample win CS is 8.805/min and loss CS is about 6.4533/min.
Within MIDDLE, loss CS is 9.01/min, above win CS 8.805/min. The direction reverses
when the support game is removed. Within-role damage differs (loss 617.52/min,
win 1286.755/min), but this is descriptive evidence, not proof of causality or
stable ability. The single support vision score is 90 and provides no observation
of ward timing, information use or decision quality.

## What the code establishes

`app/evaluation/coach_report.py:build_fact_pack` preserves match role, outcome,
CS, gold, damage and vision. `GroundedChatEvaluationAdapter` includes generation
facts, deterministic source facts and position policy under COMPACT_COACH_CONTRACT.
The existing policy-delivery test checks all nine offline request slots, including
evaluation/revision. The final saved evaluation also cites the actual metrics and
role constraints, so absent facts alone cannot explain this failure.

The 1.3.6 position policy already forbids cross-role performance conclusions.
`EvaluationResponseModelV12` checks verdict/issues consistency, not claim support.
`GroundedChatEvaluationAdapter` separately checks citation-marker presence; that
structural check cannot assess awareness or cohort comparability. Harness publishes
on pass, score threshold and empty issues. Revision consumes identified issues and
directly affected content, so an unreported semantic error can survive revision.
This proves an observable enforcement gap; it does not reveal internal model reasoning.

## Reusable offline evidence

`data/evaluation/datasets/golden_quality_counterexamples_v1.json` contains five
anonymized metric rows and ten human-labeled claims: five reject cases and five
positive controls. They cover original claims, paraphrases, ineffective disclaimers,
plain metric reporting, a question for video review, mixed-role descriptive caveats,
and valid same-role comparisons. These are development examples derived from the
known failure, never held-out acceptance data.

Run `python -B -m scripts.check_golden_quality_counterexamples` to recompute the
cohort reversal and validate the frozen evidence. It explicitly returns
model_evaluated=false and automatic_quality_fix_verified=false. It is not a
keyword classifier or an evaluator simulation. Six focused tests verify the
counterexample and reject changed roles/outcomes/inclusion/metrics or lost positive
controls; together with existing 1.3.6 delivery regression, nine tests passed.

## Selected next implementation batch

Use a new opt-in Coach version (planned 1.3.7) and versioned evaluation contract;
freeze all earlier prompts, fingerprints, reports and receipts. Reuse the existing
five/nine-call runtime and one-revision budget, with no additional model service.

1. Add deterministic role-by-outcome counts and means from included samples, with
   missing-value counts and explicit comparability limits. This supplies checkable
   facts; do not turn metric values into an ability score.
2. Require two explicit semantic audits in evaluation: metric-to-ability inference
   and cohort-based performance inference. Each finding must anchor an actual report
   quote and available evidence; unsupported/contradictory findings must appear in
   issues and cannot coexist with pass. A disclaimer elsewhere cannot discharge an
   unsupported claim. Exact quote/reference validation is deterministic; discovering
   and interpreting every natural-language claim remains model-dependent.
3. Feed the same evidence and policies to generation, evaluation and revision;
   correct affected headings, explanations and advice together. Retain honest plain
   observations and conditional video questions. Preserve existing citation, source,
   injection and score gates, the 70% revision rule and current resource budgets.
4. Offline checks must include absent/contradictory audit entries, unverifiable quote
   anchors, mixed-role means, missing metrics, legitimate comparisons and the full
   nine-call delivery/one-revision path. These prove wiring and rejection contracts,
   not semantic model success. Public same-SHA checks precede any new real run.
5. Later semantic validation must score all ten development controls, report false
   negatives and false positives separately, and use separately prepared unseen
   paraphrases before broader quality claims. Do not rerun old formal holdouts or
   relabel the old 95-point run; any real run gets a fresh identity and budget record.

No production auth/deployment, report-publication expansion, personal Training or
Workbench redesign belongs to this repair batch. The parent 8E checkpoint remains
in progress. This audit closes diagnosis/preparation, not the automatic quality gap.

## Learning and operations

Problem/principle: correct arithmetic is necessary but insufficient for a supported
claim. Design/implementation and code map are above; the flow is source rows →
cohort facts → claim audit → issues → revision → publication gate. Verification
separates evidence arithmetic, schema/wiring and actual semantic behavior. The local
runbook uses only the committed anonymized fixture; no credential, DB or network is
needed. Failure boundaries include missed claims, false positives and over-reliance
on disclaimers. Interview wording: “Diagnosed a false-negative evaluation with a
within-role reversal and prepared balanced development controls”; not “solved model
hallucinations” or “production evaluation proven”.

## Implementation and authorized real development check

2026-09-11同批推断修复接续：已实现显式Coach1.3.7的同位置/胜负事实投影、两类逐项推断审查、原句/证据键校验及修订回传；旧1.3.6身份及9调用/一次修订预算不变。相关120项测试通过。用户继续授权涵盖本批真实模型验证，公共同SHA三任务成功后执行10条已知开发正反例及旧报告评估→最多一次修订→复评，独立新身份最多25次Provider调用、每次64000输入/8192输出/90秒、SDK重试0。判定必须命中对应推断问题，其他拒绝原因不算修复。当前真实验证待执行，Provider累计68；唯一下一步为本批公共检查后完成该真实验证。8E仍in_progress，ShowMaker observed范围及后置Workbench设计不变。

Code: `app/evaluation/golden_inference_audit.py`, opt-in contract/context/composition wiring and `scripts/run_golden_inference_development.py`. The runner defaults to no-I/O preview, checks source and dataset identities, requires clean exact-SHA public CI, reserves each request before I/O and stores private outputs under a create-only run directory. Development cases require the expected unsupported inference kind, not merely any rejection. This is not a held-out admission run.


2026-09-11真实开发验证与接续修复：dd7efd3e019327692a7dda4c85b26b3b826476d4/Actions34594385409三任务同SHA成功。inference-dev-dd7efd3-20260911-a实际预约5次Provider请求，已返回可计量用量53977输入+9916输出=63893 tokens；被终止请求可能有未返回用量，不能视为零。前两条能力推断被识别，但单句控制触发整篇报告结构/来源缺失拒绝，且类别级unsupported迫使正确免责声明进入issues，不能据此统计完整误报率。为避免浪费主动终止第5次对应流子进程，父进程保留stopped/ProviderResponseError回执；这不是提供商自然故障。累计Provider预约73。新显式Coach1.3.8/evaluation1.4.0逐句status再聚合，1.3.7和旧证据冻结；案例改为向SHA固定人工校订完整报告插入一条原始标签句，先跑vision_fact正对照，若拒绝则停止其余控制但仍复核原报告。相邻92项及最终聚焦11项通过。唯一下一步为新实现公共CI后用全新身份完成真实复评，最多25次/批且一轮修订。8E仍in_progress，无个人Training或Workbench改版。


2026-09-11真实校验接续：a913b4881a4ecb56be98911dd4c098d059ad2265/Actions34595485432三任务成功。第二批b首个请求返回13297+2781 tokens后ValueError停止，具体原响应未留存，不能断言根因；新鲜单调用诊断c的完整正确对照96/pass（13297+3072），随后因诊断1调用上限正常停止，未完成10案。独立report-only诊断又1调用13107+5200 tokens，确认原句引用删除Markdown加粗并把中文引号换成英文引号，精确anchor拒绝，原报告尚未修订。四次运行共8次Provider预约，累计76；已返回计量114647 tokens，主动中止的未返回用量仍未知。只读诊断观察保存私有响应/anchor细节，范围收窄和上限已单独记录，不冒充完整批次。新增显式1.3.9将anchor校验纳入同一次结构化纠正机会，仍精确匹配且不增加9调用/一次修订预算；1.3.7/1.3.8冻结。真实入口新增显式report-only/选案、按范围缩小调用上限和响应私有留档。下一步为新补丁公共CI后优先原报告真实评估→修订→复评。


2026-09-11真实闭环收口（质量未通过）：f5caf181f4f3e0d030dcdf3b9c47c38024124df6/Actions34596802159同SHA三任务success，Python3071 passed/154 skipped/127 subtests、PostgreSQL210。新鲜inference-dev-f5caf18-20260911-report实际3调用38142输入+11767输出=49909 tokens，原报告78/needs_revision→一次修订→97/pass，格式/原句校验通过。但人工拒绝：视野90→意识原句仍在，前后两次audits都未覆盖；修订引入“稳定同位置差距/较稳定差异项”，四局同位置小样本不能支持稳定性。混合位置补刀方向及相关建议已改正，仅这一部分得到实证。完整10案未跑完，不能用receipt中0/0推算误报/漏报率。所有五次新鲜运行共11次Provider预约，累计79；已返回计量164556 tokens，被主动中止流可能另有未返回用量。原95分报告、人工副本、全部失败记录保留；新97分稿不替换Workbench、不发布可信报告。8E仍in_progress。唯一下一步为以本次漏句和稳定性误判设计并离线验证可核对的逐段/候选判断覆盖合同，再决定新鲜真实验证；不继续盲目重复同一提示。Workbench四块设计继续后置。

## Next bounded design: coverage before semantic approval

The observed defect is now concrete: valid audits can select only easy qualified
statements, omit an unsupported sentence, and still return pass. Per-claim status
and exact anchors establish internal consistency, not exhaustive coverage. The
97-point revised report also calls a four-game difference stable. This remains a
failed development review, even though the end-to-end revision path completed.

Next design should assign deterministic IDs to report paragraphs/list items and
require auditable treatment of every candidate block, preserving negations and
conditional questions. Assess input/output and time costs before implementation;
do not silently add another model stage, loosen the gate, or rewrite frozen
versions. Coverage does not prove semantic correctness, so evaluation must retain
balanced positive controls, ineffective disclaimers, newly observed stability
claims and unseen paraphrases. Do not replace reasoning with a blacklist of the
known two Chinese strings or accept a model score as manual review.

Operations: `scripts/run_golden_inference_development.py` now supports explicit
`--report-only` (maximum five calls) and `--case-id`; no flag runs all ten controls
then the report. It defaults to preview. Execution requires exact public CI,
clean checkout, a fresh run ID and fixed original/base report hashes. Provider
response text is private under the run directory; no reasoning text or credentials
are included in these response artifacts. A full positive control failure stops
remaining controls, and receipts state actual case count. Private manual-review
JSON is separate from the automatic evaluation and never overwrites its score.

Learning: source rows → role/outcome facts → model-selected claims → exact anchors
→ issues → one revision → reevaluation → manual development review. Tests establish
bounded control flow and contracts; the five real observations establish remaining
semantic failures. Interview wording: “Built versioned same-role inference audits,
found coverage gaps through real model evaluation, and prevented a 97-point false
pass from being presented as a successful repair.” The parent checkpoint is not
complete and its learning/quality exit gate is not advanced.

## 2026-09-11 selected coverage implementation

Explicit Coach 1.3.10 / Skill 0.5.10 / Program 2.3.10 / evaluation 1.5.0
adds deterministic block coverage to the existing single evaluator. Earlier
versions remain frozen. No additional model stage or package is introduced.

`app/evaluation/golden_inference_coverage.py` groups wrapped prose and table rows,
separates headings/list items, and retains every nonblank source line verbatim.
Order + text-hash IDs bind all blocks to this exact report. There is no semantic
keyword filter. A 24,000-character/64-block cap rejects oversized input before I/O.
Every block needs both inference classifications. Missing/duplicate/stale/order
mismatches reject; every unsupported classification must link to an unsupported
claim in that same block and an issue. Aggregate audit status must agree. Exact
anchors and coverage share the existing one structured correction, never two.
Security findings still reject before any correction. The status coverage survives
Harness artifacts and the revision projection. Revision receives original report,
issues and coverage, and its new report gets a newly derived inventory.

Tradeoff: coverage prevents silent omission but cannot prove a classification is
correct. Tests explicitly demonstrate a structurally complete yet semantically
wrong all-not-applicable answer, so no universal semantic guarantee is claimed.
A deterministic content blacklist and another model call were not selected.

Budget experiment: naively repeating the full report with its inventory produced
an actual request ceiling of 73,580, above 64,000. New-version-only compact JSON
preserves all values, and the indexed draft replaces the duplicate raw draft.
The original and 97-point reports each contain 27 blocks. Offline actual request
projections then fit the 64,000 limit (approximately 50–51k evaluation and 45–47k
revision); output 8,192, timeout 90 seconds, nine calls and one revision stay fixed.
`scripts/check_golden_coverage_requests.py` reproduces these private-input sizes
using a scripted Provider only. It is not model quality or latency evidence.

Validation: structural tampering, clause/negation retention, size rejection,
JSON roundtrip, security fail-before-repair, persistence and all frozen version
fingerprints; full nine-call replay and saved-report request-size checks. After
exact-SHA public CI, use a fresh report-only run against the immutable 97-point
counterexample (at most five calls), then balanced controls in a separate fresh
controls-only run (at most twenty calls) if the report path is usable. Existing
user authorization covers these bounded calls. Keep actual denominators and
manual review separate; do not replace the reviewed Workbench artifact on an
unexamined automatic pass. The 8E checkpoint and deferred design remain unchanged.


最终本地验证：144 passed、7 subtests，治理和diff检查通过。保存五局的完整脚本流程9调用/8工具/一次修订，最大请求输入估算56298；脚本低分仍拒绝。真实模型验证尚待本实现公共CI。

## Coverage real observation and remaining boundary

2026-09-11逐段覆盖已完成公共与真实开发验证：实现11278ba0b121b772002770cf5c4513dcae324abc，Actions34599166770三任务同SHA成功（Python3086 passed/154 skipped/127 subtests，PostgreSQL210）；本地144项/7 subtests。97分漏检稿在新鲜report-b运行中78/needs_revision→一次修订→96/pass，前后均完整覆盖27段，旧视野意识断言已实际改为结果记录并明确不证明意识；同位置补刀修正保留。人工仍needs_revision：稳定性措辞仍被支持，需区分所选样本内一致性与经证据证明的稳定性。独立controls运行10/10完成，5错误检出、5正确通过，漏检0/5、误报0/5，12调用含2次结构化纠正；仅已知开发集，非未见泛化或生产准入。首个report运行1请求在约74秒worker_failed中断，未获终态/用量；不是90秒截止，不能判定输出上限或网络具体根因。全新report-b的3请求52176 tokens及controls的12请求212083 tokens完整返回。本轮共16次Provider预约、已返回计量264259 tokens，中断请求用量未知；累计Provider95。旧记录/人工WorkBench副本不替换，8E仍in_progress，无可信发布/部署/个人Training。唯一下一步：为稳定性表述建立明确正反边界（样本内一致描述、长期稳定断言、含混措辞），离线校准后再验证，禁止靠关键词黑名单或重复抬高评分解决。Workbench四块设计仍后置。

Evidence remains private under `data/runs/inference_development/`:

| Fresh run suffix | Requests | Outcome | Receipt SHA-256 |
|---|---:|---|---|
| 11278ba-coverage-report | 1 | worker_failed, no terminal/usage | bba8fedf1cdec5fe0b33e1d35274a6c836a2cfd52a9dcccd8b2abed74d2dad10 |
| 11278ba-coverage-report-b | 3 | 78 → revision → 96; manual needs_revision | 3569c3970d8777731c775a21f66ac938957b07c81976261da32abd3bf4ec05ae |
| 11278ba-coverage-controls | 12 | 10/10 known controls matched | a93098c46a5c95b21d557a5c409392b425d3b70b125015a96b02f78c22477a12 |

Run IDs have the prefix `inference-dev-`. The new report's manual-review SHA is
3539a83d79e102dd84ccb37d7337afb5230fe49a8d10f000bbe5cfa71b7afa7b;
report SHA is 3b4d530279951c54a79eaf330a0b03d841910ab6dc35b8f48402be285a9f8c6e.
The original report, its 97-point false pass, the manually reviewed Workbench copy,
and this new 96-point automatic result retain separate identities. No publication
was performed. Zero usage in the failed receipt means no returned accounting,
not free usage. The entire ten-case development set was completed this time.

Next acceptance boundary must distinguish: a factual statement that both selected
losses have lower gold/damage than both selected wins; an unsupported inference
that this is a reliable future/long-term property; and ambiguous wording such as
“stable difference” without a stated scope. The first can be supported by the rows,
the second requires evidence not supplied here, and the third needs clearer
wording. Do not reject all appearances of “stable” or invent a universal minimum
sample count. This calibration is a separate remaining semantic issue, not another
coverage omission. Prepare explicit positive/negative/ambiguous cases and unseen
paraphrases before a further bounded real observation. Parent 8E remains open.

Learning closure for this bounded coverage change: code map and control flow are
above; tests prove complete inventory, report binding, persistence and shared
repair limits; real controls demonstrate the observed known-case improvement;
private run receipts and CLI examples support reproduction; the provider failure
and unsupported stability language document operational and semantic limits.
Interview wording: “Converted selective claim auditing into verifiable report
coverage, kept the existing request envelope through lossless compaction, and
validated five reject/five accept controls with real model calls; retained manual
review for a separate stability-scope ambiguity.” No claim of universal accuracy.

## Stability scope calibration (offline, 2026-09-11)

2026-09-11稳定性边界离线校准完成：新增独立golden-stability-calibration-v1十二条人工开发案例，accept/reject/clarify各4条。逐行复算确认所选两场中路输局的经济与伤害各自均低于两场赢局，故样本内方向一致可保留；长期/未来/因果外推需拒绝，未定义范围的稳定或可靠措辞需澄清。原96分稿两处稳定措辞归为范围含混，不认定已证明长期断言。新检查器仅验证来源SHA、数值及案例构成，不给模型语义判分；相关10项测试通过。当前Runtime和冻结1.3.10未改，真实语义修复仍未验证；本次无Provider请求，累计95。唯一下一步为显式新版本接入范围判定和含混修订合同，先做预算/旧合同回归及公共验证，再以新身份执行有界真实观察。8E保持in_progress，Workbench四块设计后置。

The label is about the inserted claim, not approval of a whole report. `clarify`
means editorial scope is unresolved, not that the reported arithmetic is false.
Do not collapse it into factual fabrication. A global small-sample disclaimer does
not define what a local “stable difference” means. Explicit within-sample usage,
negations, and questions are positive controls even when they contain “stable”.
Predictions or enduring-ability claims can be unsupported without that word.

Code map: `data/evaluation/datasets/golden_stability_calibration_v1.json` contains
12 human labels and explanations, with immutable source/report hashes.
`scripts/check_golden_stability_calibration.py` binds the old evidence bytes,
selects MIDDLE win/loss rows, computes pairwise order and means using Decimal,
and verifies three-way case coverage. `tests/test_golden_stability_calibration.py`
checks changed source/duplicate identities/missing ambiguity controls and explicitly
keeps semantic verification false. Run that checker then its tests alongside the
existing golden-quality evidence tests (10 passed). No provider, credential or
publication path is imported by the checker.

Next implementation design: a new explicit contract (retain 1.3.10 unchanged)
should record claim scope as selected_sample, beyond_sample, ambiguous, or
question_or_negation. Ambiguous claims require a matching clarification issue and
revision with explicit cohort/count/observed metric, without fabricated longer
history. Preserve both inference dimensions and complete report coverage. Require
scope data to reach revision and re-evaluation; prevent passing with unresolved
clarification. Do not invent a sample-size threshold or a keyword classifier.
Measure the complete saved-report request envelope before real calls; retain
64000 input, 8192 output, one report revision and existing call ceilings.

After offline implementation and matching public CI, freeze a fresh bounded run
against the 96-point artifact and balanced complete-report controls. Keep human
labels out of model input. Separately report accept retention, unsupported-claim
rejection and ambiguity clarification, including skipped cases. Any paraphrases
created during implementation are development cases, not held-out evidence;
a genuinely withheld evaluation requires independent preparation and isolation.
Neither this arithmetic check nor future structured mocks prove semantic quality.

Learning: this change separates true sample descriptions from extrapolation and
editorial ambiguity. Evidence flows from archived rows to recomputed facts to
human-labeled controls, before evaluator changes. Its limitation is precisely that
it does not grade prose. Interview wording: “Used paired positive, negative and
ambiguous controls to avoid replacing an inference bug with a keyword blacklist.”
The parent learning checkpoint remains in progress.


## Scope contract implementation

2026-09-11范围澄清合同已本地接入：显式Coach1.3.11/Skill0.5.11/Program2.3.11/evaluation1.6.0；逐条scope及逐段scope_ambiguous绑定，含混原句必须有other类澄清issue且不能pass，复用一次结构化纠正与一次报告修订。范围和覆盖经既有audits/coverage保存并传入修订，复评重建清单；冻结1.3.10及旧合同身份不变。保存96分稿27段离线请求估算52544评估/48544修订，均小于64000，8192输出及既有调用墙不变。当前未完成真实语义验证；Provider累计95。唯一下一步为本实现同SHA公共验证后，接续新身份的范围校准真实评估与修订验证，旧对照和工作台人工稿不替换；8E仍in_progress、四块设计后置。

Code map: `golden_inference_scope.py` extends frozen V15 with per-claim scope and
per-block ambiguity. `validate_scope` reuses literal anchors and complete coverage,
then verifies each ambiguity flag against an ambiguous claim in that same block.
A supported arithmetic statement may still require clarification; the extra
validator requires a quote-matched `other` issue and nonpass, without forcing a
false factual finding. Structured correction shares the existing one-call repair.
The grounded adapter sends the same scope policy to revision; persisted audits and
coverage retain the extra fields. New composition/assets/resolver opt in to1.3.11.
No keyword classifier, new dependency, score change or sample threshold is used.

Tests cover unresolved pass, quote/category mismatch, missing fields, hidden block
ambiguity, existing-security terminal refusal, new asset resolution and old
fingerprints. Nine-request replay validates policy delivery and refusal after the
one revision is consumed. Scripted supported labels do not prove prose is correct.
Run `python -m scripts.check_golden_coverage_requests --scope --source-run <saved>
--report <96-point-report>` for the actual saved-shape budget probe. It runs locally
and reports estimates only. The new schema still relies on model semantic labels;
incorrect supported/selected_sample classifications can remain structurally valid.
The real development entry still uses frozen coverage until separately wired for
scope cases; do not treat an old-version run as validation of the new contract.

Learning: ambiguity is a distinct editorial obligation carried through the same
revision flow. An unresolved claim cannot be cleared merely by a high score.
Evidence/control flow: report→indexed blocks→scoped audit→quote-bound issue→
revision→fresh full audit. Interview: “Added scope-aware revision obligations while
preserving old contract fingerprints and request budgets.” Parent gate stays open.


范围合同最终本地验证：90 passed，治理检查和diff检查通过。公共验证待本次提交。


2026-09-11范围真实验证入口已接线：--scope显式绑定1.3.11和十二案校准集；report-only强制96分稿SHA，controls-only最多24次，两批独立身份，原coverage路径不变。三类结果分开统计，只有命中插入原句及对应unsupported/ambiguous问题才算检出；正对照失败停止后续控制，完整报告嵌入标记在I/O前核验。30项聚焦回归通过，无I/O预检显示正确版本/12案/24次上限。唯一下一步为本提交同SHA公共检查后执行已授权的新鲜report-only，再按结果进行controls-only真实观察。当前Provider累计95，真实语义修复仍待验证，8E和Workbench后置边界不变。


公共首检34605503901发现校准来源SHA绑定Windows CRLF，Linux LF误报source evidence changed。校准资产明确utf8_lf_only，仅归一化CRLF，新增双平台一致及数值改动拒绝测试。旧来源文件/运行回执不改；待修复提交公共验证，Provider仍95。


2026-09-14范围合同真实验证结果：公共修复提交1d9504d的Actions34606570608三任务最终success。新版本1.3.11报告复核run inference-dev-1d9504d-scope-report实际1次请求、12345输入/5497输出，原96分稿仍verdict=pass；这确认含混稳定措辞在真实报告中仍被漏放，不能宣称修复完成。独立controls run inference-dev-1d9504d-scope-controls最多24次但第3次模型流ToolError中断，已完成前2条accept控制且均96/pass/matched=true，calls=3、已返回24713输入/12145输出，第三次及后续未知用量/未完成，不能统计三类完整率，也不自动重跑同一身份。第3次未产生终态回执，保存stream私有进度。累计Provider预约至少99（95+1+3）；本轮新增已返回54700 tokens按两回执共54700，具体单次失败用量未知，不将其记为零。下一步：先做失败流归因，再决定是否另立新身份的最小诊断；若继续真实调用，需保留原报告漏检这一失败作为门槛，不能只跑正对照。8E仍in_progress，工作台人工稿不替换，四块设计后置。


2026-09-14流失败诊断加固：旧scope-controls第三案回执只有worker_failed且assembly_code=null，实际progress为provider_error、http11.response_closed.complete、36.656秒、无终态/用量，具体Provider根因仍未知。新增GoldenProcessStream受控SAFE_PROVIDER_FAILURE_CODES，仅在failure.json投影内部固定码，不保存SDK异常、响应正文、密钥或原始Provider文本；26项聚焦回归、治理和diff通过。此次是诊断加固，不改变模型调用预算、重试或旧回执，不重跑已失败身份。下一步先以新SHA公共验证，再决定最小新身份诊断；原报告scope真实漏检仍是质量门。


2026-09-14范围合同v2离线修复：针对1.3.11真实报告把“输局的稳定同位置差距”错误标为selected_sample，新增隔离Coach1.3.12/Skill0.5.12/Program2.3.12/evaluation1.7.0。每条claim必须携带scope_anchor且逐字落在quote；selected_sample的锚点必须是本次/样本/所选/明确场次或n=数等局部范围表达。明确“这四场方向稳定”仍可supported，长期外推仍beyond_sample；不是禁止关键词。新增48项相关回归，无Provider调用；scope-v2预检绑定12案/24次和新资产解析通过。旧1.3.11及其真实失败证据冻结不改。唯一下一步为新提交同SHA公共CI，之后重新执行scope-v2报告复核；不自动重跑controls旧身份。

2026-09-14范围合同v2输出预算收口：首个真实scope-v2报告身份`inference-dev-6e0cde2-scope-v2-report`未拿到终态JSON，原因是Provider流在`finish_reason=length`、`output_tokens=8192`、`input_tokens=12507`、`content_chars=0`时结束，未进入锚点校验；该失败按`incomplete_stream/assembly_rejected`保留，不复用身份、不记作语义通过。为给终态结构化JSON留出空间，v2提示加入输出预算：锚点最多20字符、每条解释最多40字符、证据键只列必要项且不输出额外说明；并已重新生成v2资产组件指纹。32项范围/覆盖/诊断回归与治理检查通过，尚未产生新Provider调用。下一步是提交并完成同SHA公共CI，然后以新run-id重做report-only；controls保持暂停，8E与Workbench四块设计边界不变。

2026-09-14范围合同v2第二次真实报告观察：新身份`inference-dev-d59c596-scope-v2-report-c`已通过同SHA公共CI并完成1次Provider预留；约29.7秒后流以`http11.receive_response_body.failed`结束，`content_chars=0`、`finish_reason/input_tokens/output_tokens`均为空，受控诊断为`worker_failed/provider_code=null`，receipt中的token计数为0。该次没有进入结构化解析或锚点语义判断，不能当作通过或失败语义样本；不复用身份。此前`inference-dev-6e0cde2-scope-v2-report`是另一种`finish_reason=length`/8192输出耗尽，二者分别保留。当前不继续controls；需先决定Provider流稳定性是否值得第三个新身份观察，8E和Workbench边界不变。

2026-09-14 Provider流诊断分类修复：离线审查确认`http11.receive_response_body.failed`只是HTTP body迭代异常的观测事件，不能单独当作根因；最新失败流在约29.7秒内持续收到reasoning后断开，非本地90秒deadline。现将迭代期`httpx.ReadError/RemoteProtocolError/ConnectError/WriteError`映射为安全`connection_failed`，四类httpx timeout映射为`timeout`，并把`connection_failed/timeout/unexpected_sdk_error`加入body-free诊断白名单；不改重试、墙钟、close或assembly语义。新增HTTP迭代异常回归，相关69项测试/27 subtests、治理和差异检查通过。尚未新增Provider调用；当时提出的低思考观察已撤回；HTTP分类修复保留用于高档故障定位。

2026-09-14 Provider流诊断分类修复公共闭环：提交`578d1fa`对应Actions run `34798046857`，pytest、postgres-migrations、packaging-smoke三项均`completed/success`；新增httpx迭代异常分类回归已随公共pytest通过。本批没有新增Provider调用。当前scope-v2两次真实报告身份仍分别是输出耗尽与body迭代断流，均未得到语义终态；后续low提案已由本轮审计撤回，继续高档故障定位。

【已撤回的历史实现；不再作为下一步】2026-09-14 low+4096同步诊断分支离线接入：新增`--candidate-low-4096`，仅允许scope-v2/report-only；复用1.3.12语义contract/schema，但真实Provider身份单独记录`glm-5.3-flash-candidate-low-4096`、request policy 1.0.0与`transport_mode=sync`，直接使用既有候选low profile和`CandidateEvaluationBudgetedProvider`，不复用高档stream bridge，不改scope-v2资产指纹。预算为最多4次调用、4096输出、72,000总token，响应journal body-free。38项聚焦回归、预检、治理和差异检查通过；本批尚未调用Provider。若公共CI通过，下一步才执行一个全新低档report-only身份；结果只用于区分同步低档语义可用性与高档stream故障，不构成stream或生产证据。

2026-09-14审计纠正（取代此前模型策略澄清及low下一步）：Luna指Codex执行工作时的协作模型，与RIFTCOACH的GLM模型策略无关；此前将其写成“用户确认”是助手误记，撤销该归因和等待模型策略裁决的下一步。撤回00fa4ad新增的scope-v2 low诊断入口，恢复高档响应正文私有留档和I/O前预约计数；既有独立low研究资产不删除。保留scope-v2与HTTP异常分类修复，但两次真实scope-v2均未得到有效评估，断流根因及原报告语义漏检仍未解决。修复提交1eb8c440d24a8905f0e61592ff22a6628b4fd40a已由Actions34803738781同SHA三项success验证，本地相邻255项及补充中文锚点聚焦14项通过。当前下一步为继续高档故障定位及原报告真实验证；不因Luna调整GLM档位。Stage 8E仍in_progress，Workbench四块设计后置。


## 2026-09-14 额度耗尽检查点之后的修复审计

范围：从1d9504d真实scope报告/controls及71c29dd结果记录，检查到be078a4。

- 错误决策：be078a4把助手对Luna的误解写成用户确认，传播到11个文件；现逐处纠正，并撤销以low为下一步的指针。
- 实现回归：00fa4ad同时改变高档response journal且low失败主计数不同步。撤回该入口，恢复原高档I/O前预约及content/finish_reason私有留档。Counted移到模块级仅为直接验证生产调用的同一包装器；不更改预算、重试、模型或传输。
- low报告入口的72000总预算与单案24000约束混搭随入口撤回消除；9月3日起的独立low候选研究不是本次误改，保留。
- 新测试真实调用同一Counted类，用假Provider证明：失败前已有预约文件、失败计数保留、到限不再调用、成功正文逐字保留。新增中文scope正例及真实漏检短语反例，验证锚点校验；不能据此认定模型语义已通过。
- 本地相邻回归255 passed；新增6条中文锚点案例后聚焦14 passed（包含已跑案例，不重复累加）。治理、编译、diff检查通过。原5次公共CI已独立核对SHA与三job成功；本修复需自己的公共CI。
- 原证据不覆盖：1d9504d报告1次/17842 tokens，controls3次预约但仅2案完成/36858已返回tokens，合计54700。scope-v2两次各1次预约；首个progress有12507+8192=20699 tokens，父receipt为0不代表实际零费用；第二次未返回计量，未知。以此前95为基线，累计预约至少101，不把未知计量补零。
- 保留的有效改动：scope-v2显式合同/独立资产、输出简化提示、httpx安全异常分类。后者改善可诊断性而非修复网络；输出简化尚未证实能解决reasoning耗尽。
- 未解决的产品问题：高档完整响应稳定性、原报告含混措辞的真实检出与修订、完整12案验证。需在公共CI之后沿用高档和新运行身份继续验证；本次代码纠错不算这些问题已通过。
- 工作台人工稿、默认配置、历史回执、主工作树用户修改均未改动。

公共收口：修复提交`1eb8c440d24a8905f0e61592ff22a6628b4fd40a`对应[Actions34803738781](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/34803738781)，pytest、postgres-migrations、packaging-smoke均success。零网络scope-v2/report-only预检通过，合同SHA和8192输出上限保持不变。本轮没有真实Provider请求；这不是原报告语义质量收口。

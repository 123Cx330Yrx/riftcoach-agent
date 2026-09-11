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

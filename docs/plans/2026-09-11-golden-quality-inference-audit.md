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

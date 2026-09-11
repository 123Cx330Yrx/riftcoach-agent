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

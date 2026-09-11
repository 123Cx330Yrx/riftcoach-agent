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

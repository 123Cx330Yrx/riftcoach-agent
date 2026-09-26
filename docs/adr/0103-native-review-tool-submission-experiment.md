# 0103: Use the existing tool channel for a bounded review submission experiment

Date: 2026-09-22. Status: development experiment; not product adoption.

## Context

Business v1 correctly revised the explicit universal-metrics control, then emitted
a pass JSON followed by Markdown. Full semantic reassessment introduced a scope
false positive. V2 stops that tail without recovery; it does not make the model
produce a usable result. Existing JSON mode was enabled. Published GLM capability
docs expose Function Calling with auto, not required or strict JSON-schema mode.

## Decision and data flow

Full report and sources → unchanged business judgment → one submit_report_review
tool call → existing NativeIssuesReview validator → existing revision/recheck.
Reuse the same schema in tool parameters, remove its redundant text notation,
and replace only the delivery instruction. Revision stays Markdown. No external
tool is executed and no tool-result follow-up call is sent. Use AUTO honestly:
the model may decline the tool, in which case the experiment fails.

The dedicated development subclass checks issued-input identity and receipt,
then requires exactly one matching tool call, tool_calls finish and no substantive
content. Record the original response before rejection. The validator's JSON is
explicitly labelled a tool-arguments projection, not original content. No truncation,
synthetic stop response, discarded findings, extra schema or second judge.

Keep the small call/identity boundary local until evidence warrants adoption;
avoid changing historical request reconstruction or dormant product fingerprints
for an unqualified experiment. Shared budget and receipt classes remain reused.

## Alternatives and limits

Keep text JSON: already observed mixed output. Strip tail: may lose findings or
contradictions. Add strict/required: no published support. Add another model repair:
changes business judgment and consumes the same scarce total call budget.
Tool submission may improve delivery framing but does not prove semantic quality.
It changes framing and schema delivery together, so results cannot isolate either.

## Cost and failure decisions

All generation/tool/review calls share 5 calls, 401920 tokens and 900 seconds;
one revision, 32768 output/300 seconds per request, SDK retries 0, Flash/high.
Two generation calls plus review/edit/recheck fit five with no recovery. Recovery
can consume that capacity and must fail closed if no room remains; never add a
second review budget. Worst-case latency is not guaranteed to fit 900 seconds.

Test positive scope, universal false claim, and mixed true/false findings in that
order using existing frozen claim-scope cases 1, 4, 3; labels stay analyst-side.
Run only after offline receiver/SDK/shared-budget checks and exact clean HEAD CI.
Inspect every case before the next. Stop the batch at protocol/execution/semantic
failure. A channel failure rejects channel feasibility for this batch; a legal
tool result with the original false positive refutes channel change as sufficient
semantic repair. No same-batch prompt tweaks or recovery by discarding content.
Success permits further same-version coverage, not product admission.

Evidence: golden_native_business_result_d41c0bd.json; official cached documents
under native-review-d41c0bd-business-claim-4/explicit_universal_metrics/provider-docs.

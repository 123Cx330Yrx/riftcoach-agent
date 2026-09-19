# Review outcomes without a second generated fact report

The user needs a correct Coach report, meaningful detected problems, automatic
revision/recheck and attributable evidence. A mandatory narrative for every
accepted paragraph is an implementation choice, not an accepted business rule.

Two actual native-v2 failures discriminate this issue from transport failure:

- At 4f2307b, three negative controls completed revision/recheck. A fourth
  heading problem was correctly detected and fixed, but the final review
  invented a wrong auxiliary loss count and attached the wrong title explanation
  to block2. Dropping its non-JSON tail would pass the structural checker while
  retaining those errors. Its original failed receipt stays failed.
- At 0140531, the recovery entry passed all tests and public CI. A new positive
  correctly accepted the report and its OP.GG numbers but falsely attributed
  Syndra/Vex to the Locke source key in an accepted paragraph's explanation.
  No heading negative was then run. The raw response and rejection remain in
  `golden_native_review_result_0140531.json`. One call, 17789 known tokens;
  cumulative Provider requests at least221. The recovery path was not used.

The envelope fix is useful but does not repair semantic restatement. A larger
per-paragraph source graph or another field-specific hint would recreate the
same non-product obligation. Conversely, accepting false explanations because
the verdict is right would misrepresent the observed quality.

## Chosen contract

Use the native score/verdict/issues/summary/passed-checks result. Actual problems
have a block number, category/severity, explanation, correction and source IDs.
The host binds the full original paragraph and real source values. Positive
paragraphs do not require another generated narrative or provenance graph.
The summary describes the review outcome; passed checks name dimensions without
restating the report. Titles, compound tails, numerical scope, sources, identity,
causality, knowledge, recommendations and injection remain in the full input and
review instructions. The complete-context acceptance standard is unchanged.

Issue recall is measured by controlled full reports and later holdout; neither
a generated block checklist nor an empty list mechanically proves completeness.
Source existence also does not prove relevance. Both remain explicit quality
risks. We do not claim output length alone guarantees better judgments.

Reuse the existing state machine, receipt transport, deterministic calculations,
source catalog and all budgets. A valid review needs one call, revision/recheck
normally three, and one full correction per evaluation allows at most five.
Preserve raw prior opinions, their identified problems, suffixes and explicit
dispositions. Final parsing, knowledge checks and same-source revision binding
stay strict. The verbose-v2 live entry is now offline_only, alongside the eight
older retired entries. Their code/tests and raw historical outcomes are retained.

## Evidence and next actions

210 relevant tests passed. `golden_native_issues_offline_v1.json` binds the
unchanged five controls and original source hashes. Inputs45574–45650, an actual
old failed response can enter full correction at55930. The scripted five-call
reservation is387042 within401920; actual-use plus next reservation remains the
runtime rule, with no promise that arbitrary long responses always complete.
No GLM/high, token, call, deadline, estimator or retry setting changes.

1. Exact-SHA public CI, then the unchanged positive. Read the entire returned
   outcome, sources and actual problems before allowing the next control.
2. Test future extrapolation, reader identity, official date and heading ability
   one at a time through revision/recheck. A failure ends the batch for diagnosis.
   Do not turn scripted results or historical v2 successes into v3 quality proof.
3. Qualified results proceed to existing Runtime/atomic publication/Evidence/API/
   Workbench composition, with one generation-plus-review budget and isolated
   per-run transport/workflow state. The present stream adapter has instance-level
   counters/failure state; it cannot become a shared multi-run singleton unchanged.
   The typed compiler must carry observed-subject identity through generation and
   evaluation. No default production registration or manual report replacement.
4. Independent holdout and broader8E remain pending. Frontend aesthetics/rebuild,
   portraits, Coach/Review/Training/Evidence links, personal training and all62
   tracked themes continue under the Astra restart plan, with no scope reduction.

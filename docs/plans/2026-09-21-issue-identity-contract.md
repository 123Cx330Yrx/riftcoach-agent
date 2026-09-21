# Issue meaning, independent editing and two-state review

## Decision and correction of the initial prototype

The initial uncommitted character-anchor wrapper is withdrawn. It called the
whole paragraph a precise claim, duplicated that paragraph as context, bypassed
parts of native validation and was not wired into an actual editing request.
Its four passing tests did not prove the candidate usable. Those wrappers and
the misleading fixture were removed before commit; no Provider call used them.

The replacement information audit preserves the original native validation and
serializes three diagnostic views with the complete original report/sources.
The new counterexample puts two allegations in one paragraph, with identical
explanations but different scope expressed in suggested_correction. One attacks
the genuinely wrong combined-five-game comparison; the other attacks the correct
four-middle-game comparison. Swapping them reverses the required decisions.
Both full reviews validate, yet deleting suggestions produces identical readable
issue rows. Opaque hashes differ but cannot restore their meaning. Thus neither
locator-only nor suggestion deletion is adopted as a general contract. Retaining
complete old opinions preserves text, but the real full-opinion response already
showed that this alone does not fix semantic judgment.

Evidence: golden_native_issue_view_audit_offline_v2.json. This is an analyst
information-loss witness, not a new observed model failure. The prior real pair
and all real failed responses remain unchanged.

## Selected offline alternative

Use the existing single revision slot to independently edit the entire report
against all sources, without sending any prior opinion, hash or expected label.
The subsequent final reviewer receives the actual new report and the complete
original report and accepted original review, including suggestions. It must
separately output:

- each original issue's validity on the original report: confirmed,
  false_positive or unresolved;
- its repair status in the actual new report: corrected, persists,
  not_required or unresolved;
- a complete native review of the new report, including new errors.

A corrected true error is not an old false positive. A clearer new sentence
cannot validate an old allegation. A new-report pass cannot stand in for original
issue adjudication. The final reviewer sees prior opinions and may still anchor;
only the editor input is opinion-blind. No claim of statistical independence or
semantic repair is made from this architecture or its tests.

Host guards bind both reports and the original raw review; every original ID is
accounted for, including same-block/same-claim cases. Old block IDs refer only to
the original index. Current review IDs refer only to the revised index. Source
facts, knowledge, user request and provenance are checked unchanged. Source-root
maps and computed arrays are factored only after exact equality apart from their
named report identity field; they expand to their full original forms. No source
value, scope or row is removed. Chosen source IDs still require semantic review.

Native single-revision/order/recovery and security checks remain authoritative.
Malformed final responses with identifiable issues outside the review subtree
stop before recovery, so those findings cannot disappear during extraction.
Legitimate nested findings still require complete native recovery mappings.
Unresolved/persisting old problems cannot coexist with a final pass. Structurally
valid but wrong declarations and unnecessary edits remain semantic failures;
the old real bad edit is retained as such a counterexample.

## Completed offline verification

Implementation: scripts/blind_edit_settlement.py. Evidence builder:
scripts/check_blind_edit_settlement.py. Test-only product injection uses the
actual compiler, local RAG and Runtime; no product factory or manifest changes.

- Normal report-only three-call path reserves 237890 tokens.
- Report-only five-call recovery path reserves 409820, above 401920. Low synthetic
  usage can finish it; saturated usage is correctly rejected before call five.
  This limitation is recorded, not removed by changing budget rules.
- Actual product generation twice, first review, blind edit and final settlement
  takes five calls and 374902 saturated synthetic tokens, within 401920.
- Extra initial reassessment makes settlement call six; it is rejected and no
  report is published. The test's normal publication is scripted evidence only.
- Two local defects were found and fixed before live use: misplaced final issues
  could escape recovery mapping; blind editing initially carried evaluate phase
  metadata, which failed real product observation. Tests now cover both.

69 focused tests passed. Independent review repeated23 settlement/product tests
and eight projection tests, and confirmed the repairs. None are live quality
proof. New artifacts: golden_blind_edit_settlement_offline_v1.json and
 golden_blind_edit_product_budget_offline_v1.json.

The runner also preserves a fresh complete exchange when the shared sender
rejects it after response receipt (for example, elapsed deadline); known usage
is not relabeled unknown. Interrupts persist an interrupted result and re-raise.
Tests cover both fresh and stale prior exchanges on the second call.

## One bounded diagnostic after independent review and exact-SHA CI

The user requested continued sustained work under existing authorization. The
interim instruction to remain offline applied while the contract was unresolved;
the rejected projection will never be run. The new isolated diagnostic proceeds
only after independent execution review and clean exact-SHA public checks.

scripts/run_blind_edit_diagnostic.py freezes the original real mixed report and
review in golden_blind_edit_diagnostic_plan_v1.json. It does not rerun or qualify
the failed initial reviewer. First call edits the full original without opinions;
second call is built from that actual draft and the frozen original/source data.
No analyst correction, desired label or first-call rationale is inserted.

Hard two calls share401920tokens/900seconds; GLM-5.3-flash/high, per-call32768
output/63936input/300seconds, SDK retries0 remain. Original source and both actual
requests/public outputs are preserved with receipt identities. Truncation,
malformed output, changed source or exceeded budget stops without retry or
recovery. Manual full-output/source/diff review is mandatory after execution;
protocol success alone is not acceptance. No second paid batch after a patch in
this continuation. Native/editor/product live gates remain offline; the new
runner is diagnostic-only and closes after this batch.

If it succeeds, it establishes this report's independent-edit/two-state outcome
only. Same-version controls, original-review precision, historical failures and
complete product qualification remain. If it fails, preserve the exact semantic
or execution failure and reconsider the route before another experiment.

Stage8E stays in progress. Source-bound product Evidence, actual Worker/DB/API/
Workbench consumption, independent evaluation/learning, frontend aesthetics or
rebuild, portraits, four-part Coach/Review/Training/Evidence linkage and personal
Training remain tracked in the Astra restart plan and all62themes.

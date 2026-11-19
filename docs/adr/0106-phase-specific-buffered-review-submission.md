# 0106: Phase-specific review contract with buffered tool arguments

Date: 2026-09-22. Status: bounded development after exact CI; not product adoption.

## Evidence and decision

ADR0105 completed tool streams contained duplicate JSON members, including an
`issues` list overwritten by `[]`. Strict rejection is necessary. Removing only
the duplicate text schema did not fix this. Omitting vendor `tool_stream` while
retaining SSE produced two complete, strictly decoded submissions: the erroneous
full report was 85/needs_revision with the genuine block14 attribution finding;
the corrected report was 95/pass with only optional suggestions. This is one
observation per condition, not proof of stable accuracy or deterministic cause.

The positive submission failed the old contract solely for omitting
`issue_resolutions`, a required empty list when no prior review exists. Evidence:
`data/evaluation/results/golden_block_buffered_pair_result_eadb930.json`.
That failure remains failed; its raw receipt and full output are preserved.

Use distinct contracts for independent review and reassessment. The independent
tool requires exactly reviews/score/verdict. Reassessment still requires all four
fields and an explicit mapping for every prior issue. The independent contract
also applies to an independent review of the revised report. No existing issue
is silently dropped. There is one authoritative tool schema, no text duplicate.

The typed internal adapter supplies a known-empty resolution list to reuse the
old validator/editor only after strict validation of the new independent schema.
The journal preserves the original three-field output, its hash and an explicit
`validator_projection` record. It never claims the model supplied that list.
Extra old fields in an independent submission are rejected, not discarded.

For this development variant, explicitly buffer tool arguments and record the
transport mode and process-local route in the run plan. Keep SSE and usage tail,
Flash/high, 32768 output/300 seconds per call, retries0, shared 5 calls/401920
tokens/900 seconds and one revision. Product defaults and historical request
builders stay unchanged. No new dependency, reviewer Agent or extra model call.

## Why this replaces complexity

Do not accept duplicate keys, silently fill old missing fields, or add retries
asking the model to repeat an inapplicable field. The new phase-specific schema
expresses the actual available state. Reassessment obligations remain intact.
Do not revise report wording solely to satisfy optional suggestions.

## Verification and failure decisions

Offline checks cover source preservation, strict fields and duplicate rejection,
full paragraph inventory, source references, score/verdict agreement, mandatory
reassessment mappings, advisory exclusion from editing, raw-output provenance,
explicit recovery/edit/recheck and the actual scripted product five-call budget.
Replay of the old positive is compatibility evidence under a new contract only.

After exact-HEAD public CI, test the original attribution report through actual
review/edit/recheck, then the corrected full report, mixed error, universal error
and original positive, followed by the remaining distinct original15 controls.
Inspect every finding and actual edit. Stop on a genuine miss/false positive,
incorrect edit or terminal protocol failure; preserve usage and locate the first
deviation. No cross-version pass aggregation or product qualification from this
pair. Existing product binding/integration/independent-evaluation gates remain.

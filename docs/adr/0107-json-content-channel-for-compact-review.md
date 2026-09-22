# 0107: Isolate the output channel for compact phase-specific review

Date: 2026-09-22. Status: bounded development after exact CI, not product adoption.

## Failure and what it actually establishes

The ADR0106 full workflow on da06b5a / CI35714036543 failed its first call.
At161.828 seconds it had tool_calls, usage, normal exhaustion and owned close.
One entire2299-character argument delta repeated block and issues in reviews[13]:
block14 contained the true attribution finding, then block15 and empty issues
occurred in the same object. Permissive decoding would erase the real finding.
Offline replay of that single incoming delta reproduces tool_call_arguments.
Advisories4/6 also omit source_ids. No result is accepted or automatically repaired.

Evidence: `data/evaluation/results/golden_buffered_phase_failure_da06b5a.json`.
Observed usage11640+5845=17485, unknown0. The original runner receipt reports
unknown1 because its accounting had not received the earlier diagnostic-only
fix; retain it and store the correction separately. Apply observed usage accounting
to the actual integrated runner, preserving failure and delivered-response count0.

Buffering is not a sufficient fix. It also rules out local incremental argument
concatenation as necessary for this instance. It does not identify whether the
model or server tool-output transformation produced the malformed object.

## Chosen bounded channel experiment

Keep ADR0106's exact paragraph inventory, phase-specific schema, business policy,
source scope, optional-advisory partition and original15 controls. Submit review
as JSON content using the already implemented response_format=json_object path,
with no submission tool. Move the identical schema notation into the request
once, because the Provider supports JSON mode but not constrained JSON Schema.
Change only the delivery sentence; keep the actual review task and source bytes.
Editing still returns Markdown, and all calls share the existing budget.

This bypasses the server's tool-argument representation, not the model's need to
produce correct JSON. Historical text experiments had prose-tail and semantic
failures; do not claim JSON mode was previously absent or guarantees correctness.
This comparison differs in output channel from the *current compact* contract,
not just a retry of the older verbose/flat reviewer. Valid completion gives
practical evidence for this path, not proof of Provider-side causation.

No extra cleanup LLM, syntax-repair parser, last-key-wins decoding, deletion of
findings, model downgrade or budget increase. Terminal prose tails and duplicate
members remain rejected without a hidden fresh judgment. Valid JSON with invalid
fields can only use the existing explicit bounded reassessment, with prior issue
mappings; after two generation calls it may leave insufficient budget to revise
and recheck, which remains a rejection rather than an extended run.

## Evidence and decision branches

Offline: compare source/policy/schema identity, inspect actual SDK JSON-mode
payload and high settings, preserve raw-content journals, reject historical tail
and duplicate failures, check reassessment, actual product five-call budget and
complete-but-rejected usage accounting. No local ignored source files in tests.

After exact-HEAD three-job CI, one original attribution report through the full
review/edit/recheck runner. If valid, inspect all findings and the actual report
diff before continuing the corrected control and remaining existing controls.
If duplicated/malformed JSON persists, output-channel switching is not a
sufficient fix and this branch stops; do not cycle another transport setting.
If valid but semantically wrong, preserve that distinct failure and diagnose the
claim/source relation; protocol success cannot approve the reviewer.

ADR0106's tool live gate closes. The actual product entry remains closed and its
old qualification binding still needs replacement before any later adoption.

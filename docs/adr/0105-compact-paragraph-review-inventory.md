# 0105: Compact paragraph results for complete-report coverage

Date: 2026-09-22. Status: development experiment; not product adoption.

## Evidence and problem

ADR0104's whole-report reviewer missed the original compound attribution error:
93/pass with two unrelated advisories, despite complete sources and existing
role-contrast arithmetic. After narrowing only the judgment task to paragraph
14, the same model identified the real damage-attribution error (80/revise) and
accepted the unchanged corrected control (95/pass). Both diagnostic calls were
valid, with no repair, 26738 total tokens and no unknown usage. Full evidence is
`data/evaluation/results/golden_partitioned_focus_result_cb69f82.json`.

This supports trying an explicit coverage mechanism. It does not prove a causal
attention mechanism or reliable focused judgment: one call per condition and
host-selected focus cannot qualify autonomous review. Sources were not absent;
adding the same arithmetic or attribution rule again has no discriminating value.

## Experiment

Replace flat, freely selected issues/advisories with `reviews`, one entry per
original paragraph in order. Each contains `block`, `issues` and `advisories`.
Empty arrays are sufficient for a clear paragraph. Keep score/verdict and explicit
prior-issue resolutions. Nested findings use the same severity, category, sources,
explanation and correction. Host maps them to existing blockers/advisories;
original tool arguments remain in the journal. Revision consumes blockers only.

This replaces the flat output structure, not an additional reviewing Agent or
call. Unlike the historical verbose paragraph schema it has no navigation/content
classification, explanation for every correct paragraph, repeated positive facts,
summary or passed-check narrative. Full sources, model/high setting, five-call
shared product budget, single revision and exact-CI gate remain unchanged.

The host verifies the paragraph inventory and the existing source/issue contract;
it cannot prove that all clauses were semantically checked. A valid empty entry
may still be a miss. Missing/duplicated/reordered paragraphs fail validation;
existing bounded reassessment keeps original evidence and still consumes budget.
Total issues/advisories retain the existing 512 limits. No case-specific wording,
metric exception, location or expected label is inserted in the product policy.

## Alternatives and decision criteria

- Repeat the full reviewer unchanged: the miss would not distinguish explanations.
- Focus only on manually suspected sentences: useful diagnostic, not autonomous coverage.
- Restore verbose paragraph explanations: repeats prior output/semantic burden.
- Use a second reviewer or one call per paragraph: changes the five-call Agent budget.
- Deterministic keyword rejection: cannot respect correct negation, conditions or scope.

Offline checks cover complete inventory, source identity, non-blocking suggestions,
explicit recovery mappings, revision/recheck and the real product compiler/runtime
within five calls (scripted replies, not model proof). Live tests begin with the
missed attribution negative, its correct control, the real combined-population
error, the universal-metrics error and the original observed positive. Inspect all
findings and actual edits, then cover the remaining distinct existing controls.
Any semantic miss/false positive or terminal protocol failure stops this batch;
do not keep adding coverage fields after an uninformative failure. Prior versions'
passes do not qualify this changed request, and product registration stays closed.

# Metric-specific attribution review

The ac2725c product report conflated CS and damage: its review returned 97/pass
even though removing support changed the damage win/loss gap only from 695.4183
to 669.235. Both source groups were already present. Transport completed; the
external-source binding defect was independent. The observed cause is an
unsupported compound inference accepted by the reviewer, not an established
claim about the model's hidden reasoning.

## Decision

Keep the native issue-list workflow and wire 3.1.0. Add deterministic role
contrasts to its existing computed evidence source. For every supplied role and
metric, show the selected win-minus-loss mean, role win-minus-loss mean, and
their difference, calculated from unrounded source values. Preserve member
references, completeness, missing metrics and single-outcome nulls. These are
descriptive regroupings, never causal contributions or counterfactual effects.

The reviewer checks each metric in a compound inference separately and tests
the direction and magnitude of claimed composition effects. Valid sample
explanations, negations and conditional hypotheses remain allowed. No numeric
threshold or ShowMaker-specific answer is encoded. The host does not interpret
natural-language claims or auto-approve them.

Rejected alternatives: a phrase-only warning supplies no discriminating
arithmetic; rejecting every attribution would falsely block supported sample
descriptions; forcing a new claim graph or a second mandatory review repeats
earlier output/budget complexity. This change adds data to the existing review,
revision and recheck without extra mandatory calls or new response fields.

Native policy becomes v3.2; Coach 1.4.2 / Skill 0.6.0 / Program 3.0.2 retain
wire 3.1.0. Legacy computed-source callers default to their existing data shape.
All model settings, source rules, whole-context acceptance and shared budgets
remain unchanged. The product runner stays offline pending quality evidence.

## Evidence and execution

1. Check contrast arithmetic against raw values; test reversed/zero gaps,
   missing metrics, single outcomes, capped rows and input identity. Confirm
   the model and source resolver see the same hashed contrast values.
2. Preserve the five prior controls and the original attribution pair byte for
   byte. The pair's shorter observed-user request makes it a development
   control, not an exact replay of the product request. Labels and independently
   calculated expected answers never enter the model input.
3. Exercise original full-report regressions, normal revision/recheck and both
   allowed format-reassessment calls offline. Measure all request reservations
   and retain the actual-usage budget rule. Run relevant tests and same-SHA
   public pytest/Postgres/packaging checks before any paid request.
4. Run the attribution correct report first; inspect its complete judgment.
   Then the wrong report must be located, actually revised and rechecked, with
   every explanation/source and all revised text inspected. Recheck the prior
   five controls on this implementation. Any failed case ends the paid batch;
   preserve it and diagnose before considering another candidate.
5. Only qualified semantics permit a new complete product observation with
   source binding and saved-result readback. Task transaction/API/Workbench,
   independent evaluation and learning coverage remain required. This control
   suite is neither a holdout accuracy estimate nor Stage8E completion.

All downstream frontend aesthetics/portraits, four-part Workbench and personal
Training requirements remain in the Astra restart plan and 62-theme ledger.

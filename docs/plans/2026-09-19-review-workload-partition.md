# Whole-review workload decision after the 300-second deadline

Status: whole-method offline qualification completed; bounded development only
after same-implementation public CI. No production entry or semantic approval.
Current product checkpoint remains Stage8E in progress. Existing model/high,
32768 output/300 seconds per call, five calls/one revision/401920 tokens/900
seconds per report, retry0 and63936 input admission remain unchanged.

## Observed result and limits of the diagnosis

Implementation36b41b5 passed Actions35370480008 (all three public jobs). Its
frozen positive made two actual Provider requests. The first completed in
54.453s, with2856 input +4591 output =7447 known tokens,25 readings, no first
schema diagnostics and all19 body blocks mentioned. Its full raw output is
preserved, including its formatting suffix. The next request was admitted at
59364 estimated input, so this run did not fail at first-reference validation
or input-budget admission.

The second request reached300 seconds without a completed result. First event
was6.891s; visible text began264.579s. The last observed event was299.547s,
maximum inter-event gap484ms. Counters recorded65250 reasoning characters and
11486 visible characters. These are character counters, not token usage or a
valid result. No complete second response/usage arrived; that request's usage
is unknown. This does not establish an output-limit finish or a network stall.
Negative control, revision and recheck did not run. Final semantic correction
remains unverified. The entry is now held before inputs/CI/credentials/Provider.

Evidence: `data/evaluation/results/golden_provisional_reading_result_36b41b5.json`
and `scripts/audit_golden_provisional_reading_result.py`. All historical file
hashes are preserved. Cumulative Provider requests are at least205.

The mechanism to investigate is concentration of work in the final call:
meaning/scope, source addressing, all computations, first-reading correction,
complete representation and global adjudication. Event counters do not reveal
why the Provider spent that time internally. Workload partition is a hypothesis
to test, not an already-proven latency fix. Merely increasing a timeout, removing
explanations, lowering reasoning or changing labels is not the selected action.

## Alternative and acceptance criteria

Compare the current report-reading→whole-review path with two source-aware
review batches using the same full report and original sources. The host owns
the partition; it cannot depend on a model omitting difficult paragraphs.
Both batches can reference cross-paragraph context. Batch one is provisional
and has no global score. Batch two reviews its assigned content and explicitly
adjudicates the whole report after receiving all first judgments and issues.
Host merging cannot invent a score, average partial scores, silently discard
issues or treat mere coverage as correct interpretation.

The second response must not simply repeat the whole giant first-to-final
task under a new name. Measure a packet with only its own judgments, explicit
changes to the first packet and global decision; unchanged first values remain
intact. If this creates an uncorrectable first-schema gate, mismatched capacities
or another input overflow, reject it before live execution. Any replacement
must preserve complete original character coverage, all heading obligations,
every prior issue's disposition, and the original strict merged TypedReview.

Use both frozen whole reports and counterexamples for lost tails, unknown blocks,
duplicate coverage, incorrect first scope/identity, conflicting judgments,
misclassified headings and dropped issues. Whole-context acceptance remains:
context can establish sample scope without a special definition of “stable”;
genuine unsupported future extrapolation still blocks.

Measure actual schema-bearing requests and the full2+1+2 path. Transmit all
sources and explanations losslessly; compression must roundtrip exactly.
Repeated full-source inputs can increase the five-call reservation total above
401920. That is a risk, not a new admission rule: actual usage plus the next
reservation remains authoritative. Do not claim a900s or arbitrary-output
guarantee from fixtures. Host arithmetic menus may list all available cohorts
and operations, but cannot preselect the intended sample or be treated as
semantic proof. Transferring deterministic work to host requires explicit
representation and equivalence evidence, not silently filling model omissions.

No paid retry is authorized by a successful synthetic shape alone. A selected
whole-method replacement needs contract tests, documented limits and exact-SHA
public checks before another bounded real case under existing user authority.

## First offline comparison result

`scripts/check_golden_partition_feasibility.py` reproduces the full positive and
negative synthetic fixtures through strict final validation. Original two-batch
inputs are59700/71830 and59772/71746. Lossless tables reduce them to52686/63968
and52756/63936. Explicit host expansion of model-selected full-cohort operands
reduces them to52494/63000 and52566/63038. However, supplying a complete computed
comparison catalog raises second requests to65430/65470; the first-claim
arithmetic ledger variants reach65114/65126. A malformed, duplicated first claim
also reaches65348 in the table variant. Therefore this prototype is **not an
admitted replacement**. The version which merely moves member enumeration does
not substantiate reduced arithmetic work, and its synthetic reachability must
not be presented as a latency fix.

Whole-block correction, original issue disposition and final whole-body checks
are reusable findings. Five-step operand-only inputs are52566/63038/58430/52494/
63000; their full-output reservation total453368 is a risk, not an automatic
admission failure. No actual model latency or token usage was measured.

## Selected method and qualification

The new `golden_partition_review.py` replaces the layered protocol with
`golden_partition_policy.py`. Its requirements match actual batch fields: first
has no global decision, second alone provides it, and host owns report identity.
The protocol retains the accepted whole-context, source-use, position/intent,
identity and security obligations; no fixed player name or frozen answer is
inserted. The earlier prototype's absent-field and conflicting full-report
output instructions are removed.

`golden_computed_evidence.py` supplies **all** available cohorts and supported
metrics, with complete member identity, win/loss means and pairwise directions,
whole-group means/medians and missing/incomplete values. It never selects a
claim's intended sample. The model selects cohort/metric/operation and must
explain the relation to the original text. Host expands full-cohort members and
the uniquely determined source kind for a selected source key; it does not
supply missing model evidence citations, source paths, interpretations or scores.
The complete native TypedReview and its validators remain the final contract.

Host assigns the first third of body blocks to the first output, with both
requests retaining the full report and all original sources. The unequal split
reserves second-input space for the first output and its corrections. Half and
two-fifths splits were measured; they left insufficient space for the combined
malformed-reference/duplicate/false-issue witness. This does not reduce total
review obligations or make the second batch independent of the first. First
opinions remain provisional; whole-block replacement can correct fields, groups,
categories, headings and omissions. All old issues still need explicit disposition.

First-result tables and nested references/operation selectors are reversible;
nonconforming values remain under `unparsed`, never silently normalized. Original
raw responses, decoded values, operand/source-kind expansion and native final
results are retained. A larger first result may still exceed the unchanged input
cap and must stop before another Provider call, not be truncated or summarized.

`data/evaluation/results/golden_computed_partition_offline_v1.json` records the
analyst-authored whole-report witnesses, not real responses: positive53666/61412,
negative53734/61314; combined first defects63632, all below63936. Both native
results preserve the original fixture values after explicit ordering/host
metadata expansion. Full negative→revision→positive path inputs are
53734/61314/58430/53666/61412. Full-output reservations total452396; actual-use
settlement and next-call reservation remain authoritative. No guarantee of
arbitrary output size,300-second completion or900-second whole-run time is made.

Independent contract and source audits plus adverse tests verify first-value
retention, old issues, complete body and assertion headings, replacement ownership,
strict final schema, aggregate/source isolation and the full five-call sequence.
An explicit wrong-sample/same-direction counterexample still passes structure;
host calculation is not semantic approval. After exact-SHA public checks, run
one frozen positive and read **every** judgment, source, scope and explanation.
Only actual semantic success permits the negative/revision/recheck. Failure
stops the batch and requires a whole-result diagnosis, not paid local retries.

## Existing product seams after reliable evaluation

Read-only follow-up confirmed that this experimental workflow is not yet a
product Runtime implementation. Preserve and reuse these existing seams:

- `app/product/coach_composition.py`: explicit Coach/Runtime/knowledge/Memory
  composition and supported contracts; candidate integration remains missing.
- `app/product/recent_review_service.py`: same-summary generation/Evidence
  projection and run/manifest/trace/source identity checks.
- `app/tasks/recent_review_executor.py`: validated publication sidecar becomes
  pending snapshot, task/event atomic commit and terminal delivery recovery.
- `app/api/main.py`: published recent summary/timeline/Evidence, observed
  Memory and Training APIs with owner/terminal/publication access gates.
- `app/evaluation/observation_archive.py`: existing ShowMaker export is bound
  to the historical run and manual report hashes, not a generic new-report
  publication path. Do not overwrite it to claim automatic integration.

After real semantic qualification, the next integration proves one observed
relationship/conversation/task/run across Coach, Review and Evidence, hidden
before publication, same hashes after publication, durable observation notes
after restart and no duplicate terminal message after recovery. Start with a
clearly labelled replay of accepted real artifacts, then bounded real end-to-end
verification. Observation exercises are not the reader's personal Training
plan; those goals need their own accepted identity/intent flow. Frontend aesthetic
renewal, portraits, four-part interaction and all62 themes remain in the existing
Astra restart plan and retrospective, not replaced by this reliability work.

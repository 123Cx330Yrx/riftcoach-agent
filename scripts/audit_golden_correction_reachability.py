"""Read-only audit of a frozen failed review and its available repair operations."""
import argparse
from collections import defaultdict
import hashlib
from pathlib import Path

from app.evaluation import golden_contextual_first_wire as first
from app.evaluation.golden_bounded_correction import _same_source
from app.evaluation.golden_contextual_patch_wire import PatchWire
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest
from scripts.run_golden_context_controls import load_inputs, UTTERANCE


def audit(source_run,base_report,case_dir):
    summary,source,knowledge,_ = load_inputs(source_run,base_report)
    from app.evaluation.golden_contextual_sources import build_inputs
    report = strict_json((case_dir/"input.json").read_text(encoding="utf-8"))["report"]
    inputs = build_inputs(EvaluationRequest(summary,source,knowledge,report,UTTERANCE))
    originals = {p:p.read_bytes() for p in (case_dir/"response-001.json",case_dir/"response-002.json",case_dir/"result.json")}
    raw = strict_json(originals[case_dir/"response-001.json"])["content"]
    state = first.prepare_state(raw,inputs)
    patch = PatchWire.model_validate(strict_json(strict_json(originals[case_dir/"response-002.json"])["content"]),strict=True)
    groups = defaultdict(list)
    for key,row in state.base.entries().items():
        if row["type"] == "claim":
            groups[(row["audit_index"],inputs.source.resolve(row["value"]["quote_ref"]))].append(key)
    duplicates = []
    for (audit_index,text),keys in groups.items():
        if len(keys) < 2:
            continue
        ref = state.base.entries()[keys[0]]["value"]["quote_ref"]
        block = inputs.source.blocks[ref["block"]-1][1]
        is_full = text == block
        shrink_blocked = False
        if is_full:
            # A proper nonempty literal subspan is known to be resolvable.
            for length in range(1,min(32,len(text)-1)+1):
                if text.count(text[:length]) == 1:
                    try:
                        _same_source(ref,dict(block=ref["block"],head=text[:length]),inputs.source)
                    except ValueError as error:
                        shrink_blocked = str(error) == "correction_cannot_reassign_or_shrink_source"
                    break
        duplicates.append(dict(audit_index=audit_index,targets=keys,block=ref["block"],
            full_block=is_full,shrink_blocked=shrink_blocked,claim_removal_available=False,
            exact_full_block_duplicates_unrepairable=is_full and shrink_blocked))
    properties = PatchWire.model_json_schema()["properties"]
    first_properties = first.FirstWire.model_json_schema()["properties"]
    result = dict(experiment=first.canonical.EXPERIMENT_ID,provider_calls=0,
        historical_result_changed=False,duplicate_groups=duplicates,
        correction_errors_supplied_to_model=strict_json(state.base.diagnostics_json),
        limits=dict(first_claims=first.FirstAudit.model_json_schema()["properties"]["claims"]["maxItems"]*2,
            claim_updates=properties["claim_updates"]["maxItems"],
            first_heading_reviews=first_properties["heading_reviews"]["maxItems"],
            heading_edits=properties["heading_edits"]["maxItems"],
            issue_edits=properties["issue_edits"]["maxItems"],
            first_issue_count_has_no_schema_max="maxItems" not in first_properties["issues"]),
        real_patch_targets=[row.target_id for row in patch.claim_updates],
        real_result=strict_json(originals[case_dir/"result.json"]),
        source_hashes={str(p):hashlib.sha256(data).hexdigest() for p,data in originals.items()},
        limitation="Schema-valid first states are not all repairable under the bounded patch contract; semantic correctness remains a separate manual check.")
    if any(p.read_bytes() != raw for p,raw in originals.items()):
        raise ValueError("frozen_evidence_changed")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("source-run","base-report","case-dir","output"):
        parser.add_argument("--"+key,type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.source_run,args.base_report,args.case_dir)
    write_new_json(args.output,result)
    print(compact(result))


if __name__ == "__main__": main()

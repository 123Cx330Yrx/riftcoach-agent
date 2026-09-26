"""Original-set preparation and receipt gate for the coarse contract.

The original 15 and independent source audit are still required. Neither this
module nor the injected tail can qualify a product task or transfer old results.
"""
import hashlib
from pathlib import Path
from app.evaluation import role_qualification as old
from app.evaluation import golden_coarse_source_projection as coarse
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as Workflow, CONTRACT_ID
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID
from app.runtime.coach_contract import COARSE_ROLE_COACH_CONTRACT as CONTRACT
from app.runtime.composition import RuntimeCompositionRoot

ASSETS = Path("examples/runtime_profiles/flash_glm_coarse_v1")
VERSION = "coarse-role-qualification-v1"


def candidate_identity(*, root=old.ROOT):
    RuntimeCompositionRoot.from_directories(skills_root=root/ASSETS/"skills",
        prompt_programs_root=root/ASSETS/"prompt_programs",coach_contract=CONTRACT)
    manifest = root/ASSETS/"prompt_programs/recent-form-review/manifest.json"
    return dict(contract=CONTRACT.snapshot().model_dump(),workflow_id=CONTRACT_ID,
        source_projection=coarse.VERSION,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())


def prepare_qualification(root=old.ROOT):
    identity = candidate_identity(root=root)
    cases,aliases = old.frozen_cases(root=root)
    rows,requests = [],{}
    for frozen,source in cases:
        inputs = Workflow.build_inputs(source)
        request = Workflow.make_request(inputs)
        raw = validate_request(request,transport_id=REVIEW_MODEL_TRANSPORT_ID)
        requests[frozen["key"]] = raw
        rows.append(dict(frozen,request_sha256=hashlib.sha256(raw).hexdigest(),
            source_catalog_sha256=coarse.source_catalog(inputs)["catalog_sha256"],
            schema_sha256=digest(compact(request.tools[0].input_schema)),
            first_input_ceiling=old.size(request)))
    return dict(qualification_version=VERSION,identity=identity,cases=rows,aliases=aliases,
        required_distinct_inputs=15,review_controls_qualified=False,
        actual_product_task_qualified=False,production_admitted=False,execution_enabled=False),requests


def replay_case(frozen, source, calls, *, include_stage_evidence=True):
    return old._replay_case(frozen,source,calls,workflow_type=Workflow,
        include_stage_evidence=include_stage_evidence)


def read_calls(directory):
    return old.read_role_calls(directory,source_projection=coarse.VERSION)


def summarize_role_calls(directory):
    return old.summarize_role_calls(directory, source_projection=coarse.VERSION)


def validate_qualification(result, *, evidence_root, root=old.ROOT):
    """Recheck original sealed double reviews and timing, not summary flags."""
    plan, _ = prepare_qualification(root=root)
    gate = old._validate_qualification(result, evidence_root=evidence_root, root=root,
        plan=plan, read_calls=read_calls,
        replay=lambda *args: replay_case(*args, include_stage_evidence=False))
    from scripts.qualify_role_observations import inspect_runs
    evidence_root = Path(evidence_root).resolve()
    originals, hosts = {}, {}
    for row in result['cases']:
        host = old._read(old._within(evidence_root, row['host_review_file']))
        closed = host.get('closed_export')
        if not isinstance(closed, dict) or not all(closed.get(k) for k in ('run_directory', 'path', 'sha256')):
            raise ValueError('coarse_qualification_sealed_observation_required')
        run = old._within(evidence_root, closed['run_directory'])
        binding = (closed['path'], closed['sha256'])
        if run in originals and originals[run] != binding:
            raise ValueError('coarse_qualification_seal_conflict')
        originals[run] = binding
        hosts[row['key']] = (host, old._within(evidence_root, row['transport_directory']))
    _, rebuilt, _, inspected, _, _ = inspect_runs(list(originals), evidence_root=evidence_root,
        closed_exports=list(originals.values()), profile='coarse')
    if rebuilt != plan or len(inspected) != 15 or any(
            hosts.get(row['key']) != (host, transport) for row, host, transport in inspected):
        raise ValueError('coarse_qualification_strict_observation_mismatch')
    return gate


# Shared audits retain the original dataset, labels and source serialization.
frozen_cases = old.frozen_cases
read_role_calls = read_calls
size = old.size
review = old.review

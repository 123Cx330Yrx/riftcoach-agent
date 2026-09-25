"""Prepare/replay coarse controls, not an admission adapter.

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


def prepare_qualification(root=old.ROOT):
    RuntimeCompositionRoot.from_directories(skills_root=root/ASSETS/"skills",
        prompt_programs_root=root/ASSETS/"prompt_programs",coach_contract=CONTRACT)
    manifest = root/ASSETS/"prompt_programs/recent-form-review/manifest.json"
    identity = dict(contract=CONTRACT.snapshot().model_dump(),workflow_id=CONTRACT_ID,
        source_projection=coarse.VERSION,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
    cases,aliases = old.frozen_cases(root=root)
    rows,requests = [],{}
    for frozen,source in cases:
        inputs = Workflow.build_inputs(source)
        request = Workflow.make_request(inputs)
        raw = validate_request(request,transport_id=REVIEW_MODEL_TRANSPORT_ID)
        requests[frozen["key"]] = raw
        rows.append(dict(frozen,request_sha256=hashlib.sha256(raw).hexdigest(),
            source_catalog_sha256=coarse.source_catalog(inputs)["catalog_sha256"],
            schema_sha256=digest(compact(request.tools[0].input_schema))))
    return dict(qualification_version=VERSION,identity=identity,cases=rows,aliases=aliases,
        required_distinct_inputs=15,review_controls_qualified=False,
        actual_product_task_qualified=False,production_admitted=False,execution_enabled=False),requests


def replay_case(frozen, source, calls):
    return old._replay_case(frozen,source,calls,workflow_type=Workflow,include_stage_evidence=True)


def read_calls(directory):
    return old.read_role_calls(directory,source_projection=coarse.VERSION)

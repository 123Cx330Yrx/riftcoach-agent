"""Same-version document original15 controls; no product registration."""
from pathlib import Path

from app.evaluation import boundary_examples_qualification as base
from app.evaluation import role_qualification as old
from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_review_experiment import digest

from scripts.report_document_workflow import DocumentReviewWorkflow as Workflow
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT as CONTRACT
from app.runtime.document_review_provider_factory import DocumentRoleProviderFactory as ProviderFactory
from app.evaluation.document_review_identity import role_for_request
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID
from app.evaluation.golden_review_experiment import compact
from scripts import report_document_view as view
import hashlib
CONTRACT_ID = 'document-review-original15-v1'
VERSION = 'document-review-role-qualification-v1'
PROFILE = 'document-review'
SOURCE_FILES = (
    'app/evaluation/review_bound_editor.py',
    'app/evaluation/coarse_revision_editor.py',
    'app/evaluation/source_patch_editor.py',
    'app/evaluation/document_review_identity.py',
    'app/evaluation/golden_review_experiment.py',
    'app/evaluation/golden_inference_coverage.py',
    'app/evaluation/golden_inference_scope_v5.py',
    'app/providers/models.py',
    'app/evaluation/coach_report.py',
    'app/report_validation.py',
    'app/evaluation/document_review_qualification.py',
    'app/runtime/document_review_roles.py',
    'app/runtime/document_review_provider_factory.py',
    'app/runtime/reviewer_roles.py',
    'app/runtime/receipted_provider_factory.py',
    'app/runtime/coach_contract.py',
    'app/runtime/coach_budget.py',
    'scripts/report_document_view.py',
    'scripts/report_document_workflow.py',
    'scripts/run_document_review_qualification.py',
    'scripts/role_stage_review_drafts.py',
    'scripts/role_continuation.py',
)



def candidate_identity(*, root=old.ROOT):
    identity = base.candidate_identity(root=root)
    # The review model/policy is unchanged, but old whole-report qualifications
    # cannot authorize this different revision protocol or its evidence.
    return dict(identity, contract=CONTRACT.snapshot().model_dump(), workflow_id=CONTRACT_ID,
        report_presentation=view.VERSION,
        revision_protocol=editor.VERSION,
        revision_source_sha256={name: digest((root/name).read_text(encoding='utf-8'))
                                for name in SOURCE_FILES})


def prepare_qualification(root=old.ROOT):
    cases, aliases = frozen_cases(root=root)
    rows, requests = [], {}
    for frozen, source in cases:
        inputs = Workflow.build_inputs(source)
        request = Workflow.make_request(inputs)
        role_for_request(request)
        raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        requests[frozen['key']] = raw
        rows.append(dict(frozen, request_sha256=hashlib.sha256(raw).hexdigest(),
            source_catalog_sha256=base.coarse.source_catalog(inputs)['catalog_sha256'],
            schema_sha256=digest(compact(request.tools[0].input_schema)),
            first_input_ceiling=size(request)))
    return dict(qualification_version=VERSION, identity=candidate_identity(root=root), cases=rows,
        aliases=aliases, required_distinct_inputs=15, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False, execution_enabled=False), requests



def replay_case(frozen, source, calls, *, include_stage_evidence=True):
    return old._replay_case(frozen, source, calls, workflow_type=Workflow,
        include_stage_evidence=include_stage_evidence)


def validate_qualification(result, *, evidence_root, root=old.ROOT):
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
            raise ValueError('document_review_qualification_sealed_observation_required')
        run = old._within(evidence_root, closed['run_directory'])
        binding = (closed['path'], closed['sha256'])
        if run in originals and originals[run] != binding:
            raise ValueError('document_review_qualification_seal_conflict')
        originals[run] = binding
        hosts[row['key']] = (host, old._within(evidence_root, row['transport_directory']))
    _, rebuilt, _, inspected, _, _ = inspect_runs(list(originals), evidence_root=evidence_root,
        closed_exports=list(originals.values()), profile=PROFILE)
    if rebuilt != plan or len(inspected) != 15 or any(
            hosts.get(row['key']) != (host, transport) for row, host, transport in inspected):
        raise ValueError('document_review_qualification_strict_observation_mismatch')
    return gate


def read_calls(directory):
    return old.read_role_calls(directory, source_projection=base.coarse.VERSION,
                               request_role=role_for_request)


def summarize_role_calls(directory):
    return old.summarize_role_calls(directory, source_projection=base.coarse.VERSION,
                                    request_role=role_for_request)


read_role_calls = read_calls
frozen_cases = old.frozen_cases
size = old.size
review = old.review

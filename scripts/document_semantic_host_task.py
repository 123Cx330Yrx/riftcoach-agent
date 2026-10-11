"""Build prospective review tasks from exact comparison exchanges.

No dispatch, authored judgment, native event import or model call is performed.
The execution consumer must verify the transport receipt before this builder.
"""
import json
from pathlib import Path

from scripts import document_semantic_request as identity
from scripts import prepare_document_semantic_comparison as preparation
from scripts.codex_review_event_source import review_task
from scripts.document_review_host_task import with_policies
from app.evaluation.role_task_outcome import stage_identity
from app.evaluation.golden_review_experiment import compact, digest
from scripts.report_timed_document_workflow import TimedDocumentWorkflow


def stage_for(cell, inputs, request, response):
    identity.request_bytes(request)
    if identity.request_sha(request) != cell['request_sha256']:
        raise ValueError('semantic_stage_request_binding')
    if (response.provider != 'zhipu' or response.model != 'glm-5.3'
            or response.finish_reason != 'tool_calls' or (response.content or '').strip()
            or len(response.tool_calls) != 1 or response.tool_calls[0].name != 'submit_report_review'):
        raise ValueError('semantic_response_tool_channel')
    raw = compact(dict(response.tool_calls[0].arguments))
    _, wire, journal = TimedDocumentWorkflow.validate_review(raw, inputs)
    # The unchanged business validator does not claim to have applied the new
    # suffix. Keep its baseline identity and the actual prospective policy apart.
    journal = dict(journal, baseline_policy_sha256=journal['policy_sha256'],
        policy_sha256=digest(request.messages[0].content),
        semantic_comparison_identity=identity.VERSION,
        semantic_comparison_variant=cell['variant'],
        issued_request_sha256=identity.request_sha(request))
    return wire, dict(stage=cell['stage'], report=inputs.source.report, journal=journal)


def task(plan, cell, stage, bound, artifact_directory, request_raw, material_path):
    folder = Path(artifact_directory).resolve()
    material_path = Path(material_path).resolve()
    request = preparation.read_request(request_raw)
    if (cell not in plan['cells'] or identity.request_bytes(request) != request_raw
            or preparation.sha(request_raw) != cell['request_sha256']
            or bound['request_sha256'] != preparation.sha(request_raw)
            or bound['plan_sha256'] != preparation.sha(preparation.options.canonical(plan))
            or bound['key'] != cell['key'] or bound['stage'] != cell['stage']
            or stage['stage'] != cell['stage'] or bound['report_sha256'] != digest(stage['report'])
            or request.metadata[identity.MARKER]['variant'] != cell['variant']):
        raise ValueError('semantic_host_task_binding')
    material_raw = material_path.read_bytes()
    material = json.loads(material_raw)
    if (preparation.sha(material_raw) != cell['material_sha256']
            or material['report'] != stage['report']
            or material['source_key'] != cell['source_key']
            or material['source_stage'] != cell['source_stage']):
        raise ValueError('semantic_host_material_binding')
    reviewer = plan['review_principals']['independent']['principal_id']
    report_rule = ('report_assessment=null; this acceptance judges the actual opinion, '
        'not the erroneous source report as fixed.' if cell['stage'] == 'initial' else
        'report_assessment contains report_sha256=' + bound['report_sha256'] +
        ', reviewer, source_review and facts_and_sources_correct, correct_content_preserved, '
        'identity_and_goal_preserved, true_errors_fixed. All four must be true for acceptance. '
        'This is a fixed historical corrected report reviewed in a new comparison, not an edit '
        'or fresh dependent on this comparison and not retroactive qualification.')
    instructions = (
        f'Read the complete material at {material_path}, including current_input_json, report, '
        'original source, historical initial journal/request and all source citations. '
        f'Read actual issued-request.json, response.json and stage.json in {folder}. '
        'Historical Provider stages are context, never the new verdict or Host opinion. '
        'Do not read primary notes, host-reviews, other variants or expected case labels. '
        'Judge every actual issue, explanation, correction, advisory and retained report under '
        'the exact current policy. For disputes state the asserted proposition, whole-document '
        'scope basis and concrete source conflict or material unresolved ambiguity. '
        'No Provider calls, edits, private reasoning inspection or manufactured agreement. '
        f'Return only JSON {{binding: exact six fields, review: {{binding: same fields, '
        f'stage_assessment: {{stage: "{cell["stage"]}", stage_sha256: "{stage_identity(stage)}", '
        f'reviewer: "{reviewer}", source_review: detailed full-source assessment, accepted: boolean, '
        'defects: [{kind,detail}]}, report_assessment: ...}}}. '
        'Defect kinds: missed_error,false_positive,unsupported_explanation,wrong_correction,'
        'unsupported_source,internal_contradiction,wrong_final_report,correct_content_lost,'
        'identity_or_goal_changed. accepted=true requires defects=[]; rejection requires concrete defects. '
        + report_rule + ' Do not supply independent_source_event or primary_attestation. '
        'After recovery and before final reread the exact checkpoint and SHA; check your own answer '
        'then emit one multiline JSON native final. Same-task recovery uses MESSAGE, not NEW_TASK.')
    return with_policies(review_task(bound, instructions), request_raw)

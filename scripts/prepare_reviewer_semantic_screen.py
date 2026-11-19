"""Offline material assembly only. No sender, key lookup, run or qualification.

The evaluator sidecar is deliberately not consulted to construct requests.
Reuses the frozen complete source loader and current business policies.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.source_patch_editor import report_inputs
from scripts import prepare_reviewer_profile_screen as source
from scripts import reviewer_responses_nonstream as nonstream
from scripts import review_duty_direct_patch as direct
from scripts.report_document_view import restore_document

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'data/evaluation/fixtures/reviewer_semantic_screen_20261018'
VERSION = 'reviewer-semantic-materials-v1'
CASES = ('s01', 's02', 's03')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def assemble(package=PACKAGE):
    """Reports and archived source only; no labels or author opinions as inputs."""
    original = source.source_inputs()
    rows, files = [], {}
    for case in CASES:
        raw = (package / (case + '.md')).read_bytes()
        report = raw.decode('utf-8')
        inputs = report_inputs(original, report)
        for duty in source.DUTIES:
            request = replace(source.make_request(inputs, duty),
                              metadata={'offline_materials': VERSION, 'duty': duty})
            document = request.messages[1].content
            begin, end = '[UNTRUSTED REPORT DOCUMENT]\n', '\n[END UNTRUSTED REPORT DOCUMENT]'
            if not document.startswith(begin) or not document.endswith(end):
                raise ValueError('material_report_envelope')
            if restore_document(document[len(begin):-len(end)], inputs) != report:
                raise ValueError('material_report_loss')
            estimated = source.estimate_runtime_request_input_ceiling(request)
            if estimated > nonstream.MAX_INPUT:
                raise ValueError('material_input_budget')
            business = source.visible(source.json_value(request))
            wire = nonstream.build_wire(business)
            key = case + '-' + duty
            files['requests/' + key + '.json'] = encode(business)
            files['wire/' + key + '.json'] = encode(wire)
            rows.append(dict(id=key, report_sha256=sha(raw),
                request_file_sha256=sha(files['requests/' + key + '.json']),
                wire_file_sha256=sha(files['wire/' + key + '.json']),
                policy_sha256=digest(request.messages[0].content),
                schema_sha256=digest(compact(request.tools[0].input_schema)),
                input_sha256=digest(inputs.data_json),
                existing_local_input_estimate=estimated,
                model_result=None, actual_http=None))
    return rows, files


def check_contrasts(package=PACKAGE):
    evaluation = json.loads((package / 'evaluation.json').read_bytes())
    base = (package / 's01.md').read_bytes().decode('utf-8')
    if set(evaluation['contrasts']) != {'s02', 's03'}:
        raise ValueError('material_contrast_inventory')
    for case, edit in evaluation['contrasts'].items():
        if base.count(edit['before']) != 1:
            raise ValueError('material_contrast_anchor')
        actual = (package / (case + '.md')).read_bytes().decode('utf-8')
        if actual != base.replace(edit['before'], edit['after'], 1):
            raise ValueError('material_contrast_changed')
    return evaluation


def business_validator(business):
    """Bind the real worker without reading evaluator labels or author opinions."""
    matches = []
    for case in CASES:
        for duty in source.DUTIES:
            path = PACKAGE / 'requests' / (case + '-' + duty + '.json')
            if json.loads(path.read_bytes()) == business:
                matches.append((case, duty))
    if len(matches) != 1:
        raise ValueError('semantic_request_binding')
    case, duty = matches[0]
    inputs = report_inputs(source.source_inputs(), (PACKAGE / (case + '.md')).read_bytes().decode('utf-8'))
    rebuilt = source.visible(source.json_value(source.make_request(inputs, duty)))
    if rebuilt != business:
        raise ValueError('semantic_request_reconstruction')
    return lambda raw: direct.validate(raw, inputs, duty)


def reference_previews(package=PACKAGE):
    """Human-authored feasibility witnesses, never actual model/Host opinions."""
    evaluation = check_contrasts(package)
    original = source.source_inputs()
    expected = (package / 's01.md').read_bytes().decode('utf-8')
    results = []
    for case in CASES:
        inputs = report_inputs(original, (package / (case + '.md')).read_bytes().decode('utf-8'))
        opinions = evaluation['synthetic_reference_reviews'][case]
        preview = direct.preview(inputs, [direct.bind(inputs, duty, compact(opinions[duty]))
                                         for duty in source.DUTIES])
        if preview.report != expected:
            raise ValueError('material_reference_does_not_restore_baseline')
        results.append(dict(id=case, assembled_sha256=digest(preview.report),
            operations=len(preview.journal['operations']), synthetic=True,
            semantic_approval=False, actual_model_response=False))
    return results


def prepare(package=PACKAGE):
    rows, files = assemble(package)
    previews = reference_previews(package)
    inputs = {name: sha((package / name).read_bytes()) for name in
              ('s01.md', 's02.md', 's03.md', 'evaluation.json', 'primary-material-review.json')}
    manifest = dict(version=VERSION, source_material_sha256=source.MATERIAL_SHA,
        evidence_class='authored-development-screen-familiar-source-not-holdout',
        inputs=inputs, artifacts={name: sha(raw) for name, raw in files.items()},
        rows=rows, synthetic_reference_previews=previews,
        proposed_budget=dict(max_requests=6, max_retries=0, input_tokens_per_request=64000,
            output_tokens_per_request=16384, maximum_total_tokens=482304,
            request_timeout_seconds=300, maximum_active_seconds=1800,
            historical_gpt_pro_estimate_cny='0.350208', historical_price_date='2026-10-15',
            current_price_verified=False, hard_billing_cap=False, input_tokenizer_verified=False),
        proposed_response_mode=nonstream.MODE, selected_execution_profile=None,
        independent_material_review=None, provider_calls=0, execution_ready=False,
        execution_authorized=False, qualified=False, publication_allowed=False)
    return manifest, files


def verify(package=PACKAGE):
    manifest, files = prepare(package)
    if json.loads((package / 'manifest.json').read_bytes()) != manifest:
        raise ValueError('material_manifest_changed')
    for name, raw in files.items():
        if (package / name).read_bytes() != raw:
            raise ValueError('material_saved_request_changed')
    return manifest


if __name__ == '__main__':
    result = verify()
    print(json.dumps(dict(requests=len(result['rows']), provider_calls=0,
                         execution_ready=False, qualified=False), ensure_ascii=True))

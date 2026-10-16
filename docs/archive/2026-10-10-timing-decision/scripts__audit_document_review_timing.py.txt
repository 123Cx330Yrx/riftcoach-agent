"""Offline timing decision from a closed seal and hash-bound public metadata.

No model client, settings, environment file, native review or business run is
opened. Synthetic budget probes exercise the existing task budget, not a new
transport. A censored call never acquires a predicted completion or Usage.
"""
from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_stream_bridge as bridge
from app.providers.errors import ProviderError, ProviderTimeoutError
from app.providers.models import ChatResponse, TokenUsage
from app.providers.zhipu import ZhipuProvider
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT as CONTRACT
from app.runtime.reviewer_roles import ROLE_COMPOSITION_ID, ROLE_PROFILE_ID
from scripts import report_contrast_review as candidate
from scripts.report_document_view import VERSION as PRESENTATION

ROOT = Path(__file__).resolve().parents[1]
SEAL = 'data/evaluation/results/golden_document_focused10_resumption_result_20261010.json'
SEAL_SHA = '76e9a70b808ce297d7d57c8f226a26daaa72f1f932de15f0c39467c582575f30'
CAPSULE = 'data/evaluation/results/golden_document_focused10_timing_metadata_20261010.json'
OUTPUT = 'data/evaluation/contracts/document_review_timing_decision_20261010.json'
CALLS = tuple((case, stage, role, ordinal) for case in ('attribution-1', 'scope-3')
             for stage, role, ordinal in (('initial', 'review', 1),
                                          ('revision', 'generation', 2), ('final', 'review', 3)))
SUFFIXES = ('reservation.json', 'progress.json', 'result.json')
FILES = tuple(f'transport/{case}/{role}/stream-{ordinal:03d}/{suffix}'
              for case, _, role, ordinal in CALLS for suffix in SUFFIXES)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_sha(path):
    # Git normalizes source line endings; evidence bytes are never normalized.
    return sha(path.read_bytes().replace(b'\r\n', b'\n'))


def load_seal(root=ROOT):
    raw = (root / SEAL).read_bytes()
    if sha(raw) != SEAL_SHA:
        raise ValueError('timing_seal_bytes_changed')
    return json.loads(raw)


def export_metadata(directory, *, root=ROOT):
    """Explicit, read-only export of exactly 18 body-free original files."""
    seal = load_seal(root)
    files = {}
    for key in FILES:
        raw = (Path(directory) / key).read_bytes()
        if sha(raw) != seal['original_file_sha256'][key]:
            raise ValueError('timing_original_changed')
        files[key] = raw.decode('utf-8')
    capsule = dict(kind='document-review-body-free-timing-metadata-v1',
                   seal_sha256=SEAL_SHA, files=files)
    validate_metadata(capsule, seal)
    return capsule


def validate_metadata(capsule, seal):
    if (set(capsule) != {'kind', 'seal_sha256', 'files'}
            or capsule['kind'] != 'document-review-body-free-timing-metadata-v1'
            or capsule['seal_sha256'] != SEAL_SHA or set(capsule['files']) != set(FILES)):
        raise ValueError('timing_metadata_inventory_changed')
    values = {}
    for key, raw in capsule['files'].items():
        if not isinstance(raw, str) or sha(raw.encode('utf-8')) != seal['original_file_sha256'][key]:
            raise ValueError('timing_metadata_bytes_changed')
        values[key] = json.loads(raw)
    return values


class _ProbeLimits:
    """Synthetic-only overlay; never registered or accepted by a real factory."""
    def __init__(self, request_cap):
        self.request_cap = request_cap

    def __getattr__(self, name):
        return getattr(CONTRACT, name)

    def descriptor(self):
        return dict(CONTRACT.descriptor(), request_timeout_s=self.request_cap)

    @staticmethod
    def request_identity(request):
        # Classification of the genuine old request, not new transport identity.
        # The real 600s request must still be rejected by the old transport.
        return candidate.request_identity(replace(request, timeout_s=min(300, request.timeout_s)))


def budget_probe(seal, *, review_cap, spent_before_s=0, hypothetical_fresh_s=450):
    """Run three synthetic responses through the real shared 900s budget.

    450s is a counterexample, not an estimate for the timed-out request.
    Synthetic Usage is explicit and never merged with closed-call accounting.
    spent_before_s represents generation/retrieval time absent from this suite.
    """
    if review_cap not in (300, 600) or spent_before_s not in (0, 500, 900):
        raise ValueError('timing_probe_configuration')
    now, seen = [0.0], []
    rows = seal['public_json_contents']
    durations = (52.985, 22.532, hypothetical_fresh_s)

    class SyntheticProvider:
        provider_name, model_name = 'zhipu', ROLE_COMPOSITION_ID
        thinking_profile_id, sdk_max_retries = ROLE_PROFILE_ID, 0
        runtime_profile, report_presentation = None, PRESENTATION
        capabilities = ZhipuProvider.capabilities
        source_projection = CONTRACT.descriptor()['source_projection']

        def chat(self, request):
            index = len(seen)
            role = 'revision' if index == 1 else 'review'
            model = 'glm-5.3-flash' if role == 'revision' else 'glm-5.3'
            seen.append(dict(role=role, timeout_s=round(request.timeout_s, 6),
                             max_tokens=request.max_tokens))
            now[0] += min(durations[index], request.timeout_s)
            if durations[index] >= request.timeout_s:
                raise ProviderTimeoutError(provider='zhipu', code='stream_deadline')
            return ChatResponse(content='Synthetic budget-only response.', provider='zhipu',
                                model=model, usage=TokenUsage(input_tokens=13000, output_tokens=6500))

    budget = CoachBudgetedProvider(SyntheticProvider(), coach_contract=CONTRACT, clock=lambda: now[0])
    budget.contract = _ProbeLimits(review_cap)
    now[0] = spent_before_s
    error = None
    for stage in ('initial', 'revision', 'final'):
        request = bridge.REQUEST.validate_python(rows[f'scope-3/{stage}/issued-request.json'])
        request = replace(request, timeout_s=300 if stage == 'revision' else review_cap)
        try:
            budget.chat(request)
        except ProviderTimeoutError as exc:
            error = exc.code
            break
        except ProviderError as exc:
            error = exc.code
            break
    return dict(evidence='synthetic_actual_shared_budget', review_cap_s=review_cap,
                task_cap_s=900, spent_before_s=spent_before_s,
                hypothetical_fresh_s=hypothetical_fresh_s, issued=seen,
                completed=error is None, error=error, elapsed_s=round(now[0], 6),
                synthetic_calls=budget.calls, synthetic_known_tokens=budget.tokens,
                unknown_reserved_tokens=budget.reserved_tokens, stopped=budget.stopped)


def audit(*, root=ROOT):
    seal = load_seal(root)
    capsule = json.loads((root / CAPSULE).read_text(encoding='utf-8'))
    metadata = validate_metadata(capsule, seal)
    calls = []
    for case, stage, role, ordinal in CALLS:
        base = f'transport/{case}/{role}/stream-{ordinal:03d}/'
        reservation, progress, terminal = (metadata[base + name] for name in SUFFIXES)
        request = seal['public_json_contents'][f'{case}/{stage}/issued-request.json']
        calls.append(dict(key=case, stage=stage, role=role,
            request_sha256=reservation['request_sha256'], state=terminal['state'],
            elapsed_ms=terminal['elapsed_ms'], first_event_ms=progress['first_event_ms'],
            last_event_ms=progress['last_event_ms'], first_tool_ms=progress['first_tool_ms'],
            reasoning_chars=progress['reasoning_chars'], tool_delta_count=progress['tool_delta_count'],
            http_requests=progress['http_requests'], input_tokens=progress['input_tokens'],
            output_tokens=progress['output_tokens'], request_metrics=reservation['request_metrics'],
            request_timeout_s=request['timeout_s'],
            message_content_chars=[len(m['content'] or '') for m in request['messages']],
            source_file_sha256={name: seal['original_file_sha256'][base + name] for name in SUFFIXES}))
    known = sum(c['input_tokens'] + c['output_tokens'] for c in calls if c['state'] == 'complete')
    unknown = sum(c['input_tokens'] is None or c['output_tokens'] is None for c in calls)
    if (known != seal['accounting']['known_tokens'] or unknown != seal['accounting']['unknown_usage_calls']
            or len(calls) != seal['accounting']['calls']):
        raise ValueError('timing_usage_accounting_mismatch')
    old_request = bridge.REQUEST.validate_python(
        seal['public_json_contents']['scope-3/final/issued-request.json'])
    try:
        bridge.validate_request(replace(old_request, timeout_s=600),
                                transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID)
    except Exception as exc:
        old_transport_refusal = getattr(exc, 'code', type(exc).__name__)
    else:
        raise ValueError('timing_old_transport_unexpectedly_allows_600')
    try:
        bridge.CapacityBridgeObservation(elapsed_ms=450000)
    except ValueError:
        old_observation_refusal = True
    else:
        raise ValueError('timing_old_observation_unexpectedly_allows_450s')
    paths = (Path(__file__).relative_to(ROOT).as_posix(), 'app/runtime/coach_budget.py',
        'app/runtime/coach_contract.py', 'app/evaluation/golden_stream_bridge.py',
        'app/evaluation/document_review_identity.py', 'app/workers/review_worker.py',
        'scripts/run_full15_resumption_candidate.py', 'scripts/role_development_host_clock.py')
    return dict(kind='document-review-timing-decision-v1', seal_sha256=SEAL_SHA,
        metadata_sha256=sha((root / CAPSULE).read_bytes()),
        source_digest_mode='utf8-source-lf',
        source_sha256={p: source_sha(root / p) for p in paths},
        accounting=seal['accounting'], observed_calls=calls,
        right_censored=dict(key='scope:3', stage='final', completion_time_known=False,
            usage_known=False, causal_root_established=False, predicted_finish_s=None),
        current_product_limits={k: CONTRACT.descriptor()[k] for k in
            ('max_calls', 'request_timeout_s', 'execution_timeout_s', 'max_output_tokens', 'total_tokens')},
        diagnostic_limits=dict(
            batch_active_seconds=seal['public_json_contents']['plan.json']['preparation_plan']['budget']['max_active_seconds'],
            batch_host_seconds=seal['public_json_contents']['plan.json']['preparation_plan']['budget']['max_host_seconds'],
            independent_case_900s_wall_enforced=False, natural_generation_included=False),
        synthetic_probes=[budget_probe(seal, review_cap=cap, spent_before_s=prefix)
                          for cap, prefix in ((300, 0), (600, 0), (600, 500), (600, 900))],
        integration_blockers=dict(old_transport_600_refusal=old_transport_refusal,
            old_observation_450s_refused=old_observation_refusal,
            prepared_request_and_role_identity_max_s=300,
            workflow_prepared_vs_issued_timeout_requires_rebinding=True,
            old_native_and_qualification_evidence_not_transferable=True),
        decision='prepare_isolated_role_600_task_900_candidate_without_retries_or_live_admission',
        actual_new_provider_calls=0, execution_ready=False, new_qualification=0)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-metadata-from', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if args.export_metadata_from is not None:
        value = export_metadata(args.export_metadata_from)
        with (ROOT / CAPSULE).open('xb') as stream:
            stream.write(encoded(value))
        print('timing metadata exported create-only; Provider calls=0')
        return
    value = audit()
    if args.json:
        print(encoded(value).decode('utf-8'), end='')
    else:
        if (ROOT / OUTPUT).read_bytes() != encoded(value):
            raise ValueError('timing_frozen_decision_changed')
        print('Timing decision matches public originals; synthetic budget probes passed; Provider calls=0')


if __name__ == '__main__':
    main()

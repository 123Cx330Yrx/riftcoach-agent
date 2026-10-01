"""Real application and receipted transports, with only the child model scripted."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.providers.config import ZhipuSettings
from app.providers.errors import ProviderResponseError
from app.runtime.store import RuntimeTraceStore
from scripts import native_coach_preparation as common
from scripts import run_role_coach_development as runner
from tests.test_native_editor_product_budget import offline
from tests.test_reviewer_role_proposal import providers


SOURCE_NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)


def arguments(tmp_path, **changes):
    return SimpleNamespace(**dict(dict(execute=False, run_id='role-development-test', ci_run='offline-ci',
        env_file=tmp_path / 'unused.env', output_root=tmp_path / 'runs', request_output=None,
        source_now=SOURCE_NOW.isoformat(), approval_plan_sha=''), **changes))


def execution_arguments(tmp_path, **changes):
    args = arguments(tmp_path, **changes)
    preview = runner.run(args)
    args.execute = True
    args.approval_plan_sha = preview['preparation_plan_sha256']
    return args


@pytest.fixture
def environment(monkeypatch):
    generator, _ = providers()
    # Committed scripted source fixture, never private untracked data/runs.
    monkeypatch.setattr(common, 'load_frozen_sources', lambda: (deepcopy(generator.req.player_summary),
        SimpleNamespace(data_dragon=None, official_patch=None, meta_evidence=())))
    checks = []
    monkeypatch.setattr(runner, 'verify_public_ci', lambda ci: checks.append(('ci', ci)) or 'a' * 40)
    monkeypatch.setattr(runner, 'require_unchanged_checkout', lambda head: checks.append(('checkout', head)))
    def credentials(path):
        checks.append(('credentials', path))
        return tuple(ZhipuSettings(api_key='test-secret', base_url='https://open.bigmodel.cn/api/paas/v4', model=model,
            default_timeout_s=123) for model in ('glm-5.3-flash', 'glm-5.3'))
    monkeypatch.setattr(runner, 'load_role_settings', credentials)
    return checks


def scripted_child(monkeypatch, *, scenario='normal'):
    generator, reviewer = providers(recover=scenario == 'recover')
    if scenario == 'pass':
        reviewer.review_calls = 1
    sent = []
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(raw, strict=True)
        sent.append((request, environ['LLM_MODEL'], directory))
        assert environ['LLM_API_KEY'] == 'test-secret'
        if len(sent) == 3 and scenario in ('failed', 'cancelled'):
            if scenario == 'cancelled':
                raise KeyboardInterrupt()
            raise ProviderResponseError(provider='zhipu', code='scripted_transport_failure')
        selected = reviewer if environ['LLM_MODEL'] == 'glm-5.3' else generator
        response = selected.chat(request)
        write_new_json(directory / 'result.json', dict(state='complete',
            transport_id='wrong' if scenario == 'bad_receipt' else transport_id))
        return response
    monkeypatch.setattr(bridge, 'run_child', child)
    return sent


def test_preview_has_no_credentials_network_or_run_writes_and_is_reproducible(tmp_path, environment):
    first = runner.run(arguments(tmp_path))
    second = runner.run(arguments(tmp_path, source_now=first['source_now']))
    assert first == second and environment == []
    assert not tmp_path.joinpath('runs').exists()
    assert first['provider_requests'] == 0 and first['mode'] == 'preview'
    assert not first['production_admitted'] and not first['semantic_approval']
    assert first['shared_budget'] == dict(max_calls=5, total_tokens=401920, execution_timeout_s=900,
        max_revisions=1, sdk_retries=0)


def test_loaded_credentials_are_copied_only_overriding_models(monkeypatch, tmp_path):
    import dotenv
    from app.providers import config
    settings = ZhipuSettings(api_key='never-print', base_url='https://open.bigmodel.cn/api/paas/v4',
        model='glm-5.3-flash', default_timeout_s=47)
    monkeypatch.setattr(config, 'load_zhipu_settings', lambda values: settings)
    monkeypatch.setattr(dotenv, 'dotenv_values', lambda path: {})
    generator, reviewer = runner.load_role_settings(tmp_path / 'missing.env')
    assert generator == settings and generator is not settings
    assert reviewer == replace(settings, model='glm-5.3')
    assert generator.api_key == reviewer.api_key == settings.api_key


def test_real_application_five_calls_tool_memory_evidence_and_costs(tmp_path, monkeypatch, environment):
    sent = scripted_child(monkeypatch)
    args = execution_arguments(tmp_path)
    outcome = runner.run(args)
    assert outcome['status'] == 'published', outcome
    assert len(sent) == 5 and outcome['completed_calls'] == 5
    assert [model for _, model, _ in sent] == ['glm-5.3-flash', 'glm-5.3-flash', 'glm-5.3', 'glm-5.3-flash', 'glm-5.3']
    assert outcome['revision_exercised'] and outcome['revision_completed'] and outcome['first_request_matched']
    assert any(m.role.value == 'tool' for m in sent[1][0].messages)
    assert '不是阅读者本人' in ''.join(m.content or '' for m in sent[0][0].messages)
    assert outcome['unknown_usage_calls'] == 0 and outcome['total_estimated_uncached_cny'] == '0.000828'
    assert outcome['by_model']['glm-5.3']['completed_calls'] == 2
    assert not outcome['semantic_approval'] and not outcome['original_15_qualified']
    assert environment[0] == ('ci', 'offline-ci') and environment[1][0] == 'credentials'
    directory = args.output_root / 'observations' / args.run_id
    plan = json.loads((directory / 'plan.json').read_text(encoding='utf-8'))
    assert plan['first_request_sha256'] == hashlib.sha256((directory / 'first-request.json').read_bytes()).hexdigest()
    assert plan['source_now'] == SOURCE_NOW.isoformat()
    assert outcome == json.loads((directory / 'result.json').read_text(encoding='utf-8'))
    raw_plan = (directory / 'plan.json').read_text(encoding='utf-8')
    assert 'test-secret' not in raw_plan
    from app.runtime.models import RuntimeTraceReference
    ref = RuntimeTraceReference.model_validate(outcome['result']['trace_reference'])
    trace = RuntimeTraceStore(args.output_root / 'reports', args.run_id).read_trace(ref)
    assert trace.usage.provider_calls_attempted == 5 and str(trace.usage.cost) == '0.000828'
    assert outcome['pending_snapshot_run_id'] == args.run_id and outcome['evidence_bundle_digest']
    with pytest.raises(FileExistsError, match='already_exists'):
        runner.run(args)
    assert len(sent) == 5


@pytest.mark.parametrize('scenario,status,calls,revision,unknown', [
    ('pass', 'published', 3, False, 0), ('recover', 'rejected', 5, True, 0),
    ('failed', 'rejected', 3, False, 1), ('cancelled', 'cancelled', 3, False, 1),
])
def test_completion_budget_failure_and_cancellation_keep_honest_boundaries(tmp_path, monkeypatch, environment,
        scenario, status, calls, revision, unknown):
    sent = scripted_child(monkeypatch, scenario=scenario)
    args = execution_arguments(tmp_path)
    outcome = runner.run(args)
    assert outcome['status'] == status, outcome
    assert len(sent) == outcome['reserved_calls'] == calls
    assert outcome['revision_exercised'] is revision
    assert outcome['unknown_usage_calls'] == unknown
    assert (outcome['total_estimated_uncached_cny'] is None) is bool(unknown)
    assert outcome['known_usage_estimated_uncached_cny'] != '0'
    assert outcome['report_available'] is (status == 'published')
    assert not outcome['semantic_approval'] and not outcome['actual_product_task_qualified']
    assert (args.output_root / 'observations' / args.run_id / 'result.json').exists()


def test_invalid_receipt_is_not_relabelled_as_zero_fee(tmp_path, monkeypatch, environment):
    sent = scripted_child(monkeypatch, scenario='bad_receipt')
    outcome = runner.run(execution_arguments(tmp_path))
    assert len(sent) == 1 and outcome['accounting_status'] == 'invalid_receipts'
    assert outcome['unknown_usage_calls'] is None and outcome['total_estimated_uncached_cny'] is None
    assert not outcome['report_available'] and not outcome['semantic_approval']


def test_first_request_content_drift_stops_before_transport(tmp_path, monkeypatch, environment):
    original = runner.prepare_frozen_application
    def changed(**kwargs):
        prepared = original(**kwargs)
        first = prepared.first_request
        changed_message = replace(first.messages[-1], content=first.messages[-1].content + ' changed')
        return replace(prepared, first_request=replace(first, messages=(*first.messages[:-1], changed_message)))
    monkeypatch.setattr(runner, 'prepare_frozen_application', changed)
    sent = scripted_child(monkeypatch)
    outcome = runner.run(execution_arguments(tmp_path))
    assert not sent and not outcome['first_request_matched']
    assert not outcome['report_available'] and outcome['status'] == 'rejected'
    assert outcome['reserved_calls'] == 0 and Decimal(outcome['total_estimated_uncached_cny']) == 0


def test_bad_ci_stops_before_credentials_or_output(tmp_path, monkeypatch, environment):
    def rejected(ci):
        raise ValueError('exact_sha_public_ci_required')
    monkeypatch.setattr(runner, 'verify_public_ci', rejected)
    with pytest.raises(ValueError, match='exact_sha_public_ci_required'):
        runner.run(execution_arguments(tmp_path))
    assert environment == [] and not tmp_path.joinpath('runs').exists()


def test_product_live_gate_still_precedes_all_preparation(monkeypatch):
    from scripts import run_native_coach_product as product
    def denied(*args, **kwargs):
        raise AssertionError('closed product entrypoint performed preparation')
    monkeypatch.setattr(product, 'prepare_frozen_application', denied)
    with pytest.raises(ValueError, match='native_product_semantic_qualification_required'):
        product.run(SimpleNamespace(execute=True))


def test_post_run_invalid_accounting_cannot_exit_successfully(tmp_path, monkeypatch, environment):
    sent = scripted_child(monkeypatch)
    def invalid(directory):
        raise ValueError('corrupted_receipt')
    monkeypatch.setattr(runner, 'summarize_calls', invalid)
    args = execution_arguments(tmp_path)
    outcome = runner.run(args)
    assert len(sent) == 5
    assert outcome['status'] == 'failed' and outcome['accounting_status'] == 'invalid_receipts'
    assert outcome['application_publication_status'] == 'published' and outcome['report_available']
    assert outcome['unknown_usage_calls'] is None and outcome['total_estimated_uncached_cny'] is None
    assert not outcome['semantic_approval'] and not outcome['production_admitted']
    assert outcome == json.loads((args.output_root / 'observations' / args.run_id / 'result.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('composition', ['native', 'flash-glm-review'])
def test_existing_native_preview_uses_shared_preparation(tmp_path, environment, composition):
    from scripts import run_native_coach_product as product
    preview = product.run(arguments(tmp_path, composition=composition))
    assert preview['composition'] == composition
    assert preview['total_calls'] == 5 and preview['first_input_ceiling'] > 0
    assert not preview['production_admitted'] and not preview['semantic_approval']
    assert environment == [] and not tmp_path.joinpath('runs').exists()


@pytest.mark.parametrize('drift', ['plan', 'source_now', 'candidate'])
def test_stale_approved_preparation_stops_before_ci_credentials_or_output(tmp_path, monkeypatch, environment, drift):
    args = execution_arguments(tmp_path)
    if drift == 'plan':
        args.approval_plan_sha = '0' * 64
    elif drift == 'source_now':
        args.source_now = '2026-09-23T01:00:00+00:00'
    else:
        identity = runner.candidate_identity()
        monkeypatch.setattr(runner, 'candidate_identity', lambda: dict(identity, policy_sha256='0' * 64))
    sent = scripted_child(monkeypatch)
    with pytest.raises(ValueError, match='approved_preparation_mismatch'):
        runner.run(args)
    assert not sent and environment == [] and not tmp_path.joinpath('runs').exists()


def test_execution_requires_fixed_preview_time_before_credentials(tmp_path, environment):
    args = arguments(tmp_path, execute=True, source_now=None, approval_plan_sha='0' * 64)
    with pytest.raises(ValueError, match='execution_arguments_required'):
        runner.run(args)
    assert environment == [] and not tmp_path.joinpath('runs').exists()


def test_loaded_preparation_drift_is_recorded_without_transport(tmp_path, monkeypatch, environment):
    args = execution_arguments(tmp_path)
    load = runner.load_role_settings
    identity = runner.candidate_identity()
    def changed_credentials(path):
        values = load(path)
        monkeypatch.setattr(runner, 'candidate_identity', lambda: dict(identity, policy_sha256='0' * 64))
        return values
    monkeypatch.setattr(runner, 'load_role_settings', changed_credentials)
    sent = scripted_child(monkeypatch)
    outcome = runner.run(args)
    assert outcome['status'] == 'failed' and not sent
    assert not outcome['first_request_matched'] and outcome['reserved_calls'] == 0
    assert outcome['declared_approved_preparation_plan_sha256'] == args.approval_plan_sha
    directory = args.output_root / 'observations' / args.run_id
    changed_plan = json.loads((directory / 'plan.json').read_text(encoding='utf-8'))
    assert changed_plan['preparation_plan_sha256'] != args.approval_plan_sha
    assert (directory / 'first-request.json').exists() and (directory / 'result.json').exists()


def test_default_preview_needs_no_execution_arguments(tmp_path, environment):
    plan = runner.run(arguments(tmp_path, run_id='', ci_run='', env_file=None, source_now=None))
    assert plan['run_id'] == 'role-development-preview' and plan['mode'] == 'preview'
    assert plan['head_sha'] is None and plan['provider_requests'] == 0
    assert datetime.fromisoformat(plan['source_now']).utcoffset() is not None
    assert len(plan['preparation_plan_sha256']) == 64
    assert environment == [] and not tmp_path.joinpath('runs').exists()

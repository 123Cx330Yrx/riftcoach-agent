from pathlib import Path

import pytest

from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.identity import LegacyRuntimeIdentityResolver
from app.runtime.models import RuntimePublicationStatus, RuntimeStatus
from app.runtime.runtime import AgentRuntimeV1, RuntimeExecutionFactory
from app.skills.catalog import SkillCatalog
from tests.test_agent_runtime import FactoryProbe, RuntimeProvider, _catalog_with_fallback, _request, _version_mismatch_request


def runtime(tmp_path, factory, descriptor=None, catalog=None):
    probe = FactoryProbe()
    return AgentRuntimeV1(
        runs_root=tmp_path, catalog=catalog or SkillCatalog.from_directory('skills'),
        provider=descriptor or RuntimeProvider(), provider_factory=factory,
        execution_factory=RuntimeExecutionFactory(
            knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
            evaluator_factory=probe.evaluator_factory, reviser_factory=probe.reviser_factory,
        ), prompt_program_resolver=LegacyRuntimeIdentityResolver(),
    )


def test_each_run_gets_one_provider_and_failed_run_does_not_poison_next(tmp_path):
    providers = {}
    def factory(run_id):
        value = RuntimeProvider(behavior='evaluation_failure' if run_id == 'first' else 'success')
        providers[run_id] = value
        return value
    descriptor = RuntimeProvider()
    app = runtime(tmp_path, factory, descriptor, _catalog_with_fallback(False))
    def request(run_id):
        req = _request(run_id)
        return req.model_copy(update={'policy': req.policy.model_copy(update={'allow_deterministic_fallback': False})})
    first = app.run(request('first'))
    second = app.run(request('second'))
    assert first.publication_status is RuntimePublicationStatus.REJECTED
    assert first.output.report is None
    assert second.runtime_status is RuntimeStatus.COMPLETED
    assert second.publication_status is RuntimePublicationStatus.PUBLISHED
    assert providers['first'] is not providers['second']
    assert [r.metadata.get('agent_loop_iteration') for r in providers['second'].requests] == [1, 2, None]
    assert not descriptor.requests


@pytest.mark.parametrize('field,value', [('provider_name','other'), ('model_name','other'), ('thinking_profile_id','wrong')])
def test_mismatched_per_run_identity_fails_before_transport(tmp_path, field, value):
    provider = RuntimeProvider()
    setattr(provider, field, value)
    app = runtime(tmp_path, lambda run_id: provider)
    assert app.run(_request('identity_mismatch')).runtime_status is RuntimeStatus.FAILED
    assert not provider.requests


def test_invalid_skill_input_does_not_construct_transport(tmp_path):
    created = []
    app = runtime(tmp_path, lambda run_id: created.append(run_id) or RuntimeProvider())
    assert app.run(_version_mismatch_request('invalid')).runtime_status is RuntimeStatus.FAILED
    assert not created


def test_factory_may_not_reuse_descriptor(tmp_path):
    descriptor = RuntimeProvider()
    app = runtime(tmp_path, lambda run_id: descriptor, descriptor)
    assert app.run(_request('descriptor_reuse')).runtime_status is RuntimeStatus.FAILED
    assert not descriptor.requests


def test_receipted_stream_factory_isolates_transport_state_without_io(tmp_path):
    from types import SimpleNamespace
    from app.runtime.receipted_provider_factory import RunScopedReceiptedProviderFactory
    settings = SimpleNamespace(model='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = RunScopedReceiptedProviderFactory(settings=settings, transport_root=tmp_path/'transport')
    first, second = factory('first'), factory('second')
    first._failed, first._calls = True, 5
    assert not second._failed and second._calls == 0 and second.last_exchange is None
    assert first._directory != second._directory
    assert second._directory == tmp_path/'transport'/'second'
    assert not (tmp_path/'transport').exists()
    for invalid in ('../outside', 'bad/run', 'bad\\run'):
        with pytest.raises(ValueError):
            factory(invalid)


def test_stream_factory_records_issued_bytes_and_refuses_duplicate_run_before_io(tmp_path, monkeypatch):
    import hashlib
    import json
    from types import SimpleNamespace
    from app.evaluation import golden_stream_bridge as bridge
    from app.evaluation.golden_journal import write_new_json
    from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage
    from app.runtime.receipted_provider_factory import RunScopedReceiptedProviderFactory
    settings = SimpleNamespace(model='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/paas/v4', api_key='offline-fixture')
    factory = RunScopedReceiptedProviderFactory(settings=settings,transport_root=tmp_path)
    sent=[]
    def child(command, raw, *, directory, **kwargs):
        sent.append(raw)
        write_new_json(directory/'result.json',dict(state='complete',transport_id=bridge.CAPACITY_TRANSPORT_ID))
        return ChatResponse(content='ok',model='glm-5.3-flash',provider='zhipu',finish_reason='stop',
            usage=TokenUsage(input_tokens=1,output_tokens=1))
    monkeypatch.setattr(bridge,'run_child',child)
    provider=factory('run')
    request=ChatRequest(messages=(ChatMessage(role=MessageRole.USER,content='offline'),),max_tokens=1,timeout_s=30)
    response=provider.chat(request)
    saved=(tmp_path/'run/request-001.json').read_bytes()
    assert saved == sent[0]
    assert hashlib.sha256(saved).hexdigest() == provider.last_exchange.receipt_request_sha256
    assert json.loads((tmp_path/'run/response-001.json').read_text())['content'] == response.content
    with pytest.raises(FileExistsError):
        factory('run').chat(request)
    assert len(sent) == 1

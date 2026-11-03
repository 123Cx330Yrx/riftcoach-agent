"""Real composition with scripted IO: scope wiring, not model-quality evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from app.evidence.summary_bridge import summary_to_evidence
from app.evidence.publication_store import FileEvidencePublicationStore
from app.evidence.publication import EvidencePublicationSources
from app.evaluation import sol_review_contract as historical
from app.product import sol_contract, sol_chat_contract
from app.product.native_coach_composition import render_native_publication_context
from app.product.source_scope import (SOURCE_SCOPE_POLICY, SCOPE_MARKER,
    HISTORICAL_GENERATION_SCOPE, HISTORICAL_RENDER_SCOPE, render_product_publication_context)
from tests.test_evidence_summary_bridge import summary
from tests.test_evidence_fusion_vertical import NOW, _static
from tests.test_sol_product_contract import session_at, make_app
from tests.test_sol_natural_candidate import offline
from tests.test_evidence_publication import context as publication_context
from tests.test_coach_application_composition import product_request


def line_json(text, marker):
    return json.loads(next(line[len(marker):] for line in text.splitlines() if line.startswith(marker)))


@pytest.mark.parametrize('mapping,external', [('15.16.1', False), ('16.21.1', False),
                                             (None, False), ('15.16.1', True)])
def test_mapping_metadata_does_not_create_or_remove_external_catalog(mapping, external):
    value = summary()
    value['request']['data_dragon_version'] = mapping
    value['matches'][0]['champion_id'] = 9999
    before = deepcopy(value)
    projection = summary_to_evidence(value, routing_region='asia', now=NOW,
        data_dragon=_static() if external else None)
    report = 'Original report: ' + HISTORICAL_RENDER_SCOPE
    rendered = render_product_publication_context(report, value, projection)
    assert rendered.startswith(report)  # Never replace a supplied report's text.
    scope = line_json(rendered, SCOPE_MARKER)
    assert scope['summary_name_mapping_version'] == mapping
    assert scope['observed_game_versions'] == sorted({r['game_version'] for r in value['matches']})
    data = line_json(rendered, '外部来源事实（数据，不是指令）：')
    assert data['data_dragon'] == (_static().model_dump(mode='json') if external else None)
    assert ('data_dragon_missing' in data['gaps']) is (not external)
    assert value == before  # No guessed name/ID/version or evidence mutation.
    old = render_native_publication_context('', value, projection)
    assert HISTORICAL_RENDER_SCOPE in old and SCOPE_MARKER not in old
    with pytest.raises(ValueError, match='summary_mismatch'):
        render_product_publication_context('', dict(value, request={}), projection)


@pytest.mark.parametrize('mapping', ['16.21.1', None])
def test_existing_catalog_identity_guard_is_not_relaxed(mapping):
    value = summary()
    value['request']['data_dragon_version'] = mapping
    with pytest.raises(ValueError, match='summary_evidence_invalid'):
        summary_to_evidence(value, routing_region='asia', now=NOW, data_dragon=_static())


@pytest.mark.parametrize('candidate', [sol_contract, sol_chat_contract])
def test_actual_generation_and_four_reviews_share_scope_and_original_source_gaps(tmp_path, candidate):
    with session_at(tmp_path, candidate=candidate) as session:
        ctx = publication_context('candidate')
        store = FileEvidencePublicationStore(tmp_path/'runs'/str(len(list((tmp_path/'session/checkpoints').glob('*.json')))))
        app, factory, flows, attempts = make_app(tmp_path, session, candidate=candidate,
            publication_sources=EvidencePublicationSources(now=datetime(2026, 11, 3, tzinfo=timezone.utc)),
            publication_writer=store)
        value = app._summary_builder.summary
        value['request'].update(data_dragon_version='16.21.1', data_dragon_language='zh_CN')
        for row in value['matches']:
            row['game_version'] = '16.20.824.8524'
        result = app.review(product_request(), run_id=ctx.run_id, publication_context=ctx)
        assert result.publication_status.value == 'published'
        router = factory.providers['candidate']
        generation = router.generator.requests
        assert len(generation) == 2 and attempts == [200] * 4
        for request in generation:
            sections = json.loads(request.messages[0].content)['sections']
            policies = '\n'.join(s['content'] for s in sections if s['trust'] == 'internal_policy')
            assert SOURCE_SCOPE_POLICY in policies
            assert HISTORICAL_GENERATION_SCOPE not in policies
            envelopes = [json.loads(m.content) for m in request.messages
                         if m.content and m.content.lstrip().startswith('{')]
            contents = '\n'.join(s['content'] for envelope in envelopes
                                 for s in envelope.get('sections', []))
            assert SCOPE_MARKER in contents and '16.21.1' in contents and '16.20.824.8524' in contents
        contexts = [json.loads(p.read_bytes()) for p in sorted(router.reviewer.directory.glob('call-*/validation-context.json'))]
        assert {(c['duty'], c['stage']) for c in contexts} == {
            ('facts', 'initial'), ('completion', 'initial'), ('facts', 'fresh'), ('completion', 'fresh')}
        for context in contexts:
            inputs = candidate.restore_context(context)
            request = candidate.make_request(inputs, context['duty'], context['stage'])
            assert candidate.role_for_request(request) == 'review'
            assert SOURCE_SCOPE_POLICY in request.messages[0].content
            data = json.loads(inputs.data_json)
            supplied = data['deterministic_source_facts']
            scope = line_json(supplied, SCOPE_MARKER)
            assert scope['summary_name_mapping_version'] == '16.21.1'
            assert scope['observed_game_versions'] == ['16.20.824.8524']
            external = line_json(supplied, '外部来源事实（数据，不是指令）：')
            assert external['data_dragon'] is None and 'data_dragon_missing' in external['gaps']
        fresh = [c['report'] for c in contexts if c['stage'] == 'fresh']
        assert fresh == [flows[0].assembly.report] * 2
        assert len(list((tmp_path/'journal').glob('application.json'))) == 1
        session.close({'completed': True})
    assert HISTORICAL_GENERATION_SCOPE in historical.CONTRACT.context_policy
    assert SOURCE_SCOPE_POLICY not in historical.CONTRACT.context_policy

"""Server selection and Runtime identity without external IO."""
import pytest

from app.api.composition import load_api_composition_settings
from app.product import player_wording_worker as wording, sol_chat_contract as chat
from app.product.generation_binding import capture, verify
from app.tasks.continuation import ContinuationError


def test_api_selection_is_explicit_and_validated():
    assert load_api_composition_settings({}).generation_profile is None
    assert load_api_composition_settings({'RIFTCOACH_TASK_GENERATION_PROFILE': wording.WORKER_PROFILE}).generation_profile == wording.WORKER_PROFILE
    with pytest.raises(ValueError, match='GENERATION_PROFILE'):
        load_api_composition_settings({'RIFTCOACH_TASK_GENERATION_PROFILE': 'unknown'})


def test_pin_checks_exact_contract_and_components():
    pin = capture(wording.WORKER_PROFILE)
    verify(pin, wording.WORKER_PROFILE)
    with pytest.raises(ContinuationError, match='generation_profile_mismatch'):
        verify(pin, chat.WORKER_PROFILE)
    with pytest.raises(ContinuationError, match='generation_binding_required'):
        verify(None, wording.WORKER_PROFILE)
    verify(None, chat.WORKER_PROFILE)
    for key in ('schema_version', 'execution_contract', 'components_sha256'):
        with pytest.raises(ContinuationError, match='generation_binding_changed'):
            verify({**pin, key: 'changed'}, wording.WORKER_PROFILE)


def test_runtime_rejects_parent_context_for_new_contract():
    from app.runtime.coach_contract import require_coach_context, require_coach_contract
    from app.product.review_purpose import ProductContextBuilder
    from app.runtime.composition import RuntimeCompositionRoot
    from tests.test_context_builder import validated_execution, demo_summary, demo_report
    assert require_coach_contract(wording.CONTRACT) is wording.CONTRACT
    assert wording.CONTRACT.context_policy != chat.CONTRACT.context_policy
    root = RuntimeCompositionRoot.from_directories(skills_root=wording.ASSETS/'skills',
        prompt_programs_root=wording.ASSETS/'prompt_programs', coach_contract=wording.CONTRACT)
    assert root.prompt_program_resolver.verify_all()
    execution = validated_execution(utterance='复盘最近几局', run_id='wording-context',
        payload={'player_summary': demo_summary(), 'deterministic_report': demo_report(), 'focus': 'overall'})
    current = ProductContextBuilder(coach_contract=wording.CONTRACT, purpose='unbound').build(execution)
    previous = ProductContextBuilder(coach_contract=chat.CONTRACT, purpose='unbound').build(execution)
    require_coach_context(current, wording.CONTRACT)
    with pytest.raises(ValueError, match='bound trusted policy'):
        require_coach_context(previous, wording.CONTRACT)


@pytest.mark.parametrize('mode', ['pass', 'repair'])
def test_actual_wording_runtime_resumes_without_repeating_generation(tmp_path, mode):
    import json
    from app.evaluation.sol_natural_session import SessionPaused
    from app.product.player_wording_contract import WORDING
    from app.runtime.store import RuntimeTraceStore
    from tests.test_sol_product_contract import session_at, make_app, current_pins
    from tests.test_natural_duty_candidate import run
    with session_at(tmp_path, candidate=wording, max_new_models=3) as session:
        app, factory, _, attempts = make_app(tmp_path, session, candidate=wording, mode=mode)
        with pytest.raises(SessionPaused, match='session_model_boundary'):
            run(app)
        assert attempts == [200]
        for req in factory.providers['candidate'].generator.requests:
            assert any(WORDING in m.content for m in req.messages if m.content)
    with session_at(tmp_path, candidate=wording, pins=current_pins(tmp_path)) as session:
        app, factory, _, attempts = make_app(tmp_path, session, candidate=wording, mode=mode)
        result = run(app)
        assert result.publication_status.value == 'published'
        assert factory.providers['candidate'].generator.requests == []
        assert attempts == ([200] if mode == 'pass' else [200, 200, 200])
        for path in (tmp_path/'transport/candidate/review').glob('call-*/validation-context.json'):
            value = json.loads(path.read_bytes())
            inputs = chat.restore_context(value)
            assert wording.request_bytes(wording.make_request(inputs, value['duty'], value['stage'])) == chat.request_bytes(chat.make_request(inputs, value['duty'], value['stage']))

"""Concrete dual transports use task ordinals without performing role dispatch."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.providers.errors import ProviderResponseError, ProviderTimeoutError
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage
from app.runtime.receipted_provider_factory import RoleReceiptedStreamProvider


def settings(model):
    return SimpleNamespace(model=model, base_url="https://open.bigmodel.cn/api/paas/v4", api_key="offline-fixture")


def request(phase="generation"):
    return ChatRequest(messages=(ChatMessage(role=MessageRole.USER, content="offline"),),
        max_tokens=32, timeout_s=13, metadata={"phase": phase})


def transports(tmp_path, run_id="run"):
    directory = tmp_path / run_id
    return tuple(RoleReceiptedStreamProvider(settings=settings(model), directory=directory / name,
        task_directory=directory, transport_id=transport_id) for name, model, transport_id in (
            ("generation", "glm-5.3-flash", bridge.CAPACITY_TRANSPORT_ID),
            ("review", "glm-5.3", bridge.REVIEW_MODEL_TRANSPORT_ID)))


def successful_child(sent):
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        sent.append(dict(raw=raw, directory=directory, timeout_s=timeout_s,
            model=environ["LLM_MODEL"], transport_id=transport_id))
        assert command[command.index("--transport-id") + 1] == transport_id
        write_new_json(directory / "result.json", dict(state="complete", transport_id=transport_id))
        return ChatResponse(content="offline response", model=environ["LLM_MODEL"], provider="zhipu",
            finish_reason="stop", usage=TokenUsage(input_tokens=11, output_tokens=7))
    return child


def test_interleaved_models_preserve_exact_request_response_and_task_ordinal(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_child", successful_child(sent))
    generator, reviewer = transports(tmp_path)
    assert not tmp_path.joinpath("run").exists()
    for ordinal, provider in enumerate((generator, generator, reviewer, generator, reviewer), start=1):
        req = request()
        response = provider.chat_at_ordinal(req, ordinal=ordinal)
        binding = json.loads((tmp_path / f"run/call-{ordinal:03d}.json").read_text())
        terminal = json.loads((tmp_path / f"run/call-result-{ordinal:03d}.json").read_text())
        raw_directory = tmp_path / "run" / binding["raw_directory"]
        request_raw = (raw_directory / f"request-{ordinal:03d}.json").read_bytes()
        response_raw = (raw_directory / f"response-{ordinal:03d}.json").read_bytes()
        reservation = json.loads((raw_directory / f"stream-{ordinal:03d}/reservation.json").read_text())
        assert request_raw == sent[-1]["raw"] == bridge.validate_request(req, transport_id=provider.transport_id)
        assert binding["request_sha256"] == reservation["request_sha256"] == hashlib.sha256(request_raw).hexdigest()
        assert binding["ordinal"] == reservation["ordinal"] == ordinal
        assert binding["model"] == sent[-1]["model"] == provider.model_name
        assert binding["thinking_profile_id"] == provider.thinking_profile_id
        assert binding["transport_id"] == sent[-1]["transport_id"] == provider.transport_id
        assert terminal["response_sha256"] == hashlib.sha256(response_raw).hexdigest()
        assert (terminal["input_tokens"], terminal["output_tokens"]) == (11, 7)
        assert provider.last_exchange.response is response
        assert provider.last_exchange.issued_request is req
        assert provider.last_exchange.receipt_request_sha256 == binding["request_sha256"]
        assert sent[-1]["timeout_s"] == 13
    assert generator._calls == 4 and reviewer._calls == 5
    assert [item["directory"].name for item in sent] == [f"stream-{i:03d}" for i in range(1, 6)]


def test_same_task_ordinal_cannot_be_replayed_through_other_model(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_child", successful_child(sent))
    generator, reviewer = transports(tmp_path)
    generator.chat_at_ordinal(request(), ordinal=1)
    with pytest.raises(FileExistsError):
        reviewer.chat_at_ordinal(request(), ordinal=1)
    duplicate_generator, _ = transports(tmp_path)
    with pytest.raises(FileExistsError):
        duplicate_generator.chat_at_ordinal(request(), ordinal=1)
    assert len(sent) == 1


@pytest.mark.parametrize("field,value", [
    ("model_name", "other"), ("provider_name", "other"), ("thinking_profile_id", "other"),
    ("transport_id", bridge.CAPACITY_TRANSPORT_ID), ("sdk_max_retries", False),
    ("runtime_profile", object()),
])
def test_mutated_transport_identity_refused_before_files_or_io(tmp_path, monkeypatch, field, value):
    _, reviewer = transports(tmp_path)
    setattr(reviewer, field, value)
    with pytest.raises(ProviderResponseError, match="role_transport_identity_mismatch"):
        reviewer.chat_at_ordinal(request(), ordinal=1)
    assert not tmp_path.joinpath("run").exists()


@pytest.mark.parametrize("ordinal", [True, 0, -1, 10, 1.0, "1"])
def test_invalid_external_ordinal_cannot_open_transport(tmp_path, ordinal):
    generator, _ = transports(tmp_path)
    with pytest.raises(ProviderResponseError, match="role_transport_ordinal_invalid"):
        generator.chat_at_ordinal(request(), ordinal=ordinal)
    assert not tmp_path.joinpath("run").exists()


def test_direct_chat_requires_router_ordinal(tmp_path):
    generator, _ = transports(tmp_path)
    with pytest.raises(ProviderResponseError, match="role_transport_ordinal_required"):
        generator.chat(request())
    assert not tmp_path.joinpath("run").exists()


@pytest.mark.parametrize("defect", ["request_sha256", "ordinal", "transport_id", "model", "thinking_profile_id", "result_missing", "result_malformed", "model_missing"])
def test_bad_receipt_stops_and_keeps_returned_usage_without_accepted_exchange(tmp_path, monkeypatch, defect):
    sent = []
    child = successful_child(sent)
    def broken(*args, **kwargs):
        response = child(*args, **kwargs)
        directory = kwargs["directory"]
        if defect == "result_missing":
            (directory / "result.json").unlink()
        elif defect == "result_malformed":
            (directory / "result.json").write_text("not-json", encoding="utf-8")
        else:
            path = directory / "reservation.json"
            data = json.loads(path.read_text())
            if defect == "model_missing":
                del data["model"]
            else:
                data[defect] = True if defect == "ordinal" else "incorrect"
            path.write_text(json.dumps(data), encoding="utf-8")
        return response
    monkeypatch.setattr(bridge, "run_child", broken)
    _, reviewer = transports(tmp_path)
    with pytest.raises(ProviderResponseError, match="integrated_transport_receipt_invalid") as failure:
        reviewer.chat_at_ordinal(request(), ordinal=3)
    assert reviewer.last_exchange is None
    assert failure.value.observed_response is reviewer.last_response
    assert failure.value.observed_response.usage.input_tokens == 11
    assert json.loads((tmp_path / "run/review/response-003.json").read_text())["usage"]["output_tokens"] == 7
    with pytest.raises(ProviderResponseError, match="stream_bridge_exhausted"):
        reviewer.chat_at_ordinal(request(), ordinal=5)
    assert len(sent) == 1


def test_wrong_response_model_is_not_relabelled_and_usage_remains_observable(tmp_path, monkeypatch):
    sent = []
    child = successful_child(sent)
    monkeypatch.setattr(bridge, "run_child", lambda *a, **k: replace(child(*a, **k), model="glm-5.3-flash"))
    _, reviewer = transports(tmp_path)
    with pytest.raises(ProviderResponseError, match="response_identity_mismatch") as failure:
        reviewer.chat_at_ordinal(request(), ordinal=3)
    assert failure.value.observed_response.model == "glm-5.3-flash"
    assert reviewer.last_exchange is None


def test_transport_timeout_preserves_reservation_and_never_retries(tmp_path, monkeypatch):
    sent = []
    def timeout(command, raw, *, directory, timeout_s, **kwargs):
        sent.append((raw, timeout_s))
        write_new_json(directory / "result.json", dict(state="deadline", transport_id=kwargs["transport_id"]))
        raise ProviderTimeoutError(provider="zhipu", code="stream_deadline")
    monkeypatch.setattr(bridge, "run_child", timeout)
    _, reviewer = transports(tmp_path)
    with pytest.raises(ProviderTimeoutError, match="stream_deadline"):
        reviewer.chat_at_ordinal(request(), ordinal=3)
    assert reviewer._calls == 3 and reviewer.last_exchange is None and reviewer.last_response is None
    assert (tmp_path / "run/call-003.json").exists()
    assert not (tmp_path / "run/review/response-003.json").exists()
    with pytest.raises(ProviderResponseError, match="stream_bridge_exhausted"):
        reviewer.chat_at_ordinal(request(), ordinal=4)
    assert len(sent) == 1 and sent[0][1] == 13


def test_factory_builds_actual_router_and_reuses_task_ordinals_across_roles(tmp_path, monkeypatch):
    from app.evaluation.golden_explicit_source_projection import VERSION
    from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
    from app.runtime.reviewer_roles import ROLE_COMPOSITION_ID, RoleRoutedProvider

    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings("glm-5.3-flash"),
        reviewer_settings=settings("glm-5.3"), transport_root=tmp_path / "transport")
    assert factory.descriptor.model_name == ROLE_COMPOSITION_ID
    first, second = factory("first"), factory("second")
    assert isinstance(first, RoleRoutedProvider)
    assert not tmp_path.joinpath("transport").exists()
    sent = []
    monkeypatch.setattr(bridge, "run_child", successful_child(sent))
    metadata = ({"agent_loop_iteration": 1},
        {"review_phase": "native_business_review", "harness_step": "evaluate", "source_projection": VERSION},
        {"review_phase": "native_business_revision", "harness_step": "revise", "source_projection": VERSION})
    for item in metadata:
        from tests.test_role_budget_failures import request as routed_request
        role = 'generation' if 'agent_loop_iteration' in item else 'revision' if item['harness_step']=='revise' else 'review'
        first.chat(replace(routed_request(role), metadata=item))
    assert first._calls == 3 and second._calls == 0
    assert [item["model"] for item in sent] == ["glm-5.3-flash", "glm-5.3", "glm-5.3-flash"]
    bindings = [json.loads((tmp_path / f"transport/first/call-{i:03d}.json").read_text()) for i in range(1, 4)]
    assert [item["role"] for item in bindings] == ["generation", "review", "revision"]
    assert [item["ordinal"] for item in bindings] == [1, 2, 3]
    assert first.last_exchange.response.model == "glm-5.3-flash"
    for invalid in ("../outside", "bad/run", "bad\\run"):
        with pytest.raises(ValueError):
            factory(invalid)


def test_explicit_role_must_match_the_concrete_model(tmp_path):
    _, reviewer = transports(tmp_path)
    with pytest.raises(ProviderResponseError, match="role_transport_identity_mismatch"):
        reviewer.chat_at_ordinal(request(), ordinal=1, role="revision")
    assert not tmp_path.joinpath("run").exists()

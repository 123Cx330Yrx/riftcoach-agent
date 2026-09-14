"""Expanded high profile must reach the SDK and remain explicitly bounded."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import pytest
from app.evaluation import golden_stream_bridge as m
from app.runtime.coach_contract import EXPANDED_COACH_CONTRACT as CONTRACT, SCOPE_V4_COACH_CONTRACT
from app.providers.errors import ProviderResponseError
from tests.test_golden_stream_bridge import request
from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage


def test_budget_identity_assets_and_old_snapshot():
    from app.runtime.composition import RuntimeCompositionRoot
    assert SCOPE_V4_COACH_CONTRACT.snapshot().sha256 == "56fe4d8321564c6ffbc467a2cfbb8dc683515b60511bd9096195763a6d796ef8"
    limits=CONTRACT.descriptor()
    assert (limits["max_calls"],limits["max_output_tokens"],limits["request_timeout_s"],limits["total_tokens"])==(5,16384,180,401920)
    assert limits["reasoning_effort"]=="high"
    root=Path("examples/runtime_profiles/flash_v2_golden_expanded")
    runtime=RuntimeCompositionRoot.from_directories(skills_root=root/"skills",prompt_programs_root=root/"prompt_programs",coach_contract=CONTRACT)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version=="1.9.0"

@pytest.mark.parametrize("cap,seconds",[(16385,180),(16384,181)])
def test_expanded_still_rejects_oversized_requests(cap,seconds):
    with pytest.raises(ProviderResponseError):
        m.validate_request(replace(request(),max_tokens=cap,timeout_s=seconds),transport_id=m.EXPANDED_TRANSPORT_ID)

def test_old_transport_does_not_accept_new_budget():
    with pytest.raises(ProviderResponseError):m.validate_request(replace(request(),max_tokens=16384,timeout_s=180))

def test_collection_after_90_seconds_and_usage_above_8192(tmp_path):
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    raw=ClosableStream([chunk(content="complete",finish_reason="stop"),chunk(raw_usage=usage(10,10000))])
    client=FakeClient(raw)
    provider=ZhipuProvider.from_candidate_profile(client=client,model="glm-5.3-flash",profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    response=m.collect(replace(request(),max_tokens=16384,timeout_s=180),
        lambda r,h:provider.stream_adapter(evaluation_request_policy=CONTRACT.request_policy).stream_session(r,include_usage_tail=True),
        directory=tmp_path,started=0,deadline=180,clock=lambda:120,transport_id=m.EXPANDED_TRANSPORT_ID)
    assert response.usage.output_tokens==10000 and raw.closed
    sent=client.completions.calls[0]
    assert sent["max_tokens"]==16384 and sent["extra_body"]["reasoning_effort"]=="high"
    progress=json.loads((tmp_path/"progress.json").read_text())
    assert progress["terminal_ms"]==120000 and progress["output_tokens"]==10000

@pytest.mark.parametrize("tokens,finish",[(16385,"stop"),(16384,"length")])
def test_overbudget_or_incomplete_still_rejected(tmp_path,tokens,finish):
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    raw=ClosableStream([chunk(content="partial",finish_reason=finish),chunk(raw_usage=usage(10,tokens))])
    provider=ZhipuProvider.from_candidate_profile(client=FakeClient(raw),model="glm-5.3-flash",profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    with pytest.raises(Exception):m.collect(replace(request(),max_tokens=16384,timeout_s=180),
        lambda r,h:provider.stream_adapter(evaluation_request_policy=CONTRACT.request_policy).stream_session(r,include_usage_tail=True),
        directory=tmp_path,started=0,deadline=180,clock=lambda:1,transport_id=m.EXPANDED_TRANSPORT_ID)
    assert raw.closed

def test_actual_policy_budget_and_worker_sdk_chain(tmp_path):
    from app.runtime.coach_budget import CoachBudgetedProvider
    from app.tools.adapters.llm import build_llm_tools
    from app.tools.registry import ToolRegistry
    from app.tools.runtime import ToolRuntime
    from app.harness.adapters import _chat_response
    import app.evaluation.golden_stream_bridge as bridge
    # Child runs the real worker and SDK mapping; only network client is fake.
    code="""import sys,openai
from pathlib import Path
from app.evaluation.golden_stream_bridge import worker,EXPANDED_TRANSPORT_ID
from tests.test_zhipu_stream_adapter import FakeClient,ClosableStream,chunk,usage
raw=ClosableStream([chunk(content='complete',finish_reason='stop'),chunk(raw_usage=usage(10,10000))])
client=FakeClient(raw)
def close():
 assert raw.closed
 assert client.completions.calls[0]['max_tokens']==16384
 assert client.completions.calls[0]['extra_body']['reasoning_effort']=='high'
client.close=close
openai.OpenAI=lambda **kwargs:client
worker(Path(DIRECTORY),float(sys.argv[-3]),float(sys.argv[-1]),EXPANDED_TRANSPORT_ID)
""".replace("DIRECTORY",repr(str(tmp_path)))
    environ=dict(os.environ,LLM_PROVIDER="zhipu",LLM_MODEL="glm-5.3-flash",LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4",LLM_API_KEY="fixture")
    class Offline:
        provider_name="zhipu"; model_name="glm-5.3-flash"
        capabilities=bridge.GoldenProcessStreamProvider.capabilities
        thinking_profile_id=bridge.GoldenProcessStreamProvider.thinking_profile_id
        sdk_max_retries=0; runtime_profile=None
        def chat(self,r):
            assert r.max_tokens==16384 and r.timeout_s==180
            return m.run_child([sys.executable,"-B","-c",code],m.validate_request(r,transport_id=m.EXPANDED_TRANSPORT_ID),directory=tmp_path,
                              timeout_s=r.timeout_s,environ=environ,transport_id=m.EXPANDED_TRANSPORT_ID)
    registry=ToolRegistry()
    for definition in build_llm_tools(CoachBudgetedProvider(Offline(),coach_contract=CONTRACT),request_policy=CONTRACT.request_policy):registry.register(definition)
    result=_chat_response(ToolRuntime(registry),system_prompt="test",user_prompt="test",temperature=1.0,harness_step="evaluate")
    assert result.content=="complete" and result.usage.output_tokens==10000

def test_other_policy_cannot_gain_expanded_cap():
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    with pytest.raises(ValueError,match="8192"):
        _issue_candidate_evaluation_request_policy(policy_id="other",version="1.0.0",provider_id="zhipu",model="glm-5.3-flash",
            agent_timeout_s=240,llm_tool_timeout_s=240,transport_timeout_s=270,max_output_tokens=16384,temperature=1,top_p=.95)

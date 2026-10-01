import json
from dataclasses import replace
from types import SimpleNamespace as NS
from pathlib import Path
import pytest

from app.evaluation.golden_numeric_evidence_v3 import numeric_support
from app.evaluation.golden_evidence_scope_v3 import expand_evidence, table_anchor_valid
from tests.test_golden_evidence_scope import wire
from tests.test_golden_fact_candidate import summary
from app.evaluation.golden_fact_candidate import fact_pack


def pack_rows(values, roles=None, excluded=None):
    facts, provenance = {}, {}
    for i, value in enumerate(values):
        key = f"facts:recent_match:{i:02}"
        facts[key] = dict(role=roles[i] if roles else "MIDDLE", cs_per_min=value,
                          included_in_aggregate=i != excluded, queue_id=420)
        provenance[key] = {"source_path": f"/matches/{i}"}
    return dict(facts=facts, provenance=provenance)


def check(quote, pack, refs=None):
    return numeric_support(NS(quote=quote, evidence_refs=refs or list(pack["facts"])), pack)


def test_cited_role_mean_median_and_count():
    pack = pack_rows([8.95, 9.64, 8.38, 8.66])
    rows = check("4 局补刀均值 8.91，中位数 8.8", pack)
    assert all(row["supported"] for row in rows)
    assert "cited_role_median" in {c["op"] for row in rows for c in row["candidates"]}
    assert not check("均值 8.91", pack, ["facts:recent_match:00"])[0]["supported"]
    assert not check("均值 8.91", pack_rows([8.95,9.64,8.38,8.66], roles=["MIDDLE","UTILITY","TOP","JUNGLE"]))[0]["supported"]


def test_excluded_missing_invalid_and_duplicate_refs_do_not_distort_mean():
    pack = pack_rows([2,4,100,None], excluded=2)
    assert check("均值 3", pack)[0]["supported"]
    assert not check("均值 35.33", pack)[0]["supported"]
    assert not check("均值 2", pack_rows([None,4]))[0]["supported"]
    refs=["facts:recent_match:00", "facts:recent_match:01", "facts:recent_match:00"]
    assert check("均值 3",pack,refs)[0]["supported"]


def test_queue_identifier_cannot_be_supported_by_coincidental_metric_or_request():
    pack = pack_rows([999])
    assert check("队列 420",pack)[0]["supported"]
    assert not check("队列 999",pack)[0]["supported"]
    assert not check("队列 420，补刀 420",pack)[0]["supported"]
    pack["facts"]["facts:scope"]={"request":{"queue":420}}
    assert not check("队列 420",pack,["facts:scope"])[0]["supported"]


def test_table_anchor_requires_a_preceding_table():
    value, report=wire("上表差异只表示表中结果",["scope:limits"])
    claim=value["audits"][1]["claims"][0]
    claim.update(claim_kind="inference",scope="selected_sample",scope_anchor="上表")
    with pytest.raises(ValueError,match="table_scope_antecedent_missing"):
        expand_evidence(json.dumps(value),report,fact_pack(summary()))
    assert table_anchor_valid(NS(**claim),"| 指标 | 值 |\n|---|---|\n| 补刀 | 3 |\n\n"+report)
    assert not table_anchor_valid(NS(**claim),report+"\n\n| 指标 | 值 |")


@pytest.mark.parametrize("transport,seconds,cap,event_limit",[
    ("golden-process-stream-high-16384-v1",180,16384,32768),
    ("golden-process-stream-high-32768-v1",300,32768,65536),
])
def test_full_stream_survives_progress_event_16385(tmp_path,monkeypatch,transport,seconds,cap,event_limit):
    from app.evaluation import golden_stream_bridge as bridge
    from app.runtime.coach_contract import EXPANDED_COACH_CONTRACT,CAPACITY_COACH_CONTRACT
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    from tests.test_zhipu_stream_adapter import FakeClient,ClosableStream,chunk,usage
    from tests.test_golden_stream_bridge import request
    raw=ClosableStream([chunk(reasoning="r") for _ in range(17000)]+[chunk(content="complete",finish_reason="stop"),chunk(raw_usage=usage(10,10000))])
    provider=ZhipuProvider.from_candidate_profile(client=FakeClient(raw),model="glm-5.3-flash",profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    contract=CAPACITY_COACH_CONTRACT if cap==32768 else EXPANDED_COACH_CONTRACT
    observed=[]
    monkeypatch.setattr(bridge,"write_progress",lambda path,v: observed.append(v.model_dump()))
    response=bridge.collect(replace(request(),max_tokens=cap,timeout_s=seconds),
        lambda r,h:provider.stream_adapter(evaluation_request_policy=contract.request_policy).stream_session(r,include_usage_tail=True),
        directory=tmp_path,started=0,deadline=seconds,clock=lambda:1,transport_id=transport)
    assert response.content=="complete" and raw.closed
    assert observed[-1]["state"]=="complete" and observed[-1]["events"]==17002
    cls=bridge.CapacityBridgeObservation if cap==32768 else bridge.ExpandedBridgeObservation
    with pytest.raises(ValueError): cls(events=event_limit+1)


def test_new_assets_and_old_capacity_snapshot():
    from app.runtime.coach_contract import EVIDENCE_V3_COACH_CONTRACT as new,CAPACITY_COACH_CONTRACT as old
    from app.runtime.composition import RuntimeCompositionRoot
    assert old.snapshot().sha256=="d5a7a36859be4973fa13b0aa260d9707b72a607b6e7086c2e5e0510a23d6e1bf"
    for key in ("total_tokens","max_calls","max_output_tokens","request_timeout_s","execution_timeout_s"):
        assert new.descriptor()[key]==old.descriptor()[key]
    root=Path("examples/runtime_profiles/flash_v2_golden_evidence_v3")
    runtime=RuntimeCompositionRoot.from_directories(skills_root=root/"skills",prompt_programs_root=root/"prompt_programs",coach_contract=new)
    assert runtime.prompt_program_resolver.verify_all()[0].evaluation_contract_version=="1.14.0"

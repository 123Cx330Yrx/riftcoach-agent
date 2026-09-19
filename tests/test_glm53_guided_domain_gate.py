from pathlib import Path

from app.evaluation.glm53_guided_domain_assets import admit_guided_domain_assets
from app.evaluation.glm53_guided_domain_gate import canonical_result_bytes, run_guided_domain
from tests.test_coaching_retrieval_development_chain import ScriptedCoach


ROOT = Path(__file__).resolve().parents[1]


def test_guided_v4_offline_runner_covers_four_cases_without_network(tmp_path):
    bundle = admit_guided_domain_assets(project_root=ROOT)
    result = run_guided_domain(
        bundle=bundle,
        implementation_sha="31f508947af3a1b43266b6229e7d74d83d484e20",
        provider=ScriptedCoach(),
        project_root=ROOT,
        runs_root=tmp_path,
        confirm_real_call=False,
        evidence_origin="offline_fake",
    )
    assert result["evidence_origin"] == "offline_fake"
    assert result["network_used"] is False
    assert len(result["cases"]) == 4
    assert result["candidate_registered"] is False
    assert result["production_admitted"] is False
    canonical_result_bytes(result)

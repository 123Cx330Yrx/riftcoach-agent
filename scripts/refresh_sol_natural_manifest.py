"""Refresh only the new mixed candidate's manifest; no admission or IO."""
import json
from pathlib import Path
from app.evaluation.sol_natural_contract import CONTRACT, component_fingerprints, ROOT
from app.runtime.coach_contract import coach_component_fingerprint
from app.skills.catalog import SkillCatalog
from app.prompt_program.models import PromptProgramManifest


def main(candidate=None):
    if candidate is None:
        from app.evaluation import sol_natural_contract as candidate
    from app.evaluation import sol_natural_contract, sol_necessity_contract, sol_review_contract
    from app.product import sol_contract
    if candidate not in (sol_natural_contract, sol_necessity_contract, sol_review_contract, sol_contract):
        raise ValueError('unsupported_natural_manifest')
    contract, fingerprints = candidate.CONTRACT, candidate.component_fingerprints
    root = ROOT/'examples/runtime_profiles'/('sol_necessity_v1' if candidate is sol_necessity_contract else 'sol_natural_v1')
    if candidate in (sol_review_contract, sol_contract):
        root = candidate.ASSETS
    skill = SkillCatalog.from_directory(root/'skills').get('recent-form-review')
    value = dict(schema_version='1.0', program_id='recent-form-review-coach', program_version='4.0.0',
        skill_name='recent-form-review', skill_version='0.7.0', context_contract_id='context-builder-v1',
        context_contract_version='1.0.0', evaluation_contract_id='coach_evaluation', evaluation_contract_version='4.0.0',
        component_fingerprints=[r.model_dump(mode='json') for r in
            (*fingerprints(skill), coach_component_fingerprint(contract))])
    value['program_sha256'] = PromptProgramManifest.digest_for(value)
    PromptProgramManifest.model_validate(value)
    path = root/'prompt_programs/recent-form-review/manifest.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()

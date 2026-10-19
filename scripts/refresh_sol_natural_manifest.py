"""Refresh only the new mixed candidate's manifest; no admission or IO."""
import json
from pathlib import Path
from app.evaluation.sol_natural_contract import CONTRACT, component_fingerprints, ROOT
from app.runtime.coach_contract import coach_component_fingerprint
from app.skills.catalog import SkillCatalog
from app.prompt_program.models import PromptProgramManifest


def main():
    root = ROOT/'examples/runtime_profiles/sol_natural_v1'
    skill = SkillCatalog.from_directory(root/'skills').get('recent-form-review')
    value = dict(schema_version='1.0', program_id='recent-form-review-coach', program_version='4.0.0',
        skill_name='recent-form-review', skill_version='0.7.0', context_contract_id='context-builder-v1',
        context_contract_version='1.0.0', evaluation_contract_id='coach_evaluation', evaluation_contract_version='4.0.0',
        component_fingerprints=[r.model_dump(mode='json') for r in
            (*component_fingerprints(skill), coach_component_fingerprint(CONTRACT))])
    value['program_sha256'] = PromptProgramManifest.digest_for(value)
    PromptProgramManifest.model_validate(value)
    path = root/'prompt_programs/recent-form-review/manifest.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()

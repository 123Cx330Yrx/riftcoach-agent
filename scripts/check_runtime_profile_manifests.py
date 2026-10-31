"""Bootstrap current consumer profiles without providers, keys or model IO.

Historical frozen execution checkouts and archived qualification inventories
are deliberately outside this current-source consistency check.
"""
from pathlib import Path


def check() -> int:
    from app.runtime import coach_contract as coach
    from app.evaluation import natural_duty_contract, sol_natural_contract, sol_necessity_contract, sol_review_contract
    from app.product import sol_contract
    from app.runtime.composition import RuntimeCompositionRoot

    profiles = (
        ('flash_v2_native', coach.NATIVE_COACH_CONTRACT),
        ('flash_glm_review_v1', coach.ROLE_COACH_CONTRACT),
        ('flash_glm_coarse_v1', coach.COARSE_ROLE_COACH_CONTRACT),
        ('flash_glm_correction_scope_v1', coach.CORRECTION_SCOPE_COACH_CONTRACT),
        ('flash_glm_boundary_examples_v1', coach.BOUNDARY_EXAMPLES_COACH_CONTRACT),
        ('natural_duty_v1', natural_duty_contract.CONTRACT),
        ('sol_natural_v1', sol_natural_contract.CONTRACT),
        ('sol_necessity_v1', sol_necessity_contract.CONTRACT),
        ('sol_review_v1', sol_review_contract.CONTRACT),
        ('sol_product_v1', sol_contract.CONTRACT),
    )
    repository = Path(__file__).resolve().parents[1]
    root = repository / 'examples/runtime_profiles'
    consumers = [('legacy-default', repository, None)] + [
        (name, root / name, contract) for name, contract in profiles
    ]
    failures = []
    for name, assets, contract in consumers:
        try:
            RuntimeCompositionRoot.from_directories(
                skills_root=assets / 'skills',
                prompt_programs_root=assets / 'prompt_programs',
                coach_contract=contract,
            )
        except ValueError as exc:
            failures.append(f'{name}: {exc}')
    if failures:
        raise ValueError('\n'.join(failures))
    return len(consumers)


if __name__ == '__main__':
    print(f'{check()} current Runtime profiles verified; no provider construction.')

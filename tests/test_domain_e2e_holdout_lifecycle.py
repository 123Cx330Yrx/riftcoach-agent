from pathlib import Path

from app.evaluation.domain_e2e import (
    DomainDatasetRole,
    load_domain_dataset,
    validate_domain_dataset_usage,
)


HELD_OUT = Path(
    "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
)
DEVELOPMENT = Path(
    "data/evaluation/domain_e2e_v1_1_secure_executable_development_cases.json"
)


def test_secure_held_out_dataset_is_created_but_not_executed():
    held_out = load_domain_dataset(HELD_OUT)
    development = load_domain_dataset(DEVELOPMENT)

    assert held_out.role is DomainDatasetRole.HELD_OUT
    assert held_out.calibration_excluded is True
    assert held_out.contamination_notes == ()
    assert not {
        case.case_id for case in held_out.cases
    } & {case.case_id for case in development.cases}
    validate_domain_dataset_usage(
        held_out,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )

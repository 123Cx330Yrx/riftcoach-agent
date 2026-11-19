from pathlib import Path

import pytest

from app.evaluation.sol_natural_session import SessionBlocked, digest
from scripts.product_execution_guard import checked, verify_locked_inventory
from tests.test_product_budget_supplement import opened


def test_locked_mutex_is_excluded_but_business_file_is_checked(tmp_path):
    artifact = tmp_path/'report.txt'; artifact.write_text('original', encoding='utf-8')
    lock = tmp_path/'session.lock'; lock.touch()
    inventory = {str(p):digest(p.read_bytes()) for p in (artifact,lock)}
    with opened(tmp_path) as session:
        verify_locked_inventory(session, inventory)
        artifact.write_text('changed', encoding='utf-8')
        with pytest.raises(ValueError, match='inherited_file_changed'):
            verify_locked_inventory(session, inventory)


def test_outer_exception_is_a_pause_with_body_free_error():
    errors = []
    def fails():raise PermissionError('private request must not escape')
    with pytest.raises(SessionBlocked, match='product_launcher_guard_failed'):
        checked(fails, errors.append)
    assert errors == [dict(exception_type='PermissionError',new_model_request=False)]

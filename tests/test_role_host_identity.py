"""File handoff identity must survive JSON key ordering, not value changes."""
from copy import deepcopy
import json

import pytest

from app.evaluation import coarse_role_qualification, role_qualification
from app.evaluation.golden_review_experiment import compact, digest
from scripts.role_host_identity import candidate_sha256


@pytest.mark.parametrize('backend', [role_qualification, coarse_role_qualification])
def test_saved_and_reordered_identity_retains_existing_receipt_digest(backend):
    original = backend.candidate_identity()
    saved = json.loads(json.dumps(original, sort_keys=True))
    assert saved == original and digest(compact(saved)) != digest(compact(original))
    assert candidate_sha256(saved, backend=backend) == digest(compact(original))
    assert candidate_sha256(original, backend=backend) == digest(compact(original))


@pytest.mark.parametrize('mutation', ['contract', 'manifest', 'extra', 'missing', 'wrong_profile'])
def test_actual_identity_changes_are_not_order_normalization(mutation):
    identity = deepcopy(coarse_role_qualification.candidate_identity())
    if mutation == 'contract':
        identity['contract']['program_version'] = 'invented'
    elif mutation == 'manifest':
        identity['manifest_sha256'] = '0'*64
    elif mutation == 'extra':
        identity['ignored'] = True
    elif mutation == 'missing':
        identity.pop('workflow_id')
    else:
        identity = role_qualification.candidate_identity()
    with pytest.raises(ValueError, match='candidate_identity_mismatch'):
        candidate_sha256(identity, backend=coarse_role_qualification)

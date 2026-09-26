"""Bind saved JSON to the existing profile identity without changing old hashes."""
import json

from app.evaluation.golden_review_experiment import compact, digest


def candidate_sha256(identity, *, backend=None):
    if backend is None:
        from app.evaluation import role_qualification as backend
    expected = backend.candidate_identity()
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False,
                                        allow_nan=False, separators=(',', ':'))
    if canonical(identity) != canonical(expected):
        raise ValueError('task_observation_candidate_identity_mismatch')
    # Existing receipts hash the builder's ordering, including nested contract
    # keys. Verify every value first, then restore that ordering; never accept
    # both digests or globally change compact(), which would rebind old runs.
    return digest(compact(expected))

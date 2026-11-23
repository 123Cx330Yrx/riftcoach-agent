"""Zero-send Worker executor preflight; substitutes SQL pins, never a live run.

The output explicitly excludes SQL/API lifecycle verification. A separate new
task must use the real PostgreSQL store after daemon readiness and commit CI.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from scripts.archived_product_inputs import (ArchivedProductInputs, ExistingProductSecrets,
    compose_archived_executor, read_existing_flash_key)


class _VolatilePreflightPins:
    def __init__(self):
        self.accounting = None

    def begin(self, task, binding):
        return dict(guard_sha256=None, checkpoint_sha256=None, manual_retry=False)

    def pin(self, task, checkpoint, accounting):
        self.accounting = accounting


def preflight(inputs, *, root, secret_source):
    from app.product import sol_chat_contract as contract
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    from app.memory.context_models import MemoryContextSnapshot
    from app.memory.models import RelationshipRole
    from app.evaluation.sol_natural_session import CandidateSession
    from app.evaluation.golden_stream_bridge import REQUEST
    from app.providers.zhipu_profiles import ZHIPU_STANDARD_BASE_URL, ZHIPU_GLM53_FLASH_MODEL
    from app.tasks.fingerprint import compute_conversation_review_task_fingerprint
    from app.tasks.models import (ReviewTask, ConversationReviewTaskBinding,
        ConversationReviewExecutionTarget, TaskPublicationMode, TaskStatus)
    from app.tasks.reliable_runtime import TaskLease
    from app.workers.composition import load_worker_composition_settings

    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    env = dict(DATABASE_URL='postgresql+psycopg://unused:unused@127.0.0.1:1/preflight',
        LLM_PROVIDER='zhipu', LLM_DEFAULT_PROVIDER='zhipu', LLM_MODEL=ZHIPU_GLM53_FLASH_MODEL,
        LLM_BASE_URL=ZHIPU_STANDARD_BASE_URL, LLM_TIMEOUT_SECONDS='300',
        RIFTCOACH_WORKER_EXECUTION_PROFILE=contract.WORKER_PROFILE,
        RIFTCOACH_RUNS_ROOT=str(root))
    settings = load_worker_composition_settings(env, secret_source=secret_source)

    class EmptyMemory:
        def load(self, binding):
            return MemoryContextSnapshot(binding=binding, records=())

    class NoExternalKnowledge:
        provider_name = 'preflight-no-external-knowledge'
        def search(self, query):
            raise AssertionError('preflight_knowledge_send_forbidden')

    route = compose_archived_executor(settings, repository=SimpleNamespace(), inputs=inputs,
        knowledge=NoExternalKnowledge(), memory_repository=EmptyMemory())
    pins = _VolatilePreflightPins()
    route.candidate.store = pins
    # This existing session boundary runs before model-intent persistence and
    # before dispatch. No transport result or successful model response is made.
    route.candidate.max_new_models = 0
    now = datetime.now(timezone.utc)
    binding = ConversationReviewTaskBinding(conversation_id=uuid4(), relationship_id=uuid4(),
        player_subject_id=uuid4(), relationship_role=RelationshipRole.OBSERVED)
    payload = dict(count=5, queue=420, focus='overall')
    owner = 'archived-product-zero-send'
    mode = TaskPublicationMode.EVIDENCE_BOUND_V1
    args = inputs.arguments
    task = ReviewTask(task_id=uuid4(), run_id='preview_player_language_worker',
        task_kind='recent_review', schema_version='2.0', owner_id=owner,
        idempotency_key='zero-send-preview', request_payload=payload,
        request_fingerprint=compute_conversation_review_task_fingerprint(owner_id=owner,
            binding=binding, request_payload=payload, publication_mode=mode),
        publication_mode=mode, conversation_binding=binding,
        execution_target=ConversationReviewExecutionTarget.model_validate_json(json.dumps(
            {k: args[k] for k in ('puuid', 'routing_region', 'game_name', 'tag_line')})),
        status=TaskStatus.RUNNING, worker_id='zero-send-preview', created_at=now, updated_at=now,
        claimed_at=now, finished_at=None, lease_generation=1,
        lease=TaskLease(worker_id='zero-send-preview', generation=1, token='a'*64,
            acquired_at=now, heartbeat_at=now, expires_at=now+timedelta(seconds=360)),
        terminal_reason=None, publication_status=None, report_available=False,
        trace_reference=None, receipt_reference=None, artifact_reference=None)
    measured = []
    original = CandidateSession.operation

    def measure(session, kind, value, action):
        if kind == 'model':
            request = REQUEST.validate_json(json.dumps(value))
            raw = contract.request_bytes(request)
            if any(m.reasoning_content for m in request.messages):
                raise ValueError('preflight_private_reasoning_unexpected')
            ceiling = estimate_runtime_request_input_ceiling(request)
            tail = 4 * (64000 + 16384)
            if ceiling + request.max_tokens + tail > 401920:
                raise ValueError('preflight_review_tail_budget')
            measured.append(dict(estimated_input_token_ceiling=ceiling,
                serialized_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                max_output_tokens=request.max_tokens, timeout_seconds=request.timeout_s,
                first_plus_full_review_tail=ceiling + request.max_tokens + tail))
        return original(session, kind, value, action)

    def forbid(*args, **kwargs):
        raise AssertionError('preflight_transport_forbidden')

    with patch.object(CandidateSession, 'operation', measure), \
            patch('app.runtime.sol_natural_provider.RecoverableFlashProvider.chat_at_ordinal', forbid), \
            patch('app.runtime.sol_natural_provider.SolReviewProvider.chat_at_ordinal', forbid):
        result = route.candidate.execute(task)
    if (getattr(result, 'reason', None) != 'session_model_boundary'
            or len(measured) != 1 or inputs.reads != 1
            or set(secret_source.read_names) != {'llm-api', 'sol-review-api'}):
        raise ValueError('preflight_did_not_reach_expected_boundary')
    return dict(status='worker_executor_preflight_passed_no_sql',
        contract=contract.VERSION, product_version=contract.CONTRACT.version,
        source_reads=inputs.reads, secret_names=secret_source.read_names,
        first_request=measured[0], stop_reason=result.reason, accounting=pins.accounting,
        effects=dict(model_requests=0, new_source_requests=0, persisted_sql_tasks=0),
        limits=dict(sql_lifecycle_verified=False, live_execution_started=False,
            empty_memory_substitute=True, volatile_continuation_store=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pins', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--flash-env-file', type=Path, required=True)
    args = parser.parse_args()
    pins = json.loads(args.pins.read_bytes())
    inputs = ArchivedProductInputs(pins['root'], **pins['sha256'])
    from scripts.windows_reviewer_credentials import read_key
    secrets = ExistingProductSecrets(flash_reader=lambda: read_existing_flash_key(args.flash_env_file),
        reviewer_reader=read_key)
    result = preflight(inputs, root=args.output, secret_source=secrets)
    (args.output/'preflight.json').write_text(json.dumps(result, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()

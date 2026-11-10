"""Controlled operator bridge; one explicit send, no retries or secret storage.

Authorization files record prior human consent; their existence cannot grant it.
CI proofs must be obtained from the public run by the operator, not invented.
"""
import argparse
from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import socket
import sys

from scripts import reviewer_profile_batch as batch
from scripts import reviewer_profile_live_launcher as legacy
from scripts import reviewer_responses_process as process
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.reviewer_responses_transport import digest

CODEX = Path('C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe')


def document(path, pin):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or batch.sha(path) != pin:
        raise ValueError('live_document_binding')
    value = process.read_json(path)
    if value is None:
        raise ValueError('live_document_invalid')
    return value


def authorization(value, plan, now=None):
    now = now or datetime.now(timezone.utc)
    if (value.get('version') != 'reviewer-semantic-authorization-v1'
            or value.get('plan_sha256') != digest(plan)
            or value.get('budget') != plan['budget']
            or value.get('profile') != plan['profile']
            or value.get('approved') is not True
            or not isinstance(value.get('user_evidence'), str) or not value['user_evidence'].strip()
            or value.get('account_group_confirmed') != 'GPT-pro'
            or value.get('price_cny_per_million') != {'input': '0.4', 'output': '2'}):
        raise ValueError('live_authorization_binding')
    start = datetime.fromisoformat(value['issued_at'])
    end = datetime.fromisoformat(value['expires_at'])
    if (start.tzinfo is None or end.tzinfo is None or not start <= now < end
            or not 0 < (end-start).total_seconds() <= 86400):
        raise ValueError('live_authorization_expired')


def preflight(controller, client, approval, ci):
    plan = controller.plan
    authorization(approval, plan)
    if (plan['version'] != batch.SEMANTIC_VERSION or controller.fixture_only
            or plan['profile']['group'] != 'GPT-pro' or plan['profile']['route'] != 'proxy-12000'):
        raise ValueError('live_contract_required')
    if (Path.cwd().resolve() != batch.ROOT
            or Path(sys.executable).resolve() != Path(plan['workspace']['python'])):
        raise ValueError('live_execution_paths')
    if legacy._git_head() != plan['source_identity']['head'] or not legacy._git_is_clean():
        raise ValueError('live_clean_head_required')
    if (ci.get('headSha') != plan['source_identity']['head'] or ci.get('status') != 'completed'
            or ci.get('conclusion') != 'success' or not ci.get('databaseId')
            or not ci.get('jobs') or any(j.get('conclusion') != 'success' for j in ci['jobs'])):
        raise ValueError('live_ci_binding')
    principals = plan['review_principals']
    primary = principals['primary']['principal_id']
    independent = principals['independent']['principal_id']
    thread = client.request('thread/read', {'threadId': independent})['thread']
    if thread.get('id') != independent or thread.get('parentThreadId') != primary:
        raise ValueError('live_native_parent')
    if controller.status()['phase'] != 'ready':
        raise ValueError('live_batch_not_ready')
    # A local socket check is not a provider/model probe or upstream attestation.
    with socket.create_connection(('127.0.0.1', 12000), timeout=3):
        pass


def send(controller, client, approval, ci, *, read_key=getpass.getpass, sender=process.run_once):
    preflight(controller, client, approval, ci)
    key = read_key('Third-party API key (hidden): ')
    if not isinstance(key, str) or not key.strip():
        raise ValueError('live_key_missing')
    try:
        return controller.send_next(lambda business, **kw: sender(business, api_key=key, **kw),
            before_send=lambda: preflight(controller, client, approval, ci))
    finally:
        key = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('init', 'status', 'send', 'submit', 'close'))
    parser.add_argument('--operator', required=True, type=Path)
    parser.add_argument('--checkpoint-sha')
    for name in ('plan', 'authorization', 'ci'):
        parser.add_argument('--' + name, type=Path)
        parser.add_argument('--' + name + '-sha')
    parser.add_argument('--primary-answer', type=Path)
    parser.add_argument('--event-id')
    args = parser.parse_args()
    try:
        plan = (document(args.plan, args.plan_sha) if args.action == 'init'
                else process.read_json(args.operator / 'plan.json'))
        if plan['version'] != batch.SEMANTIC_VERSION or Path(plan['operator']) != args.operator.absolute():
            raise ValueError('live_plan_binding')
        with CodexReadOnlyClient(CODEX) as client:
            source = CodexHostReviewEventSource(client, plan)
            if args.action == 'init':
                controller = batch.ScreenBatch.create(plan, source)
                result = controller.status()
            else:
                controller = batch.ScreenBatch.load(args.operator, args.checkpoint_sha, source)
                if args.action == 'send':
                    result = send(controller, client,
                        document(args.authorization, args.authorization_sha), document(args.ci, args.ci_sha))
                elif args.action == 'submit':
                    decision = process.read_json(args.primary_answer)
                    submit = (controller.submit_pair_review if controller.status()['phase'] == 'awaiting_pair_review'
                              else controller.submit_review)
                    result = submit(decision, args.event_id)
                elif args.action == 'close':
                    result = controller.close()
                else:
                    result = controller.status()
            print(json.dumps(dict(status=result, checkpoint_sha256=controller.checkpoint_sha), ensure_ascii=True))
    except (Exception, KeyboardInterrupt):
        print(json.dumps(dict(ok=False, code='semantic_live_stopped', qualified=False,
                              publication_allowed=False), ensure_ascii=True))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

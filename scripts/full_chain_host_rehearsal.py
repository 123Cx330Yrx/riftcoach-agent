"""Single-case OFFLINE business fixtures with REAL native Host handoffs.

No credentials, network transport, model requests or qualification. The native
reader is the installed read-only Codex app-server. Never reopen a run.
"""
import argparse
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

from app.evaluation import golden_stream_bridge as legacy
from app.evaluation.document_review_timed_transport import TimedDocumentRouter
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts.full_chain_evidence import FullChainEvidence, ROOT, sha
from scripts.full_chain_modules import private_module
from scripts import full_chain_observed_transport as observed

VERSION = 'full-chain-offline-business-real-host-v1'
KEY = 'claim-scope:4'
FIXTURE = 'tests/fixtures/coarse_edit_initial_reviews_20261001.json'
BEFORE = '所选全部 5 局的每一个指标均值都被辅助局拉低，包括视野分与 15 分钟前死亡，应按位置分开解读。'
AFTER = '所选全部 5 局中，辅助局拉低了补刀、经济和伤害的均值，却拉高了视野分与 15 分钟前死亡的均值，应按位置分开解读。'


@contextmanager
def no_network():
    """Fail closed if in-process Provider code tries any socket connection."""
    original = socket.socket.connect, socket.socket.connect_ex
    def forbidden(*args, **kwargs):
        raise ValueError('offline_rehearsal_network_forbidden')
    socket.socket.connect = socket.socket.connect_ex = forbidden
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex = original


class Rehearsal(FullChainEvidence):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        original_controls = self.runner.controls
        @lru_cache(maxsize=1)
        def controls(root=ROOT):
            rows, variants = original_controls(root)
            return [r for r in rows if r['key'] == KEY], [v for v in variants if v[0]['key'] == KEY]
        self.runner.controls = controls
        original_task = self.runner._task
        def task(*args, **kwargs):
            value = json.loads(original_task(*args, **kwargs))
            value['instructions'] = (
                'OFFLINE business-response rehearsal. Responses and transport/usage/observation '
                'receipts are synthetic fixtures; assess their actual semantic content independently. '
                'Your own author file and single native final will be real Host evidence, '
                'not model-quality or qualification evidence. No model service calls.\n'
                + value['instructions'])
            return self.runner.compact(value)
        self.runner._task = task

    def prepare(self, **kwargs):
        plan = super().prepare(**kwargs)
        if plan['sequence'] != [KEY]:
            raise ValueError('offline_rehearsal_scope')
        plan.update(kind=VERSION, run_id=VERSION,
            business_evidence='OFFLINE FIXTURE: responses, usage, transport receipts and observations are synthetic. Only Host authorship/native import are real.',
            paid_execution_enabled=False, external_provider_calls=0, external_http_requests=0,
            scope='One fixed case; at most initial, revision, final. No paid requests or qualification.')
        plan['source_sha256'].update({p: sha(ROOT / p) for p in
            ('scripts/full_chain_host_rehearsal.py', FIXTURE)})
        return plan

    def offline_factory(self):
        """Reuse actual role receipts but replace the child before process IO."""
        bridge = private_module(Path(legacy.__file__), {})
        fixtures = json.loads((ROOT / FIXTURE).read_text(encoding='utf-8'))
        first = next(r for r in fixtures['cases'] if r['key'] == KEY)
        source = self.runner.controls()[1][0][1]
        if first['report_sha256'] != self.runner.digest(source.report):
            raise ValueError('offline_rehearsal_fixture_source')

        def child(command, raw, *, directory, timeout_s, environ, transport_id):
            self.check()
            request = bridge.REQUEST.validate_json(raw)
            phase = request.metadata['review_phase']
            ordinal = int(directory.name.split('-')[-1])
            if phase == 'native_business_revision' and ordinal == 2:
                model, tool = 'glm-5.3-flash', 'submit_block_edits'
                args = dict(edits={'block_4': [dict(before=BEFORE, after=AFTER,
                    reason='OFFLINE fixture correcting the direction of the mixed-sample means.')]})
            elif phase == 'native_business_review' and ordinal in (1, 3):
                model, tool = 'glm-5.3', 'submit_report_review'
                args = json.loads(first['initial_raw']) if ordinal == 1 else dict(
                    score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
            else:
                raise ValueError('offline_rehearsal_unexpected_request')
            side = self.observations / hashlib.sha256(str(directory.resolve()).encode()).hexdigest()
            side.mkdir(parents=True, exist_ok=False)
            write = self.runner._write_json
            write(side / 'binding.json', dict(version=observed.VERSION, transport_id=transport_id,
                request_sha256=hashlib.sha256(raw).hexdigest(), worker_directory=str(directory.resolve()),
                route=dict(route='direct', destination_host='open.bigmodel.cn', process_proxy_present=False,
                    no_proxy_matches_host=True, system_network_path_proven=False)))
            write(side / 'parent-audit.json', dict(transport_complete=True, observation_valid=True,
                files={'binding.json': sha(side / 'binding.json')},
                fixture='OFFLINE synthetic binding and observation; no HTTP, worker or route was exercised.',
                external_provider_calls=0, external_http_requests=0))
            write(directory / 'result.json', dict(state='complete', elapsed_ms=0, transport_id=transport_id,
                fixture='OFFLINE business response; no child process or HTTP'))
            return ChatResponse(provider='zhipu', model=model, content=None, finish_reason='tool_calls',
                usage=TokenUsage(20, 10), tool_calls=(ToolCall(id='OFFLINE-FIXTURE', name=tool, arguments=args),))

        bridge.run_child = child
        providers = private_module(ROOT / 'app/runtime/receipted_provider_factory.py',
            {'app.evaluation.golden_stream_bridge': bridge})
        class Factory(providers.RunScopedRoleReceiptedProviderFactory):
            def _build(inner, directory):
                def provider(settings, role, transport):
                    return providers.RoleReceiptedStreamProvider(settings=settings, directory=directory / role,
                        task_directory=directory, transport_id=transport)
                return TimedDocumentRouter(provider(inner._generator_settings, 'generation', legacy.TIMED_FLASH_TRANSPORT_ID),
                    provider(inner._reviewer_settings, 'review', legacy.TIMED_REVIEW_TRANSPORT_ID), source_projection=PROJECTION)
        settings = lambda model: SimpleNamespace(model=model, api_key='OFFLINE-NOT-A-CREDENTIAL',
            base_url='https://open.bigmodel.cn/api/paas/v4')
        return Factory(generator_settings=settings('glm-5.3-flash'), reviewer_settings=settings('glm-5.3'),
            transport_root=self.directory / 'transport', source_projection=PROJECTION)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'material', 'submit', 'abort', 'replay', 'seal'))
    for name in ('directory', 'answers', 'observations', 'python', 'cwd'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--root-thread-id')
    parser.add_argument('--independent-thread-id')
    parser.add_argument('--stage', choices=('initial', 'revision', 'final'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--codex-executable', type=Path)
    args = parser.parse_args()
    session = Rehearsal(**{k: getattr(args, k) for k in ('directory', 'answers', 'observations', 'python', 'cwd')})
    runner, evidence = session.runner, session.evidence
    if args.action == 'prepare':
        if not all((args.root_thread_id, args.independent_thread_id, args.output)):
            parser.error('prepare requires principal IDs and output')
        session.execution_paths_preflight()
        runner._write_json(args.output, session.prepare(root_thread_id=args.root_thread_id,
            independent_thread_id=args.independent_thread_id))
        print(json.dumps(dict(prepared=True, external_provider_calls=0)))
        return
    if args.action == 'run':
        if not args.preparation or session.directory.exists():
            raise ValueError('offline_rehearsal_preparation_or_existing_run')
        plan = evidence.read(args.preparation)
        if plan != session.prepare(root_thread_id=plan['root_thread_id'],
                independent_thread_id=plan['review_principals']['independent']['principal_id']):
            raise ValueError('offline_rehearsal_preparation_changed')
        session.execution_paths_preflight()
    else:
        plan = evidence.load_plan(session.directory)
    if args.action == 'material':
        if not args.stage: parser.error('stage required')
        print(evidence.task(session.directory, KEY, args.stage)); return
    if args.action == 'abort':
        if not args.stage: parser.error('stage required')
        print(runner.compact(evidence.abort(session.directory, KEY, args.stage, 'operator_stop'))); return
    if not args.codex_executable: parser.error('codex-executable required')
    with no_network(), runner.CodexReadOnlyClient(args.codex_executable) as client:
        source = runner.CodexHostReviewEventSource(client, plan)
        if args.action == 'run':
            runner.verify_native_principals(client, plan)
            session.directory.mkdir(parents=True, exist_ok=False)
            runner._write_json(session.directory / 'plan.json', dict(preparation_plan=plan,
                plan_sha256=runner.canonical_sha(plan)))
            value = runner.observe(session.offline_factory(), session.directory, plan, event_source=source)
        elif args.action == 'submit':
            if not all((args.stage, args.notes, args.event_id, args.checkpoint_sha)):
                parser.error('submission arguments required')
            value = evidence.submit(session.directory, KEY, args.stage, evidence.read(args.notes),
                args.event_id, source, args.checkpoint_sha)
        elif args.action == 'seal':
            if not args.output: parser.error('output required')
            value = evidence.seal(session.directory, args.output, event_source=source)
        else:
            value = evidence.replay(session.directory, event_source=source)
    print(runner.compact(value))


if __name__ == '__main__':
    main()

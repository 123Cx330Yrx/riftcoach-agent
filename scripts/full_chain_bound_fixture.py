"""Prospective complete-response fixtures; frozen rehearsals remain unchanged.

No CLI, Provider access or semantic approval. A pin binds the WHOLE response,
including edit reasons, to exact inputs. The normal editor still validates it.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from app.evaluation import golden_stream_bridge as legacy
from app.evaluation.document_review_timed_transport import TimedDocumentRouter
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.source_patch_editor import report_inputs
from scripts.full_chain_evidence import ROOT, sha
from scripts.full_chain_explicit_host_rehearsal import ExplicitRehearsal
from scripts.full_chain_modules import private_module
from scripts import full_chain_observed_transport as observed
from scripts.report_timed_document_workflow import TimedDocumentWorkflow as Workflow, request_sha

VERSION = 'offline-complete-response-binding-v1'
FIXTURE = 'data/evaluation/fixtures/full_chain_bound_count_20261013.json'


def load_bundle(path, expected_sha, inputs):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('bound_fixture_digest')
    value = json.loads(raw)
    if (value.get('kind') != VERSION or value.get('synthetic') is not True
            or value.get('input_sha256') != digest(inputs.data_json)
            or value.get('report_sha256') != digest(inputs.source.report)
            or set(value.get('responses', {})) != {'initial', 'revision', 'final'}):
        raise ValueError('bound_fixture_input_or_format')
    responses = {k: legacy.RESPONSE.validate_python(v) for k, v in value['responses'].items()}
    for stage, response in responses.items():
        expected = ('glm-5.3-flash', 'submit_block_edits') if stage == 'revision' else (
            'glm-5.3', 'submit_report_review')
        if (response.provider != 'zhipu' or response.model != expected[0]
                or response.finish_reason != 'tool_calls' or (response.content or '').strip()
                or len(response.tool_calls) != 1 or response.tool_calls[0].name != expected[1]):
            raise ValueError('bound_fixture_channel')
    _, accepted, _ = Workflow.validate_review(compact(responses['initial'].tool_calls[0].arguments), inputs)
    request = Workflow.edit_request(inputs, accepted)
    assembly = Workflow.inspect_exchange(request, Exchange(request, responses['revision'],
        request_sha(request)), inputs, accepted)
    if digest(assembly.report) != value.get('revised_report_sha256'):
        raise ValueError('bound_fixture_revised_report')
    final_inputs = report_inputs(inputs, assembly.report)
    Workflow.validate_review(compact(responses['final'].tool_calls[0].arguments), final_inputs)
    return responses, assembly


class BoundRehearsal(ExplicitRehearsal):
    """Future offline consumer, never selected when replaying a frozen old run."""

    def prepare(self, **kwargs):
        plan = super().prepare(**kwargs)
        plan.update(kind=VERSION, run_id=VERSION)
        plan['source_sha256'].update({p: sha(ROOT / p) for p in
            ('scripts/full_chain_bound_fixture.py', FIXTURE)})
        return plan

    def offline_factory(self):
        bridge = private_module(Path(legacy.__file__), {})
        inputs = self.runner.controls()[1][0][2]
        pin = self.evidence.load_plan(self.directory)['source_sha256'][FIXTURE]
        load_bundle(ROOT / FIXTURE, pin, inputs)

        def child(command, raw, *, directory, timeout_s, environ, transport_id):
            self.check()
            responses, assembly = load_bundle(ROOT / FIXTURE, pin, inputs)
            request = bridge.REQUEST.validate_json(raw)
            ordinal = int(directory.name.split('-')[-1])
            if ordinal not in (1, 2, 3):
                raise ValueError('bound_fixture_unexpected_request')
            stage = ('initial', 'revision', 'final')[ordinal - 1]
            phase = 'native_business_revision' if stage == 'revision' else 'native_business_review'
            expected_transport = legacy.TIMED_FLASH_TRANSPORT_ID if stage == 'revision' else legacy.TIMED_REVIEW_TRANSPORT_ID
            if request.metadata['review_phase'] != phase or transport_id != expected_transport:
                raise ValueError('bound_fixture_unexpected_request')
            # The existing role provider checks issued identity and the workflow
            # checks the full request. The fixture supplies no assembled fields.
            side = self.observations / hashlib.sha256(str(directory.resolve()).encode()).hexdigest()
            side.mkdir(parents=True, exist_ok=False)
            write = self.runner._write_json
            write(side / 'binding.json', dict(version=observed.VERSION, transport_id=transport_id,
                request_sha256=hashlib.sha256(raw).hexdigest(), worker_directory=str(directory.resolve()),
                route=dict(route='direct', destination_host='open.bigmodel.cn', process_proxy_present=False,
                    no_proxy_matches_host=True, system_network_path_proven=False)))
            write(side / 'parent-audit.json', dict(transport_complete=True, observation_valid=True,
                files={'binding.json': sha(side / 'binding.json')}, fixture='OFFLINE complete-response fixture; no HTTP or route exercised.',
                fixture_sha256=pin, external_provider_calls=0, external_http_requests=0))
            write(directory / 'result.json', dict(state='complete', elapsed_ms=0, transport_id=transport_id,
                fixture='OFFLINE complete response; no child process or HTTP'))
            return responses[stage]

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

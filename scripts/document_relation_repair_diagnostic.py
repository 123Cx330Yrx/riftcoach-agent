"""New calibrated U1/U2 initial comparison; preparation never authorizes IO."""
from pathlib import Path

from scripts.document_sampling_screening import load_private
from scripts import document_relation_observed_request as identity

ROOT = Path(__file__).resolve().parents[1]
parent = load_private(ROOT / 'scripts/document_relation_diagnostic.py', 'scripts._repair_relation_parent')
base, runner, transport = parent.base, parent.runner, parent.transport
VERSION = 'document-relation-repair-diagnostic-v1'
CALIBRATION = 'data/evaluation/fixtures/host_relation_repair_calibration_20261012/materials.json'
CALIBRATION_SHA = '77f22cafa8f28ba3149b786f9bec6113a8a2ee857e85c0110cb9b85b0e82bac8'
CALIBRATION_TASK = 'data/evaluation/fixtures/host_relation_repair_calibration_20261012/task.txt'
CALIBRATION_TASK_SHA = 'dd31cff2b1f04d99a315a773815e54c7919dc31ed12339f69858ffbe73f918de'
CALIBRATION_AUDIT = 'data/evaluation/results/host_relation_repair_calibration_20261012/close-audit.json'
CALIBRATION_AUDIT_SHA = 'b326e41089891e92fbf1897acda72f2679c491f3de294c4ba01bcf842c3076ac'

parent.VERSION = base.VERSION = runner.VERSION = VERSION
parent.CALIBRATION, parent.CALIBRATION_SHA = CALIBRATION, CALIBRATION_SHA
parent.CALIBRATION_TASK, parent.CALIBRATION_TASK_SHA = CALIBRATION_TASK, CALIBRATION_TASK_SHA
parent.CALIBRATION_AUDIT, parent.CALIBRATION_AUDIT_SHA = CALIBRATION_AUDIT, CALIBRATION_AUDIT_SHA
parent.identity = base.identity = runner.identity = base.host.identity = transport.identity = identity
base.AUTH_VERSION = runner.AUTH_VERSION = 'document-relation-repair-authorization-v1'
base.RUN_ID = 'document-relation-repair-20261013'
base.ADAPTER_SOURCE = 'scripts/document_relation_repair_diagnostic.py'
base.REQUEST_SOURCE = 'scripts/document_relation_observed_request.py'
base.IDENTITY = 'scripts.document_relation_observed_request'
base.OPERATOR_ROOT = identity.OBSERVATION_ROOT.parent


def reports():
    for case in parent.calibration()['cases']:
        yield case['case_id'], '\n\n'.join(b['text'] for b in case['report']), ('accept' if case['case_id'] == 'U1' else 'reject')


parent.reports = reports
_prepare = parent.prepare


def prepare(*, root_thread_id, independent_thread_id):
    plan, rows = _prepare(root_thread_id=root_thread_id, independent_thread_id=independent_thread_id)
    for path in ('scripts/document_relation_request.py', 'scripts/document_relation_diagnostic.py',
                 'scripts/stream_observation.py', 'tests/test_document_relation_repair_diagnostic.py'):
        plan['source_sha256'][path] = base.sha((ROOT / path).read_bytes())
    plan.update(scope='U1/U2 calibrated familiar-source full reports; baseline then relation teaching, four initial requests only.',
        prior_exposure='New authored development controls calibrated on familiar sources; not holdout. Closed batches remain separate.',
        report_projection='Two complete 26-block reports differing only in block14 proximity sentence; all facts retained.',
        observation_contract=identity.VERSION, observation_root=str(identity.OBSERVATION_ROOT.absolute()),
        observation_required=True, route_contract='direct/open.bigmodel.cn/process-proxies-cleared/NO_PROXY-exact',
        interpretation='Candidate still wrong: reject. Both arms pass or baseline does not reproduce: no improvement evidence. No product qualification.')
    return plan, rows


base.prepare = prepare
workspace = parent.workspace
workspace.answers = (base.OPERATOR_ROOT / 'author-answers').absolute()
workspace.validate_paths()
Package, controls, run = base.Package, parent.controls, parent.run


def audit_observations(directory):
    """Read-only observation inventory; completed responses require valid IO."""
    directory = Path(directory)
    plan = base.read(directory / 'plan.json')['preparation_plan']
    if (plan['observation_contract'] != identity.VERSION or plan['observation_required'] is not True
            or plan['observation_root'] != str(identity.OBSERVATION_ROOT.absolute())):
        raise ValueError('repair_observation_plan_changed')
    result = []
    for cell in plan['cells']:
        transport_dir = directory / cell['key'].replace(':','-') / 'transport'
        issued = transport_dir / 'issued-request.json'
        if issued.exists():
            result.append(identity.verify_observation(transport_dir / 'stream-001', issued.read_bytes(),
                complete_required=(transport_dir / 'raw-response.json').exists()))
    return result


_validate, _observe, _replay = runner.validate_submission, runner.observe, runner.replay


def validate_submission(directory, key, submission, event_source):
    audit_observations(directory)
    return _validate(directory, key, submission, event_source)


def observe(directory, plan, rows, provider, event_source, **kwargs):
    before = kwargs.pop('before_send', lambda: None)
    def checked():
        audit_observations(directory)
        before()
    return _observe(directory, plan, rows, provider, event_source, before_send=checked, **kwargs)


def replay(directory, *, event_source):
    observations = audit_observations(directory)
    value = _replay(directory, event_source=event_source)
    value['body_free_observations'] = observations
    return value


runner.validate_submission, runner.observe, runner.replay = validate_submission, observe, replay


if __name__ == '__main__':
    base.main()

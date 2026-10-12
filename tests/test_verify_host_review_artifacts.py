import json
from pathlib import Path

import pytest

from scripts import host_review_task_checkpoint as checkpoint
from scripts import verify_host_review_artifacts as helper
from scripts.codex_review_event_source import review_task


def make_artifacts(tmp_path):
    # Preserve deliberately noncanonical JSON bytes: reserialization is wrong.
    request = b'{ "z": 1, "a": 2 }\n'
    response = b'{"content":null}\n'
    report = 'Synthetic report only.'
    bound = dict(plan_sha256='a'*64, key='synthetic:1', stage='initial',
        request_sha256=checkpoint.digest(request), response_sha256=checkpoint.digest(response),
        report_sha256=checkpoint.digest(report.encode()))
    (tmp_path/'issued-request.json').write_bytes(request)
    (tmp_path/'response.json').write_bytes(response)
    (tmp_path/'stage.json').write_text(json.dumps(dict(stage='initial', report=report,
        journal={'note': 'synthetic'})), encoding='utf-8')
    task = tmp_path/'task.json'
    task.write_text(review_task(bound, 'Full review still required.'), encoding='utf-8')
    pin = tmp_path/'checkpoint.json'
    return pin, checkpoint.publish(pin, task, 'synthetic-independent')


def test_checks_exact_bytes_without_reading_labels_or_other_host_files(tmp_path, monkeypatch):
    pin, sha = make_artifacts(tmp_path)
    allowed = {'checkpoint.json', 'task.json', 'issued-request.json', 'response.json', 'stage.json'}
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert path.parent == tmp_path and path.name in allowed
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    result = helper.verify(pin, sha)
    assert result['artifact_hashes_verified']
    assert not result['full_source_review_performed']
    assert not result['native_review_certified']
    assert set(p.name for p in tmp_path.iterdir()) == allowed


@pytest.mark.parametrize('file,match', [
    ('issued-request.json', 'request_sha256'), ('response.json', 'response_sha256'),
    ('stage.json', 'report_sha256'), ('task.json', 'task_digest'),
    ('checkpoint.json', 'checkpoint_digest'),
])
def test_changed_artifacts_fail_without_rewriting_or_falling_back(tmp_path, file, match):
    pin, sha = make_artifacts(tmp_path)
    target = tmp_path/file
    if file == 'stage.json':
        value = json.loads(target.read_bytes()); value['report'] = 'Changed'
        target.write_text(json.dumps(value), encoding='utf-8')
    else:
        target.write_bytes(target.read_bytes() + b' ')
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match=match):
        helper.verify(pin, sha)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before

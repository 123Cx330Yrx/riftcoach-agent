"""The aggregate gate must reject skipped work, duplicate work and failed shards."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from scripts.ci_test_shards import verify

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def actual_shards(tmp_path_factory):
    root = tmp_path_factory.mktemp('ci-shard-coverage')
    source = root/'test_example.py'
    source.write_text('import pytest\n@pytest.mark.parametrize("i",range(7))\ndef test_complete(i):\n    assert i < 7\n@pytest.mark.skip(reason="fixture skip")\ndef test_skipped():\n    pass\n',encoding='utf-8')
    records = []
    for index in range(4):
        manifest = root/f'shard-{index}.json'
        done = subprocess.run([sys.executable,'-m','scripts.ci_test_shards','run','--index',str(index),
            '--count','4','--manifest',str(manifest),'--','-q',str(source)],cwd=ROOT,
            text=True,capture_output=True,encoding='utf-8')
        assert done.returncode == 0, done.stdout+done.stderr
        records.append(json.loads(manifest.read_bytes()))
    return records


def test_four_real_pytest_processes_cover_all_collected_tests_once(actual_shards):
    result = verify(actual_shards,count=4,head=actual_shards[0]['head_sha'])
    assert result['collected']==result['completed']==8 and result['skipped']==1


@pytest.mark.parametrize('fault',['missing_shard','missing_test','duplicate_test','failed_shard','different_suite','wrong_head'])
def test_aggregate_rejects_incomplete_or_inconsistent_evidence(actual_shards,fault):
    records=deepcopy(actual_shards)
    if fault=='missing_shard': records.pop()
    if fault=='missing_test': records[0]['executed_nodeids'].pop()
    if fault=='duplicate_test': records[0]['executed_nodeids'].append(records[0]['executed_nodeids'][0])
    if fault=='failed_shard': records[0]['exit_code']=1
    if fault=='different_suite': records[0]['full_nodeids']=records[0]['full_nodeids'][:-1]
    if fault=='wrong_head': records[0]['head_sha']='wrong'
    with pytest.raises(ValueError):
        verify(records,count=4,head=actual_shards[1]['head_sha'])

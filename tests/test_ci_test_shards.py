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
    (root/'tests').mkdir()
    source = root/'tests/test_example.py'
    source.write_text('import pytest\nimport unittest\n@pytest.mark.parametrize("i",range(7))\ndef test_complete(i):\n    assert i < 7\n@pytest.mark.skip(reason="fixture skip")\ndef test_skipped():\n    pass\nclass TestNested(unittest.TestCase):\n    def test_subtests(self):\n        for i in range(3):\n            with self.subTest(i=i):\n                self.assertLess(i,3)\n        with self.subTest(skipped=True):\n            self.skipTest("subtest skip")\n',encoding='utf-8')
    subprocess.run(['git','init','-q',str(root)],check=True)
    subprocess.run(['git','-c','user.name=CI test','-c','user.email=ci@example.invalid',
        'commit','--allow-empty','-qm','fixture'],cwd=root,check=True)
    listing = root/'sql-files.txt'
    listing.write_text('tests/test_example.py\n',encoding='utf-8')
    records = []
    for index in range(4):
        manifest = root/f'shard-{index}.json'
        # Both CLI entry forms must collect identical suites and split once.
        selection = ['--test-list',str(listing),'--','-q'] if index % 2 == 0 else ['--','-q',str(source)]
        done = subprocess.run([sys.executable,str(ROOT/'scripts/ci_test_shards.py'),'run','--index',str(index),
            '--count','4','--manifest',str(manifest),*selection],cwd=root,
            text=True,capture_output=True,encoding='utf-8')
        assert done.returncode == 0, done.stdout+done.stderr
        records.append(json.loads(manifest.read_bytes()))
    return records


def test_four_real_pytest_processes_cover_all_collected_tests_once(actual_shards):
    result = verify(actual_shards,count=4,head=actual_shards[0]['head_sha'])
    assert result['collected']==result['completed']==9 and result['skipped']==1
    if int(pytest.__version__.split('.')[0]) >= 9:
        assert result['subtest_reports']==4
        assert any(s['outcome']=='skipped' for r in actual_shards for s in r['subtest_reports'])


@pytest.mark.parametrize('kind', ['test', 'subtest'])
def test_sql_gate_rejects_a_skip_even_with_successful_processes(actual_shards, kind):
    records = deepcopy(actual_shards)
    for record in records:
        record['skipped_nodeids'] = []
        record['subtest_reports'] = []
    first = records[0]
    if kind == 'test':
        first['skipped_nodeids'] = [first['executed_nodeids'][0]]
    else:
        first['subtest_reports'] = [dict(nodeid=first['executed_nodeids'][0],outcome='skipped')]
    with pytest.raises(ValueError,match='ci_shard_unexpected_skip'):
        verify(records,count=4,head=first['head_sha'],require_no_skips=True)


@pytest.mark.parametrize('content', ['', 'tests/test_database_config.py\ntests/test_database_config.py\n',
    'tests/test_missing_ci_file.py\n', 'tests/../test_outside.py\n'])
def test_invalid_explicit_file_list_fails_before_running_tests(tmp_path, content):
    listing = tmp_path/'files.txt'; listing.write_text(content,encoding='utf-8')
    manifest = tmp_path/'shard-0.json'
    done = subprocess.run([sys.executable,'-m','scripts.ci_test_shards','run','--index','0',
        '--count','1','--manifest',str(manifest),'--test-list',str(listing),'--','-q'],cwd=ROOT,
        text=True,capture_output=True,encoding='utf-8')
    assert done.returncode != 0 and 'ci_test_list_invalid' in done.stderr
    assert not manifest.exists()


@pytest.mark.parametrize('fault',['missing_shard','missing_test','duplicate_test','failed_shard','different_suite','wrong_head','duplicate_skip','failed_subtest','foreign_subtest'])
def test_aggregate_rejects_incomplete_or_inconsistent_evidence(actual_shards,fault):
    records=deepcopy(actual_shards)
    if fault=='missing_shard': records.pop()
    if fault=='missing_test': records[0]['executed_nodeids'].pop()
    if fault=='duplicate_test': records[0]['executed_nodeids'].append(records[0]['executed_nodeids'][0])
    if fault=='failed_shard': records[0]['exit_code']=1
    if fault=='different_suite': records[0]['full_nodeids']=records[0]['full_nodeids'][:-1]
    if fault=='wrong_head': records[0]['head_sha']='wrong'
    if fault=='duplicate_skip':
        skipped = next(r for r in records if r['skipped_nodeids'])
        skipped['skipped_nodeids'].append(skipped['skipped_nodeids'][0])
    if fault=='failed_subtest':
        records[0]['subtest_reports'].append(dict(nodeid=records[0]['selected_nodeids'][0],outcome='failed'))
    if fault=='foreign_subtest':
        records[0]['subtest_reports'].append(dict(nodeid='uncollected-test',outcome='passed'))
    with pytest.raises(ValueError):
        verify(records,count=4,head=actual_shards[1]['head_sha'])


def test_real_failed_unittest_subtest_cannot_turn_into_a_green_shard(tmp_path):
    source=tmp_path/'test_failure.py'
    source.write_text('import unittest\nclass TestBad(unittest.TestCase):\n    def test_subtests(self):\n        for i in range(2):\n            with self.subTest(i=i):\n                self.assertEqual(i,0)\n',encoding='utf-8')
    manifest=tmp_path/'shard-0.json'
    done=subprocess.run([sys.executable,'-m','scripts.ci_test_shards','run','--index','0',
        '--count','1','--manifest',str(manifest),'--','-q',str(source)],cwd=ROOT,
        text=True,capture_output=True,encoding='utf-8')
    assert done.returncode != 0
    record=json.loads(manifest.read_bytes())
    assert record['exit_code']==done.returncode
    with pytest.raises(ValueError):
        verify([record],count=1,head=record['head_sha'])

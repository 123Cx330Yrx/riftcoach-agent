"""Run isolated pytest shards and verify exact, completed full-suite coverage."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess

import pytest


class Inventory:
    def __init__(self, index, count, head):
        if type(index) is not int or type(count) is not int or not 0 <= index < count:
            raise ValueError('ci_shard_index')
        self.index, self.count, self.head = index, count, head
        self.full, self.selected, self.executed, self.skipped = [], [], [], []

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, config, items):
        self.full = [item.nodeid for item in items]
        self.selected = self.full[self.index::self.count]
        chosen = [item for i,item in enumerate(items) if i % self.count == self.index]
        omitted = [item for i,item in enumerate(items) if i % self.count != self.index]
        items[:] = chosen
        config.hook.pytest_deselected(items=omitted)

    def pytest_runtest_logreport(self, report):
        if report.when == 'call' or (report.when == 'setup' and report.skipped):
            self.executed.append(report.nodeid)
            if report.skipped:
                self.skipped.append(report.nodeid)

    def record(self, code):
        return dict(version=1, head_sha=self.head, index=self.index, count=self.count,
            full_nodeids=self.full, selected_nodeids=self.selected,
            executed_nodeids=self.executed, skipped_nodeids=self.skipped, exit_code=int(code))


def verify(records, *, count, head):
    if (len(records) != count or {r['index'] for r in records} != set(range(count))
        or any(r['count'] != count or r['head_sha'] != head or r['version'] != 1
            or r['exit_code'] != 0 for r in records)):
        raise ValueError('ci_shard_inventory_or_failure')
    full = records[0]['full_nodeids']
    if not full or len(full) != len(set(full)) or any(r['full_nodeids'] != full for r in records):
        raise ValueError('ci_shard_collected_suites_differ')
    all_executed = []
    for r in records:
        selected = full[r['index']::count]
        if (r['selected_nodeids'] != selected or Counter(r['executed_nodeids']) != Counter(selected)
            or not Counter(r['skipped_nodeids']) <= Counter(r['executed_nodeids'])):
            raise ValueError('ci_shard_missing_duplicate_or_unfinished_tests')
        all_executed.extend(r['executed_nodeids'])
    if Counter(all_executed) != Counter(full):
        raise ValueError('ci_shard_full_coverage')
    return dict(head_sha=head, shard_count=count, collected=len(full), completed=len(all_executed),
        skipped=sum(len(r['skipped_nodeids']) for r in records), exact_full_coverage=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    run = actions.add_parser('run')
    run.add_argument('--index', type=int, required=True)
    run.add_argument('--count', type=int, required=True)
    run.add_argument('--manifest', type=Path, required=True)
    run.add_argument('pytest_args', nargs=argparse.REMAINDER)
    check = actions.add_parser('verify')
    check.add_argument('--directory', type=Path, required=True)
    check.add_argument('--count', type=int, required=True)
    args = parser.parse_args()
    head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if args.action == 'verify':
        files = sorted(args.directory.rglob('shard-*.json'))
        print(json.dumps(verify([json.loads(f.read_bytes()) for f in files],count=args.count,head=head)))
        return
    inventory = Inventory(args.index,args.count,head)
    flags = args.pytest_args[1:] if args.pytest_args[:1] == ['--'] else args.pytest_args
    code = pytest.main(flags,plugins=[inventory])
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(inventory.record(code),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(code)


if __name__ == '__main__':
    main()

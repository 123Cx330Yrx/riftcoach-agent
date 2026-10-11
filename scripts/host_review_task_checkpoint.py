"""Pin an operator task for recovery; never author or certify a review.

This prospective helper leaves frozen builders and native-event validation
unchanged. A reviewer rereads one explicit immutable checkpoint after recovery
and before final output. No filesystem search, old-task fallback or Provider IO.
"""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_inference_scope_v5 import strict_json
from scripts.codex_review_event_source import TASK_KIND
from scripts.review_independence_contract import required_binding

VERSION = 'host-review-task-checkpoint-v1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def publish(path, task_path, reviewer_id, *, purpose='review'):
    if purpose not in ('review', 'routing-probe') or not reviewer_id.strip():
        raise ValueError('host_checkpoint_purpose_or_reviewer')
    task_path = Path(task_path).resolve(strict=True)
    raw = task_path.read_bytes()
    task = strict_json(raw.decode('utf-8'))
    if (not isinstance(task, dict) or set(task) != {'kind','binding','instructions'}
            or task['kind'] != TASK_KIND or not isinstance(task['instructions'], str)
            or not task['instructions'].strip()
            or task['binding'] != required_binding(task['binding'])):
        raise ValueError('host_checkpoint_task')
    value = dict(version=VERSION, purpose=purpose, reviewer_id=reviewer_id,
        task_path=str(task_path), task_sha256=digest(raw), binding=task['binding'])
    raw = (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    with Path(path).open('xb') as f:
        f.write(raw)
    return digest(raw)


def read(path, expected_sha256):
    raw = Path(path).read_bytes()
    if digest(raw) != expected_sha256:
        raise ValueError('host_checkpoint_digest')
    value = strict_json(raw.decode('utf-8'))
    if (set(value) != {'version','purpose','reviewer_id','task_path','task_sha256','binding'}
            or value['version'] != VERSION or value['purpose'] not in ('review','routing-probe')
            or not isinstance(value['reviewer_id'],str) or not value['reviewer_id'].strip()
            or not isinstance(value['task_path'],str) or not Path(value['task_path']).is_absolute()):
        raise ValueError('host_checkpoint_format')
    task_raw = Path(value['task_path']).read_bytes()
    if digest(task_raw) != value['task_sha256']:
        raise ValueError('host_checkpoint_task_digest')
    task = strict_json(task_raw.decode('utf-8'))
    if (task.get('kind') != TASK_KIND or task.get('binding') != value['binding']
            or value['binding'] != required_binding(value['binding'])):
        raise ValueError('host_checkpoint_binding')
    return value,task


def check_answer(path, expected_sha256, answer_raw):
    """Reject drift without filling fields, changing opinions or adding events."""
    value,_ = read(path,expected_sha256)
    answer = strict_json(answer_raw.decode('utf-8'))
    if not isinstance(answer,dict) or answer.get('binding') != value['binding']:
        raise ValueError('host_checkpoint_answer_binding')
    if value['purpose'] == 'routing-probe':
        if (set(answer) != {'binding','checkpoint_sha256','probe_only','review_performed'}
                or answer['checkpoint_sha256'] != expected_sha256
                or answer['probe_only'] is not True or answer['review_performed'] is not False):
            raise ValueError('host_checkpoint_probe_answer')
    else:
        review = answer.get('review')
        if (set(answer) != {'binding','review'} or not isinstance(review,dict)
                or review.get('binding') != value['binding']
                or {'independent_source_event','primary_attestation'} & review.keys()):
            raise ValueError('host_checkpoint_review_envelope')
        # Stage/schema/source/acceptance and author provenance are still checked
        # by the unchanged native import, not granted by this routing helper.
    return answer_raw


def dispatch(path, expected_sha256):
    value,_ = read(path,expected_sha256)
    # Emit the exact command so an operator/reviewer need not retype a digest.
    quoted_path = "'"+str(Path(path).resolve()).replace("'","''")+"'"
    command = ('python -m scripts.host_review_task_checkpoint read --checkpoint '
        +quoted_path+' --checkpoint-sha '+expected_sha256)
    return (
        'Current task checkpoint: '+str(Path(path).resolve())+'\n'
        'Expected checkpoint SHA256: '+expected_sha256+'\n'
        'Reviewer: '+value['reviewer_id']+'; purpose: '+value['purpose']+'\n'
        'Run from the backend repository (using its configured Python):\n'+command+'\n'
        'First read this checkpoint with scripts.host_review_task_checkpoint read. '
        'After any context recovery reread the SAME path and SHA; do not locate tasks by search, '
        'old summaries or matching case names. Read the exact referenced task and its full required '
        'materials/policies. Do not read primary notes or other Host judgments. '
        'Before final output run check-answer against this checkpoint; it only validates routing, '
        'never fills or repairs your opinion. Return your own exact JSON as native final. '
        'If checkpoint/task cannot be read or match, report that routing failure; do not resume '
        'another task. No Provider calls, report edits or old-batch submissions.'
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('publish','read','dispatch','check-answer'))
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--task-file',type=Path)
    parser.add_argument('--reviewer-id')
    parser.add_argument('--purpose',choices=('review','routing-probe'),default='review')
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--answer-file',type=Path)
    args = parser.parse_args()
    if args.action == 'publish':
        if not args.task_file or not args.reviewer_id:parser.error('publish requires task-file and reviewer-id')
        print(publish(args.checkpoint,args.task_file,args.reviewer_id,purpose=args.purpose))
    else:
        if not args.checkpoint_sha:parser.error('expected checkpoint-sha required')
        if args.action == 'read':
            value,task = read(args.checkpoint,args.checkpoint_sha)
            print(json.dumps(dict(checkpoint=value,task=task),ensure_ascii=False))
        elif args.action == 'dispatch':print(dispatch(args.checkpoint,args.checkpoint_sha))
        else:
            if not args.answer_file:parser.error('answer-file required')
            print(check_answer(args.checkpoint,args.checkpoint_sha,args.answer_file.read_bytes()).decode('utf-8'))


if __name__ == '__main__':main()

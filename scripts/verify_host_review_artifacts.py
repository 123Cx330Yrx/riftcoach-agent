"""Read only one pinned document task's artifacts, without loading case labels.

Request/response bindings hash the original file bytes, not reserialized JSON.
This helper neither reviews semantics nor certifies native author provenance.
Run the existing full-material reader and native submission gate separately.
"""
import argparse
import json
from pathlib import Path

from app.evaluation.golden_inference_scope_v5 import strict_json
from scripts.host_review_task_checkpoint import digest, read


def verify(checkpoint, checkpoint_sha):
    value, _ = read(checkpoint, checkpoint_sha)
    if value['purpose'] != 'review':
        raise ValueError('host_artifacts_review_only')
    folder = Path(value['task_path']).parent
    binding = value['binding']
    for filename, key in [('issued-request.json', 'request_sha256'),
                          ('response.json', 'response_sha256')]:
        raw = (folder / filename).read_bytes()
        if digest(raw) != binding[key]:
            raise ValueError('host_artifacts_' + key)
        strict_json(raw.decode('utf-8'))
    stage = strict_json((folder / 'stage.json').read_text(encoding='utf-8'))
    if stage['stage'] != binding['stage']:
        raise ValueError('host_artifacts_stage')
    if digest(stage['report'].encode('utf-8')) != binding['report_sha256']:
        raise ValueError('host_artifacts_report_sha256')
    # Same representation as role_task_outcome.stage_identity; do not import
    # a batch builder or its expected labels to calculate a file checksum.
    stage_sha = digest(json.dumps({k: stage[k] for k in ('stage', 'report', 'journal')},
        sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8'))
    return dict(artifact_hashes_verified=True, binding=binding,
        stage_sha256=stage_sha, full_source_review_performed=False,
        native_review_certified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.checkpoint, args.checkpoint_sha), ensure_ascii=False))


if __name__ == '__main__':
    main()

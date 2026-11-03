"""Historical provenance fixtures only; current implementation is tested separately.

Never map a changed current program to an old digest. Materialize the pinned
historical LF text for prior() inventory tests without modifying the checkout.
Only this temporary snapshot uses the existing test-only newline projection.
"""
import hashlib
import json


def materialize(repo, manifest, seal_paths, target):
    archive = json.loads((repo / 'tests/fixtures/document_closed_program_sources.json').read_bytes())
    for name, entry in manifest['source'].items():
        text = archive['source_text_lf'].get(name)
        raw = text.encode('utf-8') if text is not None else (repo / name).read_bytes()
        lf = raw.replace(b'\r\n', b'\n')
        assert hashlib.sha256(lf).hexdigest() == entry['lf_sha256'], name
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(lf)
    for name in seal_paths:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((repo / name).read_bytes())
    return target


def projected_hash(original, snapshot, manifest):
    def read_hash(path):
        try:
            name = path.resolve().relative_to(snapshot.resolve()).as_posix()
        except ValueError:
            return original(path)
        entry = manifest['source'].get(name)
        if entry is not None:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() == entry['lf_sha256']:
                return entry['frozen_raw_sha256']
        return original(path)
    return read_hash

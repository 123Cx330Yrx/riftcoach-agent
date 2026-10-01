"""Real offline Runtime artifacts, tamper checks and interrupted delivery."""
import copy
import json
import socket
from dataclasses import replace
from uuid import UUID

import pytest

from app.evidence.publication import EvidencePublicationIntegrityError, canonical_bytes, sha256_bytes
from app.evidence.publication_store import FileEvidencePublicationStore
from app.product.coach_composition import build_coach_application
from app.product.recent_review_service import RecentReviewApplicationError
from tests.test_coach_application_composition import dependencies, product_request
from tests.test_evidence_publication import context, sources


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network forbidden")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def prepared(tmp_path, *, rejected=False, explicit=True):
    deps = dependencies()
    summary = deps["summary_builder"].summary
    summary["metadata"]["matches_requested"] = summary["request"]["count"] = 5
    for row in summary["matches"]:
        row.update(champion_id=75, queue_id=420, game_version="16.16.804.9184")
    deps["provider"].second_verdict = "fail" if rejected else "pass"
    store = FileEvidencePublicationStore(tmp_path)
    opts = dict(publication_sources=sources(), publication_writer=store) if explicit else {}
    app = build_coach_application(runs_root=tmp_path, **deps, **opts)
    projection = sources().project(copy.deepcopy(summary), routing_region="asia")
    return app, deps, store, projection


@pytest.mark.parametrize("rejected", [False, True])
def test_round_trip_and_same_content_replay(tmp_path, rejected):
    app, deps, store, projection = prepared(tmp_path, rejected=rejected)
    result = app.review(product_request(), run_id=context().run_id, publication_context=context())
    manifest = store.read(context())
    assert manifest.state == "files_ready"
    assert manifest.summary_digest == projection.summary_digest
    assert manifest.bundle.bundle_digest == projection.bundle.digest
    assert manifest.trace == result.trace_reference
    assert (manifest.report is None) is rejected
    assert result.publication_status.value == ("rejected" if rejected else "published")
    assert projection.bundle.data_dragon is None and projection.bundle.gaps
    assert store.write(context(), projection) == manifest
    assert len(deps["summary_builder"].calls) == 1
    for reference in (manifest.summary, manifest.receipt, manifest.trace, manifest.bundle, manifest.report):
        if reference is not None:
            assert sha256_bytes((tmp_path / context().run_id / reference.relative_path).read_bytes()) == reference.sha256
    assert not list(tmp_path.rglob(".publication.*"))


def test_read_pending_snapshot_rebuilds_verified_task_payload(tmp_path):
    app, _, store, projection = prepared(tmp_path)
    app.review(product_request(), run_id=context().run_id, publication_context=context())

    pending = store.read_pending_snapshot(context())

    assert pending.task_id == context().task_id
    assert pending.run_id == context().run_id
    assert pending.owner_id == context().owner_id
    assert pending.refresh_id == "publication-1"
    assert pending.bundle.digest == projection.bundle.digest


@pytest.mark.parametrize("filename", ["evidence_publication_manifest.json", "evidence_bundle.json",
    "api_run_receipt.json", "runtime_trace.json", "manifest.json", "inputs/player_summary.json", "report"])
@pytest.mark.parametrize("damage", ["truncate", "remove"])
def test_damaged_dependency_is_never_accepted(tmp_path, filename, damage):
    app, _, store, _ = prepared(tmp_path)
    app.review(product_request(), run_id=context().run_id, publication_context=context())
    manifest = store.read(context())
    target = tmp_path / context().run_id / (manifest.report.relative_path if filename == "report" else filename)
    target.unlink() if damage == "remove" else target.write_bytes(b'{"private":')
    with pytest.raises(EvidencePublicationIntegrityError) as error:
        store.read(context())
    assert error.value.args == ("evidence_publication_integrity_failed",)
    assert error.value.__context__ is None and error.value.__cause__ is None


@pytest.mark.parametrize("field,value", [("owner_id", "other"), ("run_id", "other"),
    ("task_id", UUID("40000000-0000-0000-0000-000000000001")),
    ("request_fingerprint", "b" * 64)])
def test_foreign_context_and_conflicting_replay(tmp_path, field, value):
    app, _, store, projection = prepared(tmp_path)
    app.review(product_request(), run_id=context().run_id, publication_context=context())
    different = context().model_copy(update={field: value})
    with pytest.raises(EvidencePublicationIntegrityError):
        store.read(different)
    with pytest.raises(EvidencePublicationIntegrityError):
        store.write(different, projection)
    assert store.read(context()).context == context()


def test_interrupted_write_leaves_only_bundle_and_can_resume(tmp_path, monkeypatch):
    app, _, store, projection = prepared(tmp_path, explicit=False)
    app.review(product_request(), run_id=context().run_id)
    original = store._write_once
    def interrupted(target, content):
        if target.name == store.filename:
            raise OSError("private fault")
        original(target, content)
    monkeypatch.setattr(store, "_write_once", interrupted)
    with pytest.raises(EvidencePublicationIntegrityError):
        store.write(context(), projection)
    assert (tmp_path / context().run_id / "evidence_bundle.json").exists()
    assert not (tmp_path / context().run_id / store.filename).exists()
    with pytest.raises(EvidencePublicationIntegrityError):
        store.read(context())
    monkeypatch.setattr(store, "_write_once", original)
    assert store.write(context(), projection) == store.read(context())


def test_changed_projection_and_semantic_bundle_tamper(tmp_path):
    app, deps, store, projection = prepared(tmp_path)
    app.review(product_request(), run_id=context().run_id, publication_context=context())
    with pytest.raises(EvidencePublicationIntegrityError):
        store.write(context(), replace(projection, summary_digest="b" * 64))
    # Even a self-consistent alternative bundle with rehashed sidecar cannot
    # replace the Riot facts belonging to the actual validated input.
    changed = copy.deepcopy(deps["summary_builder"].summary)
    changed["matches"][0]["champion_id"] = 76
    other = sources().project(changed, routing_region="asia")
    from app.evidence.storage import bundle_to_storage_projection
    raw = canonical_bytes(bundle_to_storage_projection(other.bundle))
    directory = tmp_path / context().run_id
    manifest = json.loads((directory / store.filename).read_bytes())
    manifest["bundle"].update(sha256=sha256_bytes(raw), bundle_digest=other.bundle.digest)
    (directory / "evidence_bundle.json").write_bytes(raw)
    (directory / store.filename).write_bytes(canonical_bytes(manifest))
    with pytest.raises(EvidencePublicationIntegrityError):
        store.read(context())


@pytest.mark.parametrize("relative", ["../escape", "/absolute", "C:/escape", "a\\b", "a/../b", "a//b"])
def test_unsafe_dependency_paths(tmp_path, relative):
    store = FileEvidencePublicationStore(tmp_path)
    with pytest.raises(ValueError):
        store._path("run", relative)


@pytest.mark.parametrize("target_name", ["evidence_publication_manifest.json", "evidence_bundle.json", "inputs", "run"])
def test_linked_paths_are_rejected(tmp_path, target_name):
    app, _, store, _ = prepared(tmp_path)
    app.review(product_request(), run_id=context().run_id, publication_context=context())
    target = tmp_path / context().run_id if target_name == "run" else tmp_path / context().run_id / target_name
    backup = target.with_name(target.name + "_backup")
    target.rename(backup)
    try:
        target.symlink_to(backup, target_is_directory=backup.is_dir())
    except OSError:
        backup.rename(target)
        pytest.skip("OS does not grant symlink creation")
    with pytest.raises(EvidencePublicationIntegrityError):
        store.read(context())


@pytest.mark.parametrize("target_name", ["evidence_publication_manifest.json", "evidence_bundle.json", "inputs", "run"])
def test_link_detection_fails_closed_without_os_privilege(tmp_path, monkeypatch, target_name):
    from pathlib import Path
    app, _, store, projection = prepared(tmp_path)
    app.review(product_request(), run_id=context().run_id, publication_context=context())
    target = tmp_path / context().run_id if target_name == "run" else tmp_path / context().run_id / target_name
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == target or original(self))
    with pytest.raises(EvidencePublicationIntegrityError):
        store.read(context())
    with pytest.raises(EvidencePublicationIntegrityError):
        store.write(context(), projection)


def test_source_snapshots_and_explicit_observation_are_reconstructable(tmp_path):
    from datetime import timedelta
    from app.evidence.publication import EvidencePublicationSources
    from app.evidence.storage import bundle_from_storage_projection
    from tests.test_evidence_fusion_vertical import NOW, _static, _patch, _meta
    app, deps, store, _ = prepared(tmp_path)
    summary = deps["summary_builder"].summary
    summary["request"].update(data_dragon_version="15.16.1", data_dragon_language="zh_CN")
    for row in summary["matches"]:
        row["game_version"] = "15.16.1"
    app._publication_sources = EvidencePublicationSources(now=NOW, observed_at=NOW-timedelta(minutes=1),
        data_dragon=_static(), official_patch=_patch(), meta_evidence=(_meta(),))
    app.review(product_request(), run_id=context().run_id, publication_context=context())
    manifest = store.read(context())
    assert manifest.observation_basis == "caller_observed_at"
    bundle = bundle_from_storage_projection(json.loads(
        (tmp_path / context().run_id / manifest.bundle.relative_path).read_bytes()))
    assert bundle.data_dragon == _static() and bundle.official_patch == _patch()
    assert bundle.meta_evidence[0].digest == _meta().digest
    assert bundle.riot_matches[0].observed_at == NOW-timedelta(minutes=1)


def test_manifest_tamper_with_valid_schema_still_fails(tmp_path):
    app, _, store, _ = prepared(tmp_path)
    app.review(product_request(), run_id=context().run_id, publication_context=context())
    target = tmp_path / context().run_id / store.filename
    value = json.loads(target.read_bytes())
    value["summary_digest"] = "b" * 64
    target.write_bytes(canonical_bytes(value))
    with pytest.raises(EvidencePublicationIntegrityError):
        store.read(context())


def test_bundle_damaged_during_delivery_cannot_complete_index(tmp_path, monkeypatch):
    app, _, store, projection = prepared(tmp_path, explicit=False)
    app.review(product_request(), run_id=context().run_id)
    original = store._write_once
    def corrupt(target, content):
        original(target, content)
        if target.name == "evidence_bundle.json":
            target.write_bytes(b"partial")
    monkeypatch.setattr(store, "_write_once", corrupt)
    with pytest.raises(EvidencePublicationIntegrityError):
        store.write(context(), projection)
    assert not (tmp_path / context().run_id / store.filename).exists()

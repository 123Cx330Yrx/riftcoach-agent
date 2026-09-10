import hashlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from app.evaluation import observation_archive as archive


def fixture(tmp_path, monkeypatch, missing_cs=False):
    manual = tmp_path / "review.md"
    manual.write_text("人工复核副本", encoding="utf-8")
    manifest = tmp_path / "manifest.json"; manifest.write_text("{}", encoding="utf-8")
    bundle = tmp_path / "bundle.json"; bundle.write_text(json.dumps({"data_dragon": {"version": "16.17.1", "retrieved_at": "2026-09-10T12:15:20Z"}, "official_patch": {"patch_version": "16.17", "retrieved_at": "2026-09-10T12:15:18Z", "update_id": "riot-patch-26-17"}, "meta_evidence": [{"source": "opgg", "position": "mid", "retrieved_at": "2026-09-10T12:15:25Z"}]}), encoding="utf-8")
    class Store:
        filename = "manifest.json"
        def __init__(self, root): pass
        def _path(self, run_id, name): return manifest if name == self.filename else bundle
        def read(self, context): return verified
    class Manifest:
        context = SimpleNamespace(run_id=archive.RUN_ID)
        @classmethod
        def model_validate_json(cls, raw): return cls()
    verified = SimpleNamespace(summary_digest="summary-digest", trace=SimpleNamespace(sha256="trace"), report=SimpleNamespace(sha256="report"), bundle=SimpleNamespace(relative_path="bundle.json", bundle_digest="bundle", sha256=hashlib.sha256(bundle.read_bytes()).hexdigest()))
    monkeypatch.setattr(archive, "FileEvidencePublicationStore", Store); monkeypatch.setattr(archive, "EvidencePublicationManifest", Manifest)
    rows = [{"match_id":"m1","champion_name":"Vex","role":"MIDDLE","win":True,"cs_per_min":None if missing_cs else 8.0,"damage_per_min":400,"deaths_before_15":1},{"match_id":"m2","champion_name":"Camille","role":"UTILITY","win":False,"cs_per_min":None,"damage_per_min":100,"deaths_before_15":2}]
    def load(*args, **kwargs): return ({"matches": rows}, datetime(2026,9,10,tzinfo=timezone.utc))
    binding = {"run_id":archive.RUN_ID,"reviewed_copy_sha256":hashlib.sha256(manual.read_bytes()).hexdigest(),"original_report_sha256":"report","trace_sha256":"trace","summary_digest":"summary-digest","automated_score":95,"manual_copy_automatically_evaluated":False,"manual_original_accepted":False}
    record = tmp_path / "golden_manual_reviews" / (archive.RUN_ID + ".json"); record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"run_id": archive.RUN_ID, "reviewed_copy_path": str(manual), "reviewed_copy_sha256": binding["reviewed_copy_sha256"], "original_report_sha256": "report", "trace_sha256": "trace", "summary_digest": "summary-digest", "automated_score": 95, "manual_copy_automatically_evaluated": False, "manual_original_accepted": False, "manual_copy_corrected": True}), encoding="utf-8")
    monkeypatch.setattr(archive, "MANUAL_REVIEW_SHA256", binding["reviewed_copy_sha256"]); monkeypatch.setattr(archive, "ORIGINAL_REPORT_SHA256", "report"); monkeypatch.setattr(archive, "TRACE_SHA256", "trace")
    monkeypatch.setattr(archive, "SUMMARY_DIGEST", "summary-digest")
    monkeypatch.setattr(archive, "load_saved_summary", load)
    return manual,verified


def export(tmp_path, monkeypatch, **kwargs):
    manual, _ = fixture(tmp_path, monkeypatch, **kwargs)
    return archive.export_observation(runs_root=tmp_path / "runs", manual_review=manual, output=tmp_path / 'out.json', exported_at='2026-09-11T00:00:00+00:00'), manual


def test_shape_and_source_time(tmp_path, monkeypatch):
    value, _ = export(tmp_path, monkeypatch)
    assert value["report"]["kind"] == "human_reviewed" and value["report"]["automated_score"] == 95
    assert value["summary"]["positions"] == [{"position":"mid","games":1,"champions":["Vex"],"cs_per_min":8.0},{"position":"support","games":1,"champions":["Camille"],"cs_per_min":None}]
    assert value["evidence"]["sources"][-1]["observed_at"].startswith("2026-09-10T12:15:25")
    assert json.loads((tmp_path/"out.json").read_text(encoding="utf-8")) == value


def test_missing_cs_is_null(tmp_path, monkeypatch):
    value, _ = export(tmp_path, monkeypatch, missing_cs=True)
    assert value["summary"]["positions"][0]["cs_per_min"] is None


def test_create_only(tmp_path, monkeypatch):
    export(tmp_path, monkeypatch)
    with pytest.raises(FileExistsError, match="observation_archive_exists"):
        export(tmp_path, monkeypatch)


def test_manual_tamper_and_size(tmp_path, monkeypatch):
    manual,_ = fixture(tmp_path, monkeypatch)
    manual.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="observation_archive_manual_changed"):
        archive.export_observation(runs_root=tmp_path / "runs", manual_review=manual, output=tmp_path/"x.json")
    huge = tmp_path/"huge.md"; huge.write_bytes(b"x" * (archive.MAX_BYTES + 1))
    with pytest.raises(ValueError, match="observation_archive_too_large"):
        archive.export_observation(runs_root=tmp_path / "runs", manual_review=huge, output=tmp_path/"x.json")





@pytest.mark.parametrize("field", ["run_id", "trace_sha256", "original_report_sha256", "reviewed_copy_sha256", "manual_copy_corrected", "automated_score"])
def test_rejects_wrong_manual_binding(tmp_path, monkeypatch, field):
    manual, _ = fixture(tmp_path, monkeypatch)
    record = tmp_path / "golden_manual_reviews" / (archive.RUN_ID + ".json")
    value = json.loads(record.read_text(encoding="utf-8"))
    value[field] = "wrong"
    record.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="observation_archive_manual_binding_invalid"):
        archive.export_observation(runs_root=tmp_path / "runs", manual_review=manual, output=tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


@pytest.mark.parametrize("field", ["summary", "trace", "report", "bundle"])
def test_rejects_wrong_verified_source(tmp_path, monkeypatch, field):
    manual, verified = fixture(tmp_path, monkeypatch)
    if field == "summary":
        verified.summary_digest = "wrong"
    else:
        getattr(verified, field).sha256 = "wrong"
    with pytest.raises(ValueError):
        archive.export_observation(runs_root=tmp_path / "runs", manual_review=manual, output=tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


def test_relative_manual_path_and_symlink_rejection(tmp_path, monkeypatch):
    manual, _ = fixture(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    archive.export_observation(runs_root=tmp_path / "runs", manual_review=manual.name, output=tmp_path / "out.json")
    link = tmp_path / "link.md"
    try:
        link.symlink_to(manual)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="observation_archive_path_invalid"):
        archive.export_observation(runs_root=tmp_path / "runs", manual_review=link, output=tmp_path / "link.json")

"""Opt-in Chromium -> cookie API -> disposable SQL -> actual Worker.

Only external source/model IO is scripted. No HTTP API response interception.
Run with RIFTCOACH_PRODUCT_BROWSER_CHECK=1 and a disposable test database;
the imported SQL fixture recreates that database's schema.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import socket
import subprocess
import threading
import time
from uuid import uuid4

import pytest
import sqlalchemy as sa
import uvicorn

from app.memory.models import RelationshipRole
from app.persistence.memory_context_repository import PostgresMemoryContextRepository
from app.persistence.player_records import PlayerAliasRecord, PlayerLinkTaskRecord
from app.persistence.terminal_turn_writer import PostgresTerminalTurnWriter
from app.product import sol_contract as product
from app.tasks.sse import TaskEventStreamService
from scripts.run_local_observation_api import create_local_observation_app
from tests.memory_candidate_postgres_support import seed_conversation
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, setup_worker

pytestmark = pytest.mark.skipif(os.getenv("RIFTCOACH_PRODUCT_BROWSER_CHECK") != "1",
    reason="explicit disposable browser/SQL check only")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("action", ["resume", "retry", "cancel"])
def test_browser_to_product_worker(continued_api, tmp_path, monkeypatch, action):
    repo = continued_api[2]
    factory = repo._session_factory
    subject, relationship, _ = seed_conversation(factory, number=901,
        owner_id="owner-1", role=RelationshipRole.OBSERVED)
    now = datetime.now(timezone.utc)
    with factory.begin() as session:
        session.add(PlayerAliasRecord(player_alias_id=uuid4(), player_subject_id=subject,
            routing_region="asia", game_name="DemoPlayer", tag_line="TEST",
            normalized_riot_id_hash="a" * 64, first_seen_at=now, last_seen_at=now))
        session.add(PlayerLinkTaskRecord(link_task_id=uuid4(), task_kind="player_link",
            schema_version="1.0", owner_id="owner-1", worker_id="browser-fixture",
            idempotency_key="browser-profile", request_fingerprint="a" * 64,
            game_name="DemoPlayer", tag_line="TEST", routing_region="asia",
            relationship_role="observed", alias_hash="a" * 64, status="succeeded",
            created_at=now, updated_at=now, claimed_at=now, finished_at=now,
            confirmed_game_name="DemoPlayer", confirmed_tag_line="TEST",
            player_subject_id=subject, relationship_id=relationship))
    app = create_local_observation_app({
        "DATABASE_URL": os.environ["RIFTCOACH_TEST_DATABASE_URL"],
        "RIFTCOACH_API_PROFILE": "local", "RIFTCOACH_LOCAL_OWNER_ID": "owner-1",
        "RIFTCOACH_RUNS_ROOT": str(tmp_path), "RIFTCOACH_TASK_PUBLICATION_MODE": "evidence_bound_v1",
    })
    make, summary, _, requests = setup_worker(tmp_path, monkeypatch, repo,
        statuses=(524,) if action == "retry" else (), contract=product, profile=product.WORKER_PROFILE,
        memory_repository=PostgresMemoryContextRepository(factory),
        terminal_turn_writer=PostgresTerminalTurnWriter(factory, runs_root=tmp_path))
    worker, route = make()
    if action != "retry":
        route.candidate.max_new_models = 3
    stopping = threading.Event()
    worker_errors = []
    outcomes = []
    stream_frames = []
    original_stream = TaskEventStreamService.stream

    def observed_stream(self, **kwargs):
        for frame in original_stream(self, **kwargs):
            stream_frames.append(frame)
            yield frame
    monkeypatch.setattr(TaskEventStreamService, "stream", observed_stream)

    def run_worker():
        nonlocal worker
        try:
            while not stopping.is_set():
                result = worker.run_once()
                if result.status.value != "idle":
                    outcomes.append(result.status.value)
                    worker, _ = make()
                stopping.wait(0.15)
        except BaseException as error:
            worker_errors.append(type(error).__name__)

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    api_thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    out_root = Path(os.environ.get("RIFTCOACH_BROWSER_OUTPUT", str(tmp_path / "browser")))
    out = out_root / action
    out.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "HOME", "PLAYWRIGHT_BROWSERS_PATH"}}
    env.update(RIFTCOACH_BROWSER_API_PORT=str(port), RIFTCOACH_BROWSER_PROFILE=str(relationship),
        RIFTCOACH_BROWSER_ACTION=action, RIFTCOACH_BROWSER_OUTPUT=str(out))
    api_thread.start()
    try:
        for _ in range(100):
            if server.started: break
            time.sleep(0.05)
        assert server.started
        worker_thread.start()
        result = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
            "--config=playwright.product.config.ts"], cwd=ROOT / "web", env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", timeout=150)
        (out / "playwright.stdout.txt").write_text(result.stdout, encoding="utf-8")
        with factory() as session:
            states = [dict(row) for row in session.execute(sa.text(
                "SELECT status, terminal_reason FROM review_tasks")).mappings()]
        (out / "attempt-state.json").write_text(json.dumps(dict(outcomes=outcomes,
            worker_errors=worker_errors, tasks=states, requests=requests, stream_frames=stream_frames), ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        assert result.returncode == 0, f"browser failed; see {out / 'playwright.stdout.txt'}"
        assert not worker_errors, worker_errors
        assert summary.reads == 1
        assert summary.calls[0][0] == "build_by_puuid"
        assert summary.calls[0][1]["puuid"] == "PUUID_MEMORY_901"
        with factory() as session:
            assert session.scalar(sa.text("SELECT count(*) FROM review_tasks")) == 1
            assert session.scalar(sa.text("SELECT count(*) FROM training_progress_events")) == 0
            assert session.scalar(sa.text("SELECT count(*) FROM conversation_messages WHERE role = 'assistant'")) == (0 if action == "cancel" else 1)
        nonempty = [calls for calls in requests if calls]
        assert nonempty == ([[524], [200, 200]] if action == "retry" else [[200]] if action == "cancel" else [[200], [200]])
        (out / "worker-proof.json").write_text(json.dumps(dict(action=action,
            outcomes=outcomes, source_reads=summary.reads, source_method=summary.calls[0][0],
            scripted_reviewer_statuses=nonempty, real_external_requests=0,
            tasks=1, training_progress_events=0, assistant_turns=0 if action == "cancel" else 1),
            ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    finally:
        stopping.set()
        if worker_thread.is_alive(): worker_thread.join(20)
        server.should_exit = True
        api_thread.join(10)
        listener.close()
        assert not worker_thread.is_alive() and not api_thread.is_alive()

from __future__ import annotations

import json

import copy
import pytest
from pydantic import ValidationError

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.evidence_models import (
    EvidencePublicProjectionResponse,
    EvidenceSnapshotResponse,
)
from app.api.task_models import ReadinessResult
from app.evidence.service import EvidenceProductServiceError
from app.evidence.storage import project_evidence_snapshot, project_product_run_state
from tests.player_link_api_stubs import UnusedPlayerLinkService
from tests.test_evidence_product_service import NOW, RUN_ID, snapshot, task


class Tasks:
    def create(self, _command):
        raise AssertionError("test does not create tasks")

    def get_task(self, **_kwargs):
        return task()

    def get_task_by_run_id(self, **_kwargs):
        return task()


class Query:
    def get_run(self, _run_id):
        raise AssertionError("evidence endpoints do not read run artifacts")

    def get_report(self, _run_id):
        raise AssertionError("evidence endpoints do not read report bodies")


class Readiness:
    def check(self):
        return ReadinessResult.ready()


class Products:
    def __init__(self) -> None:
        self.error: EvidenceProductServiceError | None = None
        self.calls: list[tuple[str, str, str]] = []

    def get_evidence(self, *, owner_id: str, run_id: str):
        self.calls.append(("evidence", owner_id, run_id))
        if self.error is not None:
            raise self.error
        return project_evidence_snapshot(snapshot(), now=NOW)

    def get_product_state(self, *, owner_id: str, run_id: str):
        self.calls.append(("state", owner_id, run_id))
        if self.error is not None:
            raise self.error
        return project_product_run_state(task(), snapshot(), now=NOW)


def client(products: Products | None) -> TestClient:
    return TestClient(
        create_app(
            task_service=Tasks(),
            player_link_service=UnusedPlayerLinkService(),
            query_service=Query(),
            actor_provider=StaticActorContextProvider(
                owner_id="owner-1",
                profile="test",
            ),
            readiness_probe=Readiness(),
            evidence_product_service=products,
        )
    )


def test_evidence_and_product_state_are_owner_scoped_safe_dtos() -> None:
    products = Products()
    http = client(products)

    evidence = http.get(f"/runs/{RUN_ID}/evidence")
    state = http.get(f"/runs/{RUN_ID}/product-state")

    assert evidence.status_code == state.status_code == 200
    assert products.calls == [
        ("evidence", "owner-1", RUN_ID),
        ("state", "owner-1", RUN_ID),
    ]
    evidence_body = evidence.json()
    assert evidence_body["revision"] == 3
    assert evidence_body["freshness"] == "current"
    assert evidence_body["bundle_disposition"] == "complete"
    assert state.json()["state"] == "published"
    serialized = (evidence.text + state.text).lower()
    for forbidden in (
        "owner_id",
        "refresh_id",
        "request_payload",
        "puuid",
        "prompt",
        "raw_response",
        "api_key",
        "worker_id",
        "checkpoint_reference",
    ):
        assert forbidden not in serialized


def test_product_api_maps_only_allowlisted_error_codes() -> None:
    products = Products()
    http = client(products)
    cases = (
        ("run_not_found", 404, "run_not_found"),
        ("evidence_not_available", 409, "evidence_not_available"),
        ("evidence_integrity_failed", 500, "evidence_integrity_failed"),
        ("evidence_unavailable", 503, "evidence_unavailable"),
    )

    for internal, status, public in cases:
        products.error = EvidenceProductServiceError(internal)
        response = http.get(f"/runs/{RUN_ID}/evidence")
        assert response.status_code == status
        assert response.json() == {"code": public, "run_id": RUN_ID}


def test_unbound_product_service_fails_closed_and_openapi_is_body_free() -> None:
    http = client(None)

    response = http.get(f"/runs/{RUN_ID}/product-state")
    openapi = http.get("/openapi.json").json()
    schema = json.dumps(
        {
            "paths": {
                name: openapi["paths"][name]
                for name in (
                    "/runs/{run_id}/evidence",
                    "/runs/{run_id}/product-state",
                )
            },
            "models": {
                name: openapi["components"]["schemas"][name]
                for name in ("EvidenceSnapshotResponse", "ProductStateResponse")
            },
        },
        sort_keys=True,
    ).lower()

    assert response.status_code == 503
    assert response.json() == {"code": "evidence_unavailable", "run_id": RUN_ID}
    assert f"/runs/{{run_id}}/evidence" in schema
    assert f"/runs/{{run_id}}/product-state" in schema
    for forbidden in ("owner_id", "refresh_id", "puuid", "raw_response", "api_key"):
        assert forbidden not in schema


def test_evidence_openapi_exposes_concrete_nested_projection_without_wire_drift() -> None:
    http = client(Products())

    body = http.get(f"/runs/{RUN_ID}/evidence").json()
    openapi = http.get("/openapi.json").json()
    snapshot_schema = openapi["components"]["schemas"][
        "EvidenceSnapshotResponse"
    ]
    projection_schema = openapi["components"]["schemas"][
        "EvidencePublicProjectionResponse"
    ]

    assert snapshot_schema["properties"]["projection"] == {
        "$ref": "#/components/schemas/EvidencePublicProjectionResponse"
    }
    assert set(projection_schema["properties"]) == {
        "schema_version",
        "bundle_digest",
        "disposition",
        "confidence",
        "claims",
        "matches",
        "joins",
        "conflicts",
        "gaps",
        "sources",
    }
    expected_projection = project_evidence_snapshot(
        snapshot(), now=NOW
    ).projection
    assert body["projection"] == expected_projection
    assert set(body["projection"]["sources"]) == {
        "riot_official",
        "data_dragon",
        "riot_patch",
        "opgg",
    }


@pytest.mark.parametrize("tamper", ("extra", "enum", "digest"))
def test_typed_evidence_projection_rejects_schema_drift(tamper: str) -> None:
    payload = copy.deepcopy(
        project_evidence_snapshot(snapshot(), now=NOW).projection
    )
    if tamper == "extra":
        payload["raw_body"] = "forbidden"
    elif tamper == "enum":
        payload["confidence"] = "certain"
    else:
        payload["bundle_digest"] = "not-a-digest"

    with pytest.raises(ValidationError):
        EvidencePublicProjectionResponse.model_validate(payload)


def test_typed_evidence_snapshot_rejects_bad_outer_timestamp() -> None:
    response = EvidenceSnapshotResponse.from_view(
        project_evidence_snapshot(snapshot(), now=NOW)
    )
    payload = response.model_dump(mode="python")
    payload["stored_at"] = "2026-08-23"

    with pytest.raises(ValidationError):
        EvidenceSnapshotResponse.model_validate(payload)

"""Restricted, transport-neutral RiftCoach MCP Server.

The server owns MCP envelope/session semantics only.  Product behavior is
provided by an injected, owner-scoped Application Facade; Repository, HTTP,
Provider, Prompt, and Artifact bodies never cross this boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from jsonschema import Draft202012Validator
from pydantic import BaseModel

from app.api.actor import ActorContext, ActorContextProvider
from app.harness.run_ids import normalize_run_id
from app.mcp.models import (
    JSONRPC_VERSION,
    McpContractLimits,
    McpImplementation,
    McpInitializeRequest,
    McpToolCallRequest,
    McpToolCatalog,
    McpToolDescriptor,
)
from app.mcp.errors import (
    McpErrorInfo,
    McpToolCallError,
    McpTransportError,
    McpTransportTimeout,
)


MCP_SERVER_PROTOCOL_VERSION = "2025-06-18"
MCP_SERVER_IMPLEMENTATION = McpImplementation(
    name="RiftCoach MCP Server",
    version="1.0.0",
)
MCP_SERVER_TOOL_NAMES = (
    "riftcoach.knowledge_search",
    "riftcoach.recent_summary",
    "riftcoach.report_evaluation",
    "riftcoach.single_match_review",
)
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_FACADE_CODES = frozenset(
    {
        "owner_scope_denied",
        "not_found",
        "not_published",
        "integrity_failed",
        "service_unavailable",
        "unsupported",
    }
)


class McpFacadeError(RuntimeError):
    """A stable, body-free failure from the Application Facade."""

    def __init__(self, code: str) -> None:
        if code not in _SAFE_FACADE_CODES:
            raise ValueError("facade error code is not allowlisted")
        self.code = code
        super().__init__(code)


class McpApplicationFacade(Protocol):
    """Read-only Application Service port used by the MCP Server."""

    def recent_summary(self, *, actor: ActorContext, run_id: str) -> Mapping[str, Any]: ...

    def single_match_review(self, *, actor: ActorContext, run_id: str) -> Mapping[str, Any]: ...

    def knowledge_search(
        self,
        *,
        actor: ActorContext,
        query: str,
        top_k: int,
        filters: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def report_evaluation(self, *, actor: ActorContext, run_id: str) -> Mapping[str, Any]: ...


class QueryMcpApplicationFacade:
    """Default read-only facade composed from existing query/service ports.

    The constructor deliberately accepts ports rather than repositories.  A
    deployment can therefore bind the same owner-scoped services used by the
    HTTP API without giving the MCP boundary a second persistence path.
    """

    def __init__(
        self,
        *,
        task_service: Any,
        run_query: Any,
        knowledge_provider: Any,
    ) -> None:
        for name in ("get_task_by_run_id",):
            if not callable(getattr(task_service, name, None)):
                raise TypeError("task_service must expose get_task_by_run_id()")
        for name in (
            "get_run",
            "get_recent_summary",
            "get_single_match_review",
        ):
            if not callable(getattr(run_query, name, None)):
                raise TypeError(f"run_query must expose {name}()")
        if not callable(getattr(knowledge_provider, "search", None)):
            raise TypeError("knowledge_provider must expose search()")
        self._task_service = task_service
        self._run_query = run_query
        self._knowledge_provider = knowledge_provider

    def _require_owned_run(self, *, actor: ActorContext, run_id: str) -> None:
        try:
            task = self._task_service.get_task_by_run_id(
                owner_id=actor.owner_id,
                run_id=run_id,
            )
        except Exception as exc:
            # The underlying service owns its detailed error mapping.  The
            # MCP facade only exposes a stable not-found/availability code.
            code = getattr(exc, "code", None)
            safe_code = (
                "not_found"
                if code in {"run_not_found", "task_not_found"}
                else "service_unavailable"
            )
            raise McpFacadeError(
                safe_code
            ) from None
        if getattr(task, "run_id", run_id) != run_id:
            raise McpFacadeError("integrity_failed")

    def _owned_query(
        self,
        *,
        actor: ActorContext,
        run_id: str,
        method_name: str,
    ) -> Any:
        self._require_owned_run(actor=actor, run_id=run_id)
        try:
            return getattr(self._run_query, method_name)(run_id)
        except Exception as exc:
            code = getattr(exc, "code", None)
            mapped = {
                "run_not_found": "not_found",
                "report_not_available": "not_published",
                "run_integrity_failed": "integrity_failed",
            }.get(code, "service_unavailable")
            raise McpFacadeError(mapped) from None

    @staticmethod
    def _dump(value: Any) -> Mapping[str, Any]:
        return _as_mapping(value)

    def recent_summary(self, *, actor: ActorContext, run_id: str) -> Mapping[str, Any]:
        return self._dump(
            self._owned_query(
                actor=actor,
                run_id=run_id,
                method_name="get_recent_summary",
            )
        )

    def single_match_review(self, *, actor: ActorContext, run_id: str) -> Mapping[str, Any]:
        return self._dump(
            self._owned_query(
                actor=actor,
                run_id=run_id,
                method_name="get_single_match_review",
            )
        )

    def knowledge_search(
        self,
        *,
        actor: ActorContext,
        query: str,
        top_k: int,
        filters: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        del actor
        from app.rag.models import KnowledgeQuery

        try:
            result = self._knowledge_provider.search(
                KnowledgeQuery(text=query, top_k=top_k, filters=filters)
            )
        except Exception:
            raise McpFacadeError("service_unavailable") from None
        hits = getattr(result, "hits", ())
        attributions = []
        for hit in hits:
            metadata = getattr(hit, "metadata", None)
            if metadata is None:
                raise McpFacadeError("integrity_failed")
            attributions.append(
                {
                    "chunk_id": getattr(hit, "chunk_id", None),
                    "source_id": getattr(metadata, "source_id", None),
                    "title": getattr(metadata, "title", None),
                    "version": getattr(metadata, "version", None),
                }
            )
        return {
            "provider": getattr(result, "provider", "unknown"),
            "abstained": getattr(result, "abstained", False),
            "count": len(attributions),
            "attributions": attributions,
        }

    def report_evaluation(self, *, actor: ActorContext, run_id: str) -> Mapping[str, Any]:
        raw = dict(
            self._dump(
                self._owned_query(
                    actor=actor,
                    run_id=run_id,
                    method_name="get_run",
                )
            )
        )
        publication = raw.get("publication_status")
        if publication not in {"published", "degraded"}:
            raise McpFacadeError("not_published")
        return {
            "run_id": raw.get("run_id"),
            "publication_status": publication,
            "evaluation_status": "passed" if publication == "published" else "degraded",
            "score_available": False,
        }


def _object_schema(
    properties: Mapping[str, Any],
    required: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }


_RUN_INPUT = _object_schema(
    {"run_id": {"type": "string", "pattern": _RUN_ID_PATTERN.pattern}},
    ("run_id",),
)
_KNOWLEDGE_INPUT = _object_schema(
    {
        "query": {"type": "string", "minLength": 1, "maxLength": 512},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        "filters": _object_schema(
            {
                "version": {"type": "string", "maxLength": 64},
                "position": {"type": "string", "maxLength": 32},
                "as_of": {
                    "type": "string",
                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                },
            },
            (),
        ),
    },
    ("query", "top_k"),
)
_RUN_OUTPUT_PROPERTIES = {
    "schema_version": {"const": "1.0"},
    "run_id": {"type": "string", "pattern": _RUN_ID_PATTERN.pattern},
    "status": {"const": "completed"},
    "publication_status": {"enum": ["published", "degraded"]},
    "terminal_reason": {
        "type": "string",
        "pattern": r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$",
        "maxLength": 128,
    },
}
_AVERAGES_OUTPUT = _object_schema(
    {
        "kda": {"type": "number", "minimum": 0},
        "cs_per_min": {"type": "number", "minimum": 0},
        "gold_per_min": {"type": "number", "minimum": 0},
        "damage_per_min": {"type": "number", "minimum": 0},
        "vision_score": {"type": "number", "minimum": 0},
        "kill_participation_percent": {"type": "number", "minimum": 0, "maximum": 100},
        "damage_share_percent": {"type": "number", "minimum": 0, "maximum": 100},
        "gold_share_percent": {"type": "number", "minimum": 0, "maximum": 100},
        "deaths_before_15": {"type": "number", "minimum": 0},
    },
    (
        "kda",
        "cs_per_min",
        "gold_per_min",
        "damage_per_min",
        "vision_score",
        "kill_participation_percent",
        "damage_share_percent",
        "gold_share_percent",
        "deaths_before_15",
    ),
)
_COMPARISON_ROW_OUTPUT = _object_schema(
    {
        "cs_per_min": {"type": "number", "minimum": 0},
        "gold_per_min": {"type": "number", "minimum": 0},
        "damage_per_min": {"type": "number", "minimum": 0},
        "vision_score": {"type": "number", "minimum": 0},
        "deaths_before_15": {"type": "number", "minimum": 0},
    },
    (
        "cs_per_min",
        "gold_per_min",
        "damage_per_min",
        "vision_score",
        "deaths_before_15",
    ),
)
_RECENT_OUTPUT = _object_schema(
    {
        **_RUN_OUTPUT_PROPERTIES,
        "skill_name": {"const": "recent-form-review"},
        "skill_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "report_available": {"const": True},
        "games_analyzed": {"type": "integer", "minimum": 1, "maximum": 100},
        "wins": {"type": "integer", "minimum": 0, "maximum": 100},
        "losses": {"type": "integer", "minimum": 0, "maximum": 100},
        "win_rate": {"type": "number", "minimum": 0, "maximum": 100},
        "main_role": {"type": "string", "minLength": 1, "maxLength": 64},
        "main_champions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 64},
        },
        "averages": _AVERAGES_OUTPUT,
        "win_loss_comparison": _object_schema(
            {"wins": _COMPARISON_ROW_OUTPUT, "losses": _COMPARISON_ROW_OUTPUT},
            ("wins", "losses"),
        ),
    },
    (
        "schema_version",
        "run_id",
        "skill_name",
        "skill_version",
        "status",
        "publication_status",
        "terminal_reason",
        "report_available",
        "games_analyzed",
        "wins",
        "losses",
        "win_rate",
        "main_role",
        "main_champions",
        "averages",
        "win_loss_comparison",
    ),
)
_SINGLE_OUTPUT = _object_schema(
    {
        **_RUN_OUTPUT_PROPERTIES,
        "skill_name": {"const": "single-match-review"},
        "skill_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "review_available": {"const": True},
        "review_sha256": {"type": "string", "pattern": r"^[0-9a-f]{64}$"},
    },
    (
        "schema_version",
        "run_id",
        "skill_name",
        "skill_version",
        "status",
        "publication_status",
        "terminal_reason",
        "review_available",
        "review_sha256",
    ),
)
_KNOWLEDGE_OUTPUT = _object_schema(
    {
        "schema_version": {"const": "1.0"},
        "provider": {"type": "string", "maxLength": 128},
        "abstained": {"type": "boolean"},
        "count": {"type": "integer", "minimum": 0, "maximum": 20},
        "attributions": {
            "type": "array",
            "maxItems": 20,
            "items": _object_schema(
                {
                    "chunk_id": {"type": "string", "maxLength": 128},
                    "source_id": {"type": "string", "maxLength": 256},
                    "title": {"type": "string", "maxLength": 512},
                    "version": {"type": ["string", "null"], "maxLength": 64},
                },
                ("chunk_id", "source_id", "title", "version"),
            ),
        },
    },
    ("schema_version", "provider", "abstained", "count", "attributions"),
)
_EVALUATION_OUTPUT = _object_schema(
    {
        "schema_version": {"const": "1.0"},
        "run_id": {"type": "string", "pattern": _RUN_ID_PATTERN.pattern},
        "publication_status": {"enum": ["published", "degraded"]},
        "evaluation_status": {"enum": ["passed", "degraded"]},
        "score_available": {"const": False},
    },
    ("schema_version", "run_id", "publication_status", "evaluation_status", "score_available"),
)


@dataclass(frozen=True)
class _ToolSpec:
    name: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]

    def descriptor(self) -> McpToolDescriptor:
        canonical = json.dumps(
            {"inputSchema": self.input_schema, "outputSchema": self.output_schema},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return McpToolDescriptor(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            schema_digest=hashlib.sha256(canonical).hexdigest(),
            annotations={
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )


_TOOL_SPECS = (
    _ToolSpec(
        name="riftcoach.recent_summary",
        description="Read an owner-scoped summary of an existing RiftCoach run.",
        input_schema=_RUN_INPUT,
        output_schema=_RECENT_OUTPUT,
    ),
    _ToolSpec(
        name="riftcoach.single_match_review",
        description="Read an owner-scoped summary of an existing single-match review.",
        input_schema=_RUN_INPUT,
        output_schema=_SINGLE_OUTPUT,
    ),
    _ToolSpec(
        name="riftcoach.knowledge_search",
        description="Search attributable RiftCoach knowledge without exposing document bodies.",
        input_schema=_KNOWLEDGE_INPUT,
        output_schema=_KNOWLEDGE_OUTPUT,
    ),
    _ToolSpec(
        name="riftcoach.report_evaluation",
        description="Read the verified evaluation/publication status of an existing report.",
        input_schema=_RUN_INPUT,
        output_schema=_EVALUATION_OUTPUT,
    ),
)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _descriptor_wire(descriptor: McpToolDescriptor) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": descriptor.name,
        "description": descriptor.description,
        "inputSchema": _thaw(descriptor.input_schema),
        "outputSchema": _thaw(descriptor.output_schema),
    }
    if descriptor.annotations is not None:
        payload["annotations"] = _thaw(descriptor.annotations)
    return payload


def _rpc_error(request_id: str | int | None, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _tool_error(
    request_id: str | int,
    code: str,
) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": "RiftCoach tool failed."}],
            "isError": True,
            "_meta": {"errorCode": code},
        },
    }


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise McpFacadeError("integrity_failed")
    return value


def _run_projection_base(
    value: Any,
    *,
    expected_skill: str,
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    raw = _as_mapping(value)
    run_id = raw.get("run_id")
    try:
        normalized_run_id = normalize_run_id(run_id)
    except (TypeError, ValueError):
        raise McpFacadeError("integrity_failed") from None
    status = raw.get("status", raw.get("runtime_status"))
    publication = raw.get("publication_status")
    terminal_reason = raw.get("terminal_reason")
    skill_name = raw.get("skill_name")
    skill_version = raw.get("skill_version")
    if status != "completed":
        raise McpFacadeError("integrity_failed")
    if publication not in {"published", "degraded"}:
        raise McpFacadeError("integrity_failed")
    if (
        not isinstance(terminal_reason, str)
        or len(terminal_reason) > 128
        or re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", terminal_reason) is None
    ):
        raise McpFacadeError("integrity_failed")
    if (
        skill_name != expected_skill
        or not isinstance(skill_version, str)
        or re.fullmatch(r"\d+\.\d+\.\d+", skill_version) is None
    ):
        raise McpFacadeError("integrity_failed")
    return raw, {
        "schema_version": "1.0",
        "run_id": normalized_run_id,
        "skill_name": skill_name,
        "skill_version": skill_version,
        "status": status,
        "publication_status": publication,
        "terminal_reason": terminal_reason,
    }


def _project_recent_summary(value: Any) -> dict[str, Any]:
    raw, result = _run_projection_base(
        value,
        expected_skill="recent-form-review",
    )
    if raw.get("report_available") is not True:
        raise McpFacadeError("integrity_failed")
    champions = raw.get("main_champions")
    averages = _as_mapping(raw.get("averages"))
    comparison = _as_mapping(raw.get("win_loss_comparison"))
    wins = _as_mapping(comparison.get("wins"))
    losses = _as_mapping(comparison.get("losses"))
    if not isinstance(champions, (list, tuple)):
        raise McpFacadeError("integrity_failed")
    average_fields = (
        "kda",
        "cs_per_min",
        "gold_per_min",
        "damage_per_min",
        "vision_score",
        "kill_participation_percent",
        "damage_share_percent",
        "gold_share_percent",
        "deaths_before_15",
    )
    comparison_fields = (
        "cs_per_min",
        "gold_per_min",
        "damage_per_min",
        "vision_score",
        "deaths_before_15",
    )
    result.update(
        {
            "report_available": True,
            "games_analyzed": raw.get("games_analyzed"),
            "wins": raw.get("wins"),
            "losses": raw.get("losses"),
            "win_rate": raw.get("win_rate"),
            "main_role": raw.get("main_role"),
            "main_champions": list(champions),
            "averages": {field: averages.get(field) for field in average_fields},
            "win_loss_comparison": {
                "wins": {field: wins.get(field) for field in comparison_fields},
                "losses": {field: losses.get(field) for field in comparison_fields},
            },
        }
    )
    games = result["games_analyzed"]
    win_count = result["wins"]
    loss_count = result["losses"]
    if (
        isinstance(games, bool)
        or not isinstance(games, int)
        or isinstance(win_count, bool)
        or not isinstance(win_count, int)
        or isinstance(loss_count, bool)
        or not isinstance(loss_count, int)
        or win_count + loss_count != games
    ):
        raise McpFacadeError("integrity_failed")
    return result


def _project_single_match_review(value: Any) -> dict[str, Any]:
    raw, result = _run_projection_base(
        value,
        expected_skill="single-match-review",
    )
    digest = raw.get("review_sha256")
    if (
        raw.get("review_available") is not True
        or not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise McpFacadeError("integrity_failed")
    result.update({"review_available": True, "review_sha256": digest})
    return result


def _project_knowledge(value: Any) -> dict[str, Any]:
    raw = _as_mapping(value)
    provider = raw.get("provider")
    abstained = raw.get("abstained")
    if not isinstance(provider, str) or len(provider) > 128 or not isinstance(abstained, bool):
        raise McpFacadeError("integrity_failed")
    rows = raw.get("attributions")
    if rows is None:
        rows = raw.get("chunks", ())
    if not isinstance(rows, (list, tuple)) or len(rows) > 20:
        raise McpFacadeError("integrity_failed")
    attributions: list[dict[str, Any]] = []
    for row in rows:
        item = _as_mapping(row)
        chunk_id = item.get("chunk_id")
        source_id = item.get("source_id")
        title = item.get("title")
        version = item.get("version")
        if not all(isinstance(part, str) for part in (chunk_id, source_id, title)):
            raise McpFacadeError("integrity_failed")
        if version is not None and not isinstance(version, str):
            raise McpFacadeError("integrity_failed")
        if (
            len(chunk_id) > 128
            or len(source_id) > 256
            or len(title) > 512
            or version is not None
            and len(version) > 64
        ):
            raise McpFacadeError("integrity_failed")
        attributions.append(
            {
                "chunk_id": chunk_id,
                "source_id": source_id,
                "title": title,
                "version": version,
            }
        )
    count = raw.get("count", len(attributions))
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 20:
        raise McpFacadeError("integrity_failed")
    if count != len(attributions) or (abstained and attributions):
        raise McpFacadeError("integrity_failed")
    return {
        "schema_version": "1.0",
        "provider": provider,
        "abstained": abstained,
        "count": count,
        "attributions": attributions,
    }


def _project_evaluation(value: Any) -> dict[str, Any]:
    raw = _as_mapping(value)
    try:
        run_id = normalize_run_id(raw.get("run_id"))
    except (TypeError, ValueError):
        raise McpFacadeError("integrity_failed") from None
    publication = raw.get("publication_status")
    evaluation_status = raw.get("evaluation_status")
    score_available = raw.get("score_available")
    if publication not in {"published", "degraded"}:
        raise McpFacadeError("integrity_failed")
    if evaluation_status not in {"passed", "degraded"}:
        raise McpFacadeError("integrity_failed")
    if score_available is not False:
        raise McpFacadeError("integrity_failed")
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "publication_status": publication,
        "evaluation_status": evaluation_status,
        "score_available": False,
    }


class RiftCoachMcpServer:
    """Build sessions for a restricted, read-only RiftCoach MCP facade."""

    def __init__(
        self,
        *,
        facade: McpApplicationFacade,
        actor_provider: ActorContextProvider,
        limits: McpContractLimits | None = None,
    ) -> None:
        if facade is None:
            raise TypeError("facade is required")
        if not callable(actor_provider):
            raise TypeError("actor_provider must be callable")
        for name in MCP_SERVER_TOOL_NAMES:
            if not callable(getattr(facade, name.rsplit(".", 1)[1], None)):
                raise TypeError(f"facade must expose {name}")
        self.facade = facade
        self.actor_provider = actor_provider
        self.limits = limits or McpContractLimits(max_result_bytes=64 * 1024)
        descriptors = tuple(spec.descriptor() for spec in _TOOL_SPECS)
        # McpToolCatalog validates its digest; construct the canonical digest
        # once without keeping any caller-controlled content.
        digest_payload = {
            "protocolVersion": MCP_SERVER_PROTOCOL_VERSION,
            "serverInfo": MCP_SERVER_IMPLEMENTATION.to_wire(),
            "tools": [
                {"name": tool.name, "schemaDigest": tool.schema_digest}
                for tool in descriptors
            ],
        }
        digest = hashlib.sha256(
            json.dumps(
                digest_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        self._catalog = McpToolCatalog(
            protocol_version=MCP_SERVER_PROTOCOL_VERSION,
            server_info=MCP_SERVER_IMPLEMENTATION,
            tools=descriptors,
            digest=digest,
        )
        self._default_session: McpServerSession | None = None

    @property
    def catalog(self) -> McpToolCatalog:
        return self._catalog

    @property
    def tool_names(self) -> tuple[str, ...]:
        return MCP_SERVER_TOOL_NAMES

    def new_session(self, *, session_id: str | None = None) -> "McpServerSession":
        return McpServerSession(self, session_id=session_id)

    def handle(self, message: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Convenience handler for one fixture transport session."""

        if self._default_session is None:
            self._default_session = self.new_session()
        return self._default_session.handle(message)


class McpServerSession:
    """One isolated MCP session with no network or persistence side effects."""

    def __init__(self, server: RiftCoachMcpServer, *, session_id: str | None = None) -> None:
        self.server = server
        self.session_id = session_id or uuid.uuid4().hex
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ValueError("session_id must be a non-blank string")
        self._initialized = False
        self._client_ready = False
        self._closed = False
        self._protocol_version: str | None = None

    @property
    def initialized(self) -> bool:
        return self._initialized

    def close(self) -> None:
        self._closed = True
        self._initialized = False
        self._client_ready = False
        self._protocol_version = None

    def handle(self, message: Mapping[str, Any]) -> Mapping[str, Any] | None:
        request_id = self._request_id(message)
        if self._closed:
            return _rpc_error(request_id, -32001, "MCP session is closed.")
        if not isinstance(message, Mapping):
            return _rpc_error(None, -32600, "Invalid MCP request.")
        jsonrpc = message.get("jsonrpc")
        method = message.get("method")
        if jsonrpc != JSONRPC_VERSION or not isinstance(method, str) or not method:
            return _rpc_error(request_id, -32600, "Invalid MCP request.")
        if method == "notifications/initialized":
            if (
                "id" in message
                or set(message) != {"jsonrpc", "method"}
                or not self._initialized
            ):
                return _rpc_error(request_id, -32600, "Invalid MCP notification.")
            self._client_ready = True
            return None
        if method == "initialize":
            return self._initialize(message, request_id)
        if "id" not in message or not self._valid_request_id(message.get("id")):
            return _rpc_error(None, -32600, "Invalid MCP request.")
        if not self._initialized or not self._client_ready:
            return _rpc_error(request_id, -32001, "MCP session is not initialized.")
        if method == "tools/list":
            return self._list_tools(message, request_id)
        if method == "tools/call":
            return self._call_tool(message, request_id)
        return _rpc_error(request_id, -32601, "MCP method is not supported.")

    @staticmethod
    def _valid_request_id(value: Any) -> bool:
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, str) and bool(value.strip())
        )

    @classmethod
    def _request_id(cls, message: Any) -> str | int | None:
        if isinstance(message, Mapping) and cls._valid_request_id(message.get("id")):
            return message["id"]
        return None

    def _initialize(
        self,
        message: Mapping[str, Any],
        request_id: str | int | None,
    ) -> Mapping[str, Any]:
        if not self._valid_request_id(request_id) or set(message) != {
            "jsonrpc",
            "id",
            "method",
            "params",
        }:
            return _rpc_error(request_id, -32600, "Invalid MCP initialize request.")
        if self._initialized:
            return _rpc_error(request_id, -32600, "MCP session is already initialized.")
        params = message.get("params")
        if not isinstance(params, Mapping) or set(params) != {
            "protocolVersion",
            "capabilities",
            "clientInfo",
        }:
            return _rpc_error(request_id, -32602, "Invalid MCP initialize parameters.")
        client_info = params.get("clientInfo")
        try:
            request = McpInitializeRequest(
                request_id=request_id,
                protocol_version=params.get("protocolVersion"),
                capabilities=params.get("capabilities"),
                client_info=McpImplementation(
                    name=client_info["name"],
                    version=client_info["version"],
                )
                if isinstance(client_info, Mapping) and set(client_info) == {"name", "version"}
                else None,
            )
        except (TypeError, KeyError, ValueError):
            return _rpc_error(request_id, -32602, "Invalid MCP initialize parameters.")
        if request.protocol_version != MCP_SERVER_PROTOCOL_VERSION:
            return _rpc_error(request_id, -32602, "Unsupported MCP protocol version.")
        self._initialized = True
        self._client_ready = False
        self._protocol_version = request.protocol_version
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": {
                "protocolVersion": request.protocol_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": MCP_SERVER_IMPLEMENTATION.to_wire(),
                "instructions": "RiftCoach exposes bounded read-only owner-scoped tools.",
            },
        }

    def _list_tools(
        self,
        message: Mapping[str, Any],
        request_id: str | int,
    ) -> Mapping[str, Any]:
        if set(message) != {"jsonrpc", "id", "method", "params"}:
            return _rpc_error(request_id, -32600, "Invalid MCP tools/list request.")
        params = message.get("params", {})
        if not isinstance(params, Mapping) or set(params) - {"cursor"}:
            return _rpc_error(request_id, -32602, "Invalid MCP tools/list parameters.")
        if params.get("cursor") not in (None, ""):
            return _rpc_error(request_id, -32602, "Unsupported MCP tools/list cursor.")
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": {
                "tools": [_descriptor_wire(tool) for tool in self.server.catalog.tools],
            },
        }

    def _call_tool(
        self,
        message: Mapping[str, Any],
        request_id: str | int,
    ) -> Mapping[str, Any]:
        if set(message) != {"jsonrpc", "id", "method", "params"}:
            return _rpc_error(request_id, -32600, "Invalid MCP tools/call request.")
        params = message.get("params")
        if not isinstance(params, Mapping) or set(params) - {"name", "arguments"}:
            return _rpc_error(request_id, -32602, "Invalid MCP tools/call parameters.")
        name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            request = McpToolCallRequest.from_catalog(
                request_id=request_id,
                catalog=self.server.catalog,
                tool_name=name,
                arguments=arguments,
                allowed_tools=set(self.server.tool_names),
                limits=self.server.limits,
            )
        except McpToolCallError:
            return _rpc_error(request_id, -32602, "Invalid MCP tool arguments.")
        if request.tool_name in {
            "riftcoach.recent_summary",
            "riftcoach.single_match_review",
            "riftcoach.report_evaluation",
        }:
            try:
                normalize_run_id(request.arguments["run_id"])
            except (KeyError, TypeError, ValueError):
                return _rpc_error(request_id, -32602, "Invalid MCP tool arguments.")
        try:
            actor = self.server.actor_provider()
            if not isinstance(actor, ActorContext):
                raise McpFacadeError("service_unavailable")
            result = self._dispatch(request.tool_name, _thaw(request.arguments), actor)
            try:
                Draft202012Validator(
                    request.output_schema or {"type": "object"}
                ).validate(result)
            except Exception:
                raise McpFacadeError("integrity_failed") from None
            result_bytes = json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            if len(result_bytes) > self.server.limits.max_result_bytes:
                raise McpFacadeError("integrity_failed")
        except McpFacadeError as error:
            return _tool_error(request_id, error.code)
        except Exception:
            return _tool_error(request_id, "service_unavailable")
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": "RiftCoach structured result."}],
                "structuredContent": result,
            },
        }

    def _dispatch(
        self,
        name: str,
        arguments: Mapping[str, Any],
        actor: ActorContext,
    ) -> dict[str, Any]:
        if name == "riftcoach.recent_summary":
            run_id = normalize_run_id(arguments["run_id"])
            return _project_recent_summary(
                self.server.facade.recent_summary(actor=actor, run_id=run_id)
            )
        if name == "riftcoach.single_match_review":
            run_id = normalize_run_id(arguments["run_id"])
            return _project_single_match_review(
                self.server.facade.single_match_review(actor=actor, run_id=run_id)
            )
        if name == "riftcoach.knowledge_search":
            return _project_knowledge(
                self.server.facade.knowledge_search(
                    actor=actor,
                    query=arguments["query"],
                    top_k=arguments["top_k"],
                    filters=arguments.get("filters", {}),
                )
            )
        if name == "riftcoach.report_evaluation":
            run_id = normalize_run_id(arguments["run_id"])
            return _project_evaluation(
                self.server.facade.report_evaluation(actor=actor, run_id=run_id)
            )
        raise McpFacadeError("unsupported")


class McpServerTransport:
    """In-process transport used to prove the Server with the real MCP Client.

    It deliberately implements both request and notification delivery so the
    Client/Server fixture follows the standard initialized lifecycle.  It is
    not a claim of network deployment.
    """

    def __init__(self, session: McpServerSession) -> None:
        if not isinstance(session, McpServerSession):
            raise TypeError("session must be McpServerSession")
        self._session = session
        self._server = session.server
        self._generation = 0
        self._open = True

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def is_open(self) -> bool:
        return self._open

    @staticmethod
    def _ensure_deadline(
        deadline_monotonic: float,
        request_id: str | int | None,
    ) -> None:
        if time.monotonic() >= deadline_monotonic:
            raise McpTransportTimeout(
                McpErrorInfo(
                    code="mcp_transport_timeout",
                    retryable=True,
                    request_id=request_id,
                )
            )

    def request(
        self,
        message: Mapping[str, Any],
        *,
        deadline_monotonic: float,
    ) -> Mapping[str, Any]:
        request_id = message.get("id") if isinstance(message, Mapping) else None
        if not self._open:
            raise McpTransportError(
                McpErrorInfo(
                    code="mcp_transport_disconnected",
                    retryable=True,
                    request_id=request_id,
                )
            )
        self._ensure_deadline(deadline_monotonic, request_id)
        response = self._session.handle(message)
        self._ensure_deadline(deadline_monotonic, request_id)
        if not isinstance(response, Mapping):
            raise McpTransportError(
                McpErrorInfo(
                    code="mcp_transport_frame_invalid",
                    retryable=False,
                    request_id=request_id,
                )
            )
        return response

    send = request

    def notify(
        self,
        message: Mapping[str, Any],
        *,
        deadline_monotonic: float,
    ) -> None:
        if not self._open:
            raise McpTransportError(
                McpErrorInfo(
                    code="mcp_transport_disconnected",
                    retryable=True,
                )
            )
        self._ensure_deadline(deadline_monotonic, None)
        response = self._session.handle(message)
        if response is not None:
            raise McpTransportError(
                McpErrorInfo(
                    code="mcp_transport_notification_failed",
                    retryable=False,
                )
            )

    def restart(self) -> None:
        self._session.close()
        self._session = self._server.new_session()
        self._generation += 1
        self._open = True

    def close(self) -> None:
        if not self._open:
            return
        self._session.close()
        self._open = False


def build_riftcoach_mcp_server(
    *,
    task_service: Any,
    run_query: Any,
    knowledge_provider: Any,
    actor_provider: ActorContextProvider,
    limits: McpContractLimits | None = None,
) -> RiftCoachMcpServer:
    """Compose the Server from service/query ports without persistence access."""

    return RiftCoachMcpServer(
        facade=QueryMcpApplicationFacade(
            task_service=task_service,
            run_query=run_query,
            knowledge_provider=knowledge_provider,
        ),
        actor_provider=actor_provider,
        limits=limits,
    )


__all__ = [
    "MCP_SERVER_IMPLEMENTATION",
    "MCP_SERVER_PROTOCOL_VERSION",
    "MCP_SERVER_TOOL_NAMES",
    "McpApplicationFacade",
    "McpFacadeError",
    "McpServerSession",
    "McpServerTransport",
    "QueryMcpApplicationFacade",
    "RiftCoachMcpServer",
    "build_riftcoach_mcp_server",
]

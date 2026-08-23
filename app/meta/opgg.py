"""Strict anti-corruption adapter for one OP.GG lane-Meta MCP tool."""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.mcp.client import McpClientSession
from app.tools.runtime import ToolRuntime

from .models import (
    LaneMetaChampionFact,
    MetaEvidence,
    MetaProvenance,
    MetaUseCase,
)


OPGG_LANE_META_REMOTE_TOOL = "lol_list_lane_meta_champions"
OPGG_LANE_META_LOCAL_TOOL = "opgg.lane_meta_champions"
_POSITIONS = frozenset({"top", "mid", "jungle", "adc", "support"})
_ROW_NAMES = {
    "top": "Top",
    "mid": "Mid",
    "jungle": "Jungle",
    "adc": "Adc",
    "support": "Support",
}
_ROW_FIELDS = (
    "champion",
    "win_rate",
    "pick_rate",
    "ban_rate",
    "tier",
    "rank",
    "rank_prev",
    "rank_prev_patch",
)


@dataclass(frozen=True)
class OPGGMetaSchemaDiagnostic:
    """Body-free structural summary of one rejected OP.GG result.

    The diagnostic intentionally contains no source text or parsed values.  It
    is safe to persist alongside an external validation result and is useful
    for deciding whether an upstream schema change is understood well enough
    to admit.
    """

    stage: str
    position: str
    row_name: str | None
    field_name: str | None
    field_index: int | None
    observed_node_type: str | None
    text_length: int
    text_digest: str

    def __post_init__(self) -> None:
        if self.stage not in {"header", "expression", "rows", "row", "row_field", "row_value"}:
            raise ValueError("diagnostic stage is invalid")
        if self.position not in _POSITIONS:
            raise ValueError("diagnostic position is invalid")
        if self.row_name is not None and self.row_name != _ROW_NAMES[self.position]:
            raise ValueError("diagnostic row name is invalid")
        if self.field_name is not None and self.field_name not in _ROW_FIELDS:
            raise ValueError("diagnostic field name is invalid")
        if self.field_index is not None and not 0 <= self.field_index < len(_ROW_FIELDS):
            raise ValueError("diagnostic field index is invalid")
        if isinstance(self.text_length, bool) or not isinstance(self.text_length, int) or self.text_length < 0:
            raise ValueError("diagnostic text length is invalid")
        if len(self.text_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.text_digest
        ):
            raise ValueError("diagnostic text digest is invalid")

    def to_public_projection(self) -> dict[str, Any]:
        """Return an allowlisted, body-free JSON-compatible projection."""

        return {
            "stage": self.stage,
            "position": self.position,
            "row_name": self.row_name,
            "field_name": self.field_name,
            "field_index": self.field_index,
            "observed_node_type": self.observed_node_type,
            "text_length": self.text_length,
            "text_digest": self.text_digest,
        }
_SAFE_MESSAGES = {
    "opgg_meta_catalog_incompatible": "OP.GG Meta tool contract is incompatible.",
    "opgg_meta_call_failed": "OP.GG Meta tool call failed.",
    "opgg_meta_result_invalid": "OP.GG Meta result is invalid.",
    "opgg_meta_result_too_large": "OP.GG Meta result exceeds configured limits.",
}


class OPGGMetaError(RuntimeError):
    """Body-free OP.GG adapter failure."""

    def __init__(
        self,
        code: str,
        *,
        diagnostic: OPGGMetaSchemaDiagnostic | None = None,
    ) -> None:
        if code not in _SAFE_MESSAGES:
            raise ValueError("unknown OP.GG Meta error code")
        if diagnostic is not None and not isinstance(diagnostic, OPGGMetaSchemaDiagnostic):
            raise TypeError("diagnostic must be OPGGMetaSchemaDiagnostic")
        self.code = code
        self.diagnostic = diagnostic
        super().__init__(_SAFE_MESSAGES[code])

    def __repr__(self) -> str:
        return f"OPGGMetaError(code={self.code!r})"


def _diagnostic(
    text: str,
    *,
    position: str,
    stage: str,
    row_name: str | None = None,
    field_index: int | None = None,
    observed_node_type: str | None = None,
) -> OPGGMetaSchemaDiagnostic:
    return OPGGMetaSchemaDiagnostic(
        stage=stage,
        position=position,
        row_name=row_name,
        field_name=(
            _ROW_FIELDS[field_index]
            if field_index is not None and 0 <= field_index < len(_ROW_FIELDS)
            else None
        ),
        field_index=field_index,
        observed_node_type=observed_node_type,
        text_length=len(text),
        text_digest=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _call(node: ast.AST, name: str, argument_count: int) -> ast.Call:
    if (
        not isinstance(node, ast.Call)
        or not isinstance(node.func, ast.Name)
        or node.func.id != name
        or node.keywords
        or len(node.args) != argument_count
    ):
        raise OPGGMetaError("opgg_meta_result_invalid")
    return node


def _constant(node: ast.AST) -> object:
    if not isinstance(node, ast.Constant):
        raise OPGGMetaError("opgg_meta_result_invalid")
    value = node.value
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OPGGMetaError("opgg_meta_result_invalid")
    return value


def _integer(value: object, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise OPGGMetaError("opgg_meta_result_invalid")
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OPGGMetaError("opgg_meta_result_invalid")
    return float(value)


def _parse_lane_meta_text(
    text: str,
    *,
    position: str,
    top_n: int,
) -> tuple[LaneMetaChampionFact, ...]:
    row_name = _ROW_NAMES[position]
    expected_header = (
        "class LolListLaneMetaChampions: lang,position_filter,data\n"
        "class Data: positions\n"
        f"class Positions: {position}\n"
        f"class {row_name}: {','.join(_ROW_FIELDS)}"
    )
    normalized = text.replace("\r\n", "\n")
    try:
        header, expression = normalized.split("\n\n", 1)
    except ValueError:
        raise OPGGMetaError(
            "opgg_meta_result_invalid",
            diagnostic=_diagnostic(
                text,
                position=position,
                stage="header",
            ),
        ) from None
    if header != expected_header or not expression.strip():
        raise OPGGMetaError(
            "opgg_meta_result_invalid",
            diagnostic=_diagnostic(
                text,
                position=position,
                stage="header",
            ),
        )
    try:
        root = ast.parse(expression.strip(), mode="eval")
    except (MemoryError, RecursionError, SyntaxError, ValueError):
        raise OPGGMetaError(
            "opgg_meta_result_invalid",
            diagnostic=_diagnostic(
                text,
                position=position,
                stage="expression",
                observed_node_type="parse_error",
            ),
        ) from None

    try:
        outer = _call(root.body, "LolListLaneMetaChampions", 3)
    except OPGGMetaError:
        raise OPGGMetaError(
            "opgg_meta_result_invalid",
            diagnostic=_diagnostic(
                text,
                position=position,
                stage="expression",
                observed_node_type=type(root.body).__name__,
            ),
        ) from None
    lang = _constant(outer.args[0])
    position_filter = _constant(outer.args[1])
    if lang != "en_US" or position_filter != position:
        raise OPGGMetaError("opgg_meta_result_invalid")
    data = _call(outer.args[2], "Data", 1)
    positions = _call(data.args[0], "Positions", 1)
    rows_node = positions.args[0]
    if not isinstance(rows_node, ast.List) or not 1 <= len(rows_node.elts) <= 200:
        raise OPGGMetaError(
            "opgg_meta_result_invalid",
            diagnostic=_diagnostic(
                text,
                position=position,
                stage="rows",
                row_name=row_name,
                observed_node_type=type(rows_node).__name__,
            ),
        )

    facts: list[LaneMetaChampionFact] = []
    for node in rows_node.elts:
        row = _call(node, row_name, len(_ROW_FIELDS))
        values: list[object] = []
        for field_index, argument in enumerate(row.args):
            try:
                values.append(_constant(argument))
            except OPGGMetaError:
                raise OPGGMetaError(
                    "opgg_meta_result_invalid",
                    diagnostic=_diagnostic(
                        text,
                        position=position,
                        stage="row_field",
                        row_name=row_name,
                        field_index=field_index,
                        observed_node_type=type(argument).__name__,
                    ),
                ) from None
        values_tuple = tuple(values)
        try:
            champion = values_tuple[0]
            if not isinstance(champion, str):
                raise ValueError("champion")
            facts.append(
                LaneMetaChampionFact(
                    champion=champion,
                    win_rate=_number(values_tuple[1]),
                    pick_rate=_number(values_tuple[2]),
                    ban_rate=_number(values_tuple[3]),
                    tier=_integer(values_tuple[4]),
                    rank=_integer(values_tuple[5]),
                    rank_previous=_integer(values_tuple[6], nullable=True),
                    rank_previous_patch=_integer(values_tuple[7], nullable=True),
                )
            )
        except (TypeError, ValueError):
            raise OPGGMetaError(
                "opgg_meta_result_invalid",
                diagnostic=_diagnostic(
                    text,
                    position=position,
                    stage="row_value",
                    row_name=row_name,
                    observed_node_type=type(values_tuple[0]).__name__,
                ),
            ) from None
    if len({fact.champion.casefold() for fact in facts}) != len(facts):
        raise OPGGMetaError(
            "opgg_meta_result_invalid",
            diagnostic=_diagnostic(
                text,
                position=position,
                stage="rows",
                row_name=row_name,
                observed_node_type="duplicate_champion",
            ),
        )
    if len({fact.rank for fact in facts}) != len(facts):
        raise OPGGMetaError(
            "opgg_meta_result_invalid",
            diagnostic=_diagnostic(
                text,
                position=position,
                stage="rows",
                row_name=row_name,
                observed_node_type="duplicate_rank",
            ),
        )
    return tuple(facts[:top_n])


class OPGGLaneMetaAdapter:
    """Turn an unstructured OP.GG MCP response into partial Meta evidence."""

    def __init__(
        self,
        *,
        session: McpClientSession,
        runtime: ToolRuntime,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        ttl: timedelta = timedelta(minutes=15),
        max_content_chars: int = 128 * 1024,
    ) -> None:
        if not isinstance(session, McpClientSession):
            raise TypeError("session must be McpClientSession")
        if not isinstance(runtime, ToolRuntime):
            raise TypeError("runtime must be ToolRuntime")
        if not callable(clock):
            raise TypeError("clock must be callable")
        if not isinstance(ttl, timedelta) or ttl <= timedelta(0):
            raise ValueError("ttl must be positive")
        if (
            isinstance(max_content_chars, bool)
            or not isinstance(max_content_chars, int)
            or max_content_chars <= 0
        ):
            raise ValueError("max_content_chars must be a positive integer")
        self._session = session
        self._runtime = runtime
        self._clock = clock
        self._ttl = ttl
        self._max_content_chars = max_content_chars

    def _descriptor(self):
        catalog = self._session.catalog
        descriptor = (
            catalog.get(OPGG_LANE_META_REMOTE_TOOL)
            if catalog is not None
            else None
        )
        if catalog is None or descriptor is None or descriptor.output_schema is not None:
            raise OPGGMetaError("opgg_meta_catalog_incompatible")
        schema = descriptor.input_schema
        properties = schema.get("properties")
        required = schema.get("required")
        if (
            schema.get("type") != "object"
            or not isinstance(properties, Mapping)
            or frozenset(properties)
            != frozenset({"lang", "position", "desired_output_fields"})
            or tuple(required or ()) != ("desired_output_fields",)
        ):
            raise OPGGMetaError("opgg_meta_catalog_incompatible")
        desired = properties.get("desired_output_fields")
        position = properties.get("position")
        position_enum = position.get("enum") if isinstance(position, Mapping) else None
        if (
            not isinstance(desired, Mapping)
            or desired.get("type") != "array"
            or not isinstance(desired.get("items"), Mapping)
            or desired["items"].get("type") != "string"
            or not isinstance(position, Mapping)
            or position.get("type") != "string"
            or not isinstance(position_enum, tuple)
            or not all(isinstance(item, str) for item in position_enum)
            or not _POSITIONS.issubset(frozenset(position_enum))
        ):
            raise OPGGMetaError("opgg_meta_catalog_incompatible")
        annotations = descriptor.annotations
        if not isinstance(annotations, Mapping) or any(
            annotations.get(name) is not value
            for name, value in (
                ("readOnlyHint", True),
                ("destructiveHint", False),
                ("idempotentHint", True),
                ("openWorldHint", False),
            )
        ):
            raise OPGGMetaError("opgg_meta_catalog_incompatible")
        return catalog, descriptor

    def fetch(
        self,
        *,
        position: str,
        top_n: int = 10,
        timeout_s: float = 15.0,
    ) -> MetaEvidence:
        if position not in _POSITIONS:
            raise ValueError("position is invalid")
        if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 10:
            raise ValueError("top_n must be between one and ten")
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or timeout_s <= 0
        ):
            raise ValueError("timeout_s must be positive")
        catalog, descriptor = self._descriptor()
        fields = ",".join(_ROW_FIELDS)
        result = self._runtime.execute(
            OPGG_LANE_META_LOCAL_TOOL,
            {
                "lang": "en_US",
                "position": position,
                "desired_output_fields": [
                    f"data.positions.{position}[].{{{fields}}}",
                    "lang",
                    "position_filter",
                ],
            },
            timeout_cap_s=float(timeout_s),
            metadata={"source": "opgg", "data_class": "dynamic_meta"},
        )
        if not result.success or not isinstance(result.data, Mapping):
            raise OPGGMetaError("opgg_meta_call_failed")
        content = result.data.get("content")
        if not isinstance(content, (list, tuple)) or len(content) != 1:
            raise OPGGMetaError("opgg_meta_result_invalid")
        item = content[0]
        if (
            not isinstance(item, Mapping)
            or frozenset(item) != frozenset({"type", "text"})
            or item.get("type") != "text"
            or not isinstance(item.get("text"), str)
        ):
            raise OPGGMetaError("opgg_meta_result_invalid")
        text = item["text"]
        if len(text) > self._max_content_chars:
            raise OPGGMetaError("opgg_meta_result_too_large")
        facts = _parse_lane_meta_text(text, position=position, top_n=top_n)
        retrieved_at = self._clock()
        if not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        retrieved_at = retrieved_at.astimezone(timezone.utc)
        return MetaEvidence(
            source="opgg",
            remote_tool=OPGG_LANE_META_REMOTE_TOOL,
            position=position,
            facts=facts,
            provenance=MetaProvenance.PARTIAL,
            upstream_patch=None,
            source_generated_at=None,
            retrieved_at=retrieved_at,
            expires_at=retrieved_at + self._ttl,
            allowed_uses=frozenset(
                {MetaUseCase.CURRENT_SNAPSHOT_RECOMMENDATION}
            ),
            catalog_digest=catalog.digest,
            tool_schema_digest=descriptor.schema_digest,
        )

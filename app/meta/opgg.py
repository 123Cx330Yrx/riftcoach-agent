"""Strict anti-corruption adapter for one OP.GG lane-Meta MCP tool."""

from __future__ import annotations

import ast
from collections.abc import Mapping
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
_SAFE_MESSAGES = {
    "opgg_meta_catalog_incompatible": "OP.GG Meta tool contract is incompatible.",
    "opgg_meta_call_failed": "OP.GG Meta tool call failed.",
    "opgg_meta_result_invalid": "OP.GG Meta result is invalid.",
    "opgg_meta_result_too_large": "OP.GG Meta result exceeds configured limits.",
}


class OPGGMetaError(RuntimeError):
    """Body-free OP.GG adapter failure."""

    def __init__(self, code: str) -> None:
        if code not in _SAFE_MESSAGES:
            raise ValueError("unknown OP.GG Meta error code")
        self.code = code
        super().__init__(_SAFE_MESSAGES[code])

    def __repr__(self) -> str:
        return f"OPGGMetaError(code={self.code!r})"


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
        raise OPGGMetaError("opgg_meta_result_invalid") from None
    if header != expected_header or not expression.strip():
        raise OPGGMetaError("opgg_meta_result_invalid")
    try:
        root = ast.parse(expression.strip(), mode="eval")
    except (MemoryError, RecursionError, SyntaxError, ValueError):
        raise OPGGMetaError("opgg_meta_result_invalid") from None

    outer = _call(root.body, "LolListLaneMetaChampions", 3)
    lang = _constant(outer.args[0])
    position_filter = _constant(outer.args[1])
    if lang != "en_US" or position_filter != position:
        raise OPGGMetaError("opgg_meta_result_invalid")
    data = _call(outer.args[2], "Data", 1)
    positions = _call(data.args[0], "Positions", 1)
    rows_node = positions.args[0]
    if not isinstance(rows_node, ast.List) or not 1 <= len(rows_node.elts) <= 200:
        raise OPGGMetaError("opgg_meta_result_invalid")

    facts: list[LaneMetaChampionFact] = []
    for node in rows_node.elts:
        row = _call(node, row_name, len(_ROW_FIELDS))
        values = tuple(_constant(argument) for argument in row.args)
        try:
            champion = values[0]
            if not isinstance(champion, str):
                raise ValueError("champion")
            facts.append(
                LaneMetaChampionFact(
                    champion=champion,
                    win_rate=_number(values[1]),
                    pick_rate=_number(values[2]),
                    ban_rate=_number(values[3]),
                    tier=_integer(values[4]),
                    rank=_integer(values[5]),
                    rank_previous=_integer(values[6], nullable=True),
                    rank_previous_patch=_integer(values[7], nullable=True),
                )
            )
        except (TypeError, ValueError):
            raise OPGGMetaError("opgg_meta_result_invalid") from None
    if len({fact.champion.casefold() for fact in facts}) != len(facts):
        raise OPGGMetaError("opgg_meta_result_invalid")
    if len({fact.rank for fact in facts}) != len(facts):
        raise OPGGMetaError("opgg_meta_result_invalid")
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

"""Strict, provider-neutral validation for machine-consumed responses."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from .errors import ProviderResponseError
from .models import ChatResponse, StructuredResponseContract


OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredRepairRequest:
    """One invalid response made available to a bounded repair caller."""

    contract: StructuredResponseContract
    invalid_content: str
    failure_code: str


StructuredRepair = Callable[[StructuredRepairRequest], ChatResponse]


@dataclass(frozen=True)
class StructuredDecodeResult(Generic[OutputModelT]):
    value: OutputModelT
    response: ChatResponse
    repair_attempted: bool = False


class _InvalidStructuredOutput(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def contract_for_model(
    *,
    name: str,
    version: str,
    output_model: type[OutputModelT],
) -> StructuredResponseContract:
    """Build the transport contract from the exact local validation model."""

    _require_pydantic_model(output_model)
    return StructuredResponseContract(
        name=name,
        version=version,
        json_schema=output_model.model_json_schema(),
    )


def decode_structured_response(
    *,
    response: ChatResponse,
    contract: StructuredResponseContract,
    output_model: type[OutputModelT],
    repair: StructuredRepair | None = None,
) -> StructuredDecodeResult[OutputModelT]:
    """Validate once, optionally repair once, then fail closed."""

    _validate_configuration(contract=contract, output_model=output_model)
    try:
        value = _decode_once(response=response, output_model=output_model)
    except _InvalidStructuredOutput as first_error:
        if repair is None:
            raise _safe_error(response.provider) from None
        repaired_response = repair(
            StructuredRepairRequest(
                contract=contract,
                invalid_content=response.content or "",
                failure_code=first_error.code,
            )
        )
        if not isinstance(repaired_response, ChatResponse):
            raise TypeError("structured repair must return ChatResponse.")
        try:
            repaired_value = _decode_once(
                response=repaired_response,
                output_model=output_model,
            )
        except _InvalidStructuredOutput:
            raise _safe_error(response.provider) from None
        return StructuredDecodeResult(
            value=repaired_value,
            response=repaired_response,
            repair_attempted=True,
        )

    return StructuredDecodeResult(
        value=value,
        response=response,
        repair_attempted=False,
    )


def _validate_configuration(
    *,
    contract: StructuredResponseContract,
    output_model: type[OutputModelT],
) -> None:
    if not isinstance(contract, StructuredResponseContract):
        raise ValueError("contract must be StructuredResponseContract.")
    _require_pydantic_model(output_model)
    if output_model.model_config.get("extra") != "forbid":
        raise ValueError("structured output models must forbid extra fields.")
    expected_schema = output_model.model_json_schema()
    if _canonical_json(contract.schema_dict()) != _canonical_json(expected_schema):
        raise ValueError("response contract does not match output model schema.")


def _require_pydantic_model(output_model: type[BaseModel]) -> None:
    if not isinstance(output_model, type) or not issubclass(output_model, BaseModel):
        raise ValueError("output_model must be a Pydantic BaseModel type.")


def _decode_once(
    *,
    response: ChatResponse,
    output_model: type[OutputModelT],
) -> OutputModelT:
    finish_reason = (response.finish_reason or "").strip().lower()
    if finish_reason in {"length", "max_tokens", "content_filter"}:
        raise _InvalidStructuredOutput("incomplete_response")
    if response.content is None:
        raise _InvalidStructuredOutput("missing_content")
    try:
        return output_model.model_validate_json(response.content, strict=True)
    except (ValidationError, ValueError, TypeError):
        raise _InvalidStructuredOutput("schema_validation_failed") from None


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _safe_error(provider: str) -> ProviderResponseError:
    return ProviderResponseError(
        provider=provider,
        code="invalid_structured_output",
    )

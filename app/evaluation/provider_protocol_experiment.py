"""Compose a bounded real Provider protocol gate into public-safe evidence."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.providers.protocol import LLMProvider

from .provider_adapter_protocol import (
    AdapterProtocolSliceReport,
    AdapterProtocolSliceRunner,
)
from .provider_adoption import (
    ExperimentBudgetedProvider,
    ExperimentControlSnapshot,
    ExperimentPreparationReport,
    ExperimentStopController,
    ProviderResourceLedger,
    ResourceLedgerSnapshot,
    deepseek_experiment_policy,
)


class ProviderAdapterProtocolExperimentRecord(BaseModel):
    """Immutable, sanitized evidence for one real adapter protocol gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    preparation: ExperimentPreparationReport
    protocol: AdapterProtocolSliceReport
    resources: ResourceLedgerSnapshot
    control: ExperimentControlSnapshot
    held_out_executed: Literal[False] = False

    @model_validator(mode="after")
    def validate_cross_layer_identity(
        self,
    ) -> "ProviderAdapterProtocolExperimentRecord":
        identity = (
            self.preparation.provider_id,
            self.preparation.requested_model,
            self.preparation.code_sha,
        )
        if identity != (
            self.protocol.provider_id,
            self.protocol.requested_model,
            self.protocol.code_sha,
        ):
            raise ValueError("preparation and protocol identity must match")
        if identity[:2] != (
            self.resources.provider_id,
            self.resources.model,
        ):
            raise ValueError("preparation and resource identity must match")
        if self.protocol.calls_used != self.resources.calls_used:
            raise ValueError("protocol and resource call counts must match")
        if self.protocol.calls_used != sum(
            case.external_calls for case in self.protocol.cases
        ):
            raise ValueError("protocol case call counts must match the total")
        if self.resources.input_tokens != sum(
            case.input_tokens for case in self.protocol.cases
        ):
            raise ValueError("protocol and resource input tokens must match")
        if self.resources.output_tokens != sum(
            case.output_tokens for case in self.protocol.cases
        ):
            raise ValueError("protocol and resource output tokens must match")
        scope_calls = {
            scope.scope: scope.calls_used for scope in self.resources.scope_calls
        }
        if scope_calls.get("adapter_protocol") != self.protocol.calls_used:
            raise ValueError("all real calls must belong to adapter_protocol scope")
        if scope_calls.get("domain") != 0:
            raise ValueError("protocol evidence cannot claim domain execution")
        return self


def run_deepseek_adapter_protocol_experiment(
    *,
    preparation: ExperimentPreparationReport,
    provider: LLMProvider,
    clock: Callable[[], float] = time.monotonic,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ProviderAdapterProtocolExperimentRecord:
    """Run only the frozen three-call DeepSeek protocol gate."""

    policy = deepseek_experiment_policy()
    _require_frozen_preparation(preparation, provider, policy)

    ledger = ProviderResourceLedger(policy)
    controller = ExperimentStopController(
        allowed_provider_ids=(policy.provider_id,)
    )
    controlled_provider = ExperimentBudgetedProvider(
        provider=provider,
        ledger=ledger,
        controller=controller,
        scope="adapter_protocol",
        clock=clock,
    )
    protocol = AdapterProtocolSliceRunner(
        provider=controlled_provider,
        code_sha=preparation.code_sha,
        max_calls=preparation.protocol_max_calls,
        clock=clock,
        now=now,
    ).run()
    return ProviderAdapterProtocolExperimentRecord(
        preparation=preparation,
        protocol=protocol,
        resources=ledger.snapshot(),
        control=controller.snapshot(),
    )


def _require_frozen_preparation(preparation, provider, policy) -> None:
    if not isinstance(preparation, ExperimentPreparationReport):
        raise TypeError("preparation must be an ExperimentPreparationReport")
    if preparation.code_sha != preparation.public_ci_sha:
        raise ValueError("local code SHA must match the successful public CI SHA")
    if not preparation.public_ci_success_confirmed:
        raise ValueError("successful public CI must be explicitly confirmed")
    if not preparation.local_preflight_passed:
        raise ValueError("local no-I/O preflight must pass")
    if preparation.external_provider_calls != 0 or preparation.held_out_executed:
        raise ValueError("preparation must not claim external or held-out execution")
    if (
        preparation.provider_id != policy.provider_id
        or preparation.requested_model != policy.model
        or provider.provider_name != policy.provider_id
        or provider.model_name != policy.model
    ):
        raise ValueError("Provider identity does not match the frozen experiment")
    if (
        preparation.protocol_max_calls
        != policy.scope_call_limits["adapter_protocol"]
        or preparation.domain_max_calls != policy.scope_call_limits["domain"]
        or preparation.cumulative_max_calls != policy.max_calls
        or preparation.maximum_total_tokens != policy.max_observed_tokens
        or preparation.maximum_output_tokens_per_request
        != policy.max_output_tokens_per_request
        or preparation.maximum_estimated_cost != policy.max_estimated_cost
        or preparation.currency != policy.currency
    ):
        raise ValueError("preparation resource policy does not match frozen limits")

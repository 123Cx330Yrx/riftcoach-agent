"""Body-free contract for an explicitly selected, unpublished Worker candidate.

Session checkpoints are separate from lease checkpoints: execution_started is
never reclassified as safe_to_replay. No credential or model body enters SQL.
"""
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


WORKER_SOL_PROFILE = "sol-dual-development-v1"


class ContinuationError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ResumeContinuation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manual_retry: bool = False


class SessionAccounting(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    scope: Literal["cumulative_session"] = "cumulative_session"
    requests_reserved: int = Field(ge=0)
    requests_observed: int = Field(ge=0)
    known_tokens: int = Field(ge=0)
    unknown_token_reservation: int = Field(ge=0)
    retries: int = Field(ge=0)
    unresolved_intents: int = Field(ge=0)


@dataclass(frozen=True)
class TaskExecutionPause:
    run_id: str
    reason: str

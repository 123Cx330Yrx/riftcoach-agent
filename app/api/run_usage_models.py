"""Owner-scoped usage projection, independent of report publication."""
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.runtime.models import RuntimeUsage
from app.tasks.models import TaskStatus


class RunUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    task_status: Literal[TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    # Missing trusted observations are not a zero-cost result.
    usage: RuntimeUsage | None = None

"""HTTP adapters and deployment composition for the RiftCoach boundary."""

from __future__ import annotations

from typing import Any

__all__ = ["create_app", "create_composed_app"]


def __getattr__(name: str) -> Any:
    """Preserve the package convenience API without eager dependency cycles."""

    if name == "create_app":
        from .main import create_app

        return create_app
    if name == "create_composed_app":
        from .composition import create_composed_app

        return create_composed_app
    raise AttributeError(name)

"""HTTP adapters and deployment composition for the RiftCoach boundary."""

from .composition import create_composed_app
from .main import create_app

__all__ = ["create_app", "create_composed_app"]

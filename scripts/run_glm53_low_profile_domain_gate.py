"""CLI entry point for the candidate-only low-profile domain gate."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.glm53_low_profile_domain_gate import main


if __name__ == "__main__":
    raise SystemExit(main())

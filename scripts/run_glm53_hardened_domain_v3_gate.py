"""CLI entry point for the candidate-only hardened V3 domain gate."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.glm53_hardened_domain_v3_gate import main


if __name__ == "__main__":
    raise SystemExit(main())

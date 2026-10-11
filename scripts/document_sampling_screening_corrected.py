"""Corrected-control wrapper for the isolated temperature screening diagnostic."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "scripts" / "document_sampling_screening.py"
spec = importlib.util.spec_from_file_location("scripts._document_sampling_screening_base", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("sampling_base_import")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

base.VERSION = "document-sampling-screening-corrected-v1"
base.AUTH_VERSION = "document-sampling-screening-corrected-authorization-v1"
base.RUN_ID = "document-sampling-screening-20261012-corrected-v2"
base.OPERATOR_ROOT = Path(
    r"C:/Users/33502/Documents/Agent/outputs/riftcoach-corrected-temperature-screening-20261012-v2"
)
base.ADAPTER_SOURCE = "scripts/document_sampling_screening_corrected.py"
# The base module loads the generic runner before this adapter overrides the
# diagnostic identity.  Keep the runner's result and authorization gates on
# the corrected identity as well; otherwise every valid corrected authorization
# is rejected against the historical generic version.
base.runner.VERSION = base.VERSION
base.runner.AUTH_VERSION = base.AUTH_VERSION
base.SAMPLES = (
    (
        "claim-scope:1",
        "initial",
        "data/evaluation/results/golden_document_full15_time600_result_20261010.json",
        "30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576",
        "accept",
    ),
    (
        "observed:3",
        "final",
        "data/evaluation/results/golden_document_remaining4_time600_result_20261011.json",
        "a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec",
        "accept",
    ),
    (
        "observed:4",
        "final",
        "data/evaluation/results/golden_document_remaining4_time600_result_20261011.json",
        "a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec",
        "accept",
    ),
    (
        "claim-scope:4",
        "initial",
        "data/evaluation/results/golden_document_full15_time600_result_20261010.json",
        "30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576",
        "reject",
    ),
    (
        "scope:4",
        "initial",
        "data/evaluation/results/golden_document_full15_time600_result_20261010.json",
        "30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576",
        "reject",
    ),
)

if __name__ == "__main__":
    base.main()

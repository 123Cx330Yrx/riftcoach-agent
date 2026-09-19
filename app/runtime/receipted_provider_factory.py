"""One stream counter, failure flag and receipt directory per trusted run."""
from pathlib import Path

from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, RESPONSE, validate_request
from app.harness.run_ids import normalize_run_id


class JournaledReceiptedProvider(ReceiptedStreamProvider):
    def chat(self, request):
        self.last_exchange = None
        raw = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        ordinal = self._calls + 1
        self._directory.mkdir(parents=True, exist_ok=True)
        with (self._directory / f'request-{ordinal:03d}.json').open('xb') as stream:
            stream.write(raw)
        response = super().chat(request)
        with (self._directory / f'response-{ordinal:03d}.json').open('xb') as stream:
            stream.write(RESPONSE.dump_json(response))
        return response


class RunScopedReceiptedProviderFactory:
    def __init__(self, *, settings, transport_root):
        self._settings = settings
        self._root = Path(transport_root).resolve()
        # Identity/capability validation only: no directory or request is made.
        self.descriptor = JournaledReceiptedProvider(settings=settings,
            directory=self._root / '_identity_only', transport_id=CAPACITY_TRANSPORT_ID)

    def __call__(self, run_id):
        run_id = normalize_run_id(run_id)
        return JournaledReceiptedProvider(settings=self._settings,
            directory=self._root / run_id, transport_id=CAPACITY_TRANSPORT_ID)

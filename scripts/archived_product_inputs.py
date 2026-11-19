"""Explicit read-only archived inputs for an operator-approved product task.

This adapter is never selected by a default Worker. It reuses existing summary,
Evidence and composition ports without constructing a Riot client or changing
the age, identity or contents of the original observations.
"""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path

from app.evidence.fusion import EvidenceBundle
from app.evidence.publication import EvidencePublicationSources
from app.providers.secrets import SecretConfigurationError, SecretMaterial


def pinned_json(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('archived_input_pin_mismatch')
    return json.loads(raw)


class ArchivedProductInputs:
    def __init__(self, root, *, summary_sha256, bundle_sha256,
                 manifest_sha256, source_intent_sha256):
        root = Path(root).resolve()
        self._summary = pinned_json(root/'inputs/player_summary.json', summary_sha256)
        bundle = EvidenceBundle.model_validate_json(json.dumps(
            pinned_json(root/'evidence_bundle.json', bundle_sha256)))
        manifest = pinned_json(root/'evidence_publication_manifest.json', manifest_sha256)
        intent = pinned_json(root/'.continuation/session/operations/0001-intent.json', source_intent_sha256)
        if (intent.get('kind') != 'source' or intent['request']['method'] != 'build_by_puuid'
                or manifest['summary']['sha256'] != summary_sha256
                or manifest['bundle']['sha256'] != bundle_sha256):
            raise ValueError('archived_source_binding')
        self._arguments = deepcopy(intent['request']['arguments'])
        self.sources = EvidencePublicationSources(now=bundle.created_at)
        projected = self.sources.project(self._summary, routing_region=self._arguments['routing_region'])
        request, player = self._summary['request'], self._summary['player']
        if (projected.bundle != bundle or projected.summary_digest != manifest['summary_digest']
                or bundle.digest != manifest['bundle']['bundle_digest']
                or any(self._arguments[k] != v for k, v in {
                    'game_name': player['game_name'], 'tag_line': player['tag_line'],
                    'count': request['count'], 'queue': request['requested_queue']}.items())
                or player['puuid_prefix'] != self._arguments['puuid'][:16] + '...'):
            raise ValueError('archived_source_binding')
        self.reads = 0

    @property
    def arguments(self):
        return deepcopy(self._arguments)

    def build(self, **kwargs):
        raise ValueError('archived_conversation_identity_required')

    def build_by_puuid(self, **kwargs):
        if kwargs != self._arguments:
            raise ValueError('archived_request_scope_mismatch')
        self.reads += 1
        return deepcopy(self._summary)


class ExistingProductSecrets:
    """Lazy two-name allowlist; unknown names cannot read any credential."""
    def __init__(self, *, flash_reader, reviewer_reader):
        self._readers = {'llm-api': flash_reader, 'sol-review-api': reviewer_reader}
        self.read_names = []

    def read(self, *, name, now, version=None):
        if name not in self._readers or version not in (None, 'existing-local'):
            raise SecretConfigurationError('product_secret_scope')
        value = self._readers[name]()
        self.read_names.append(name)
        return SecretMaterial(name=name, version='existing-local', value=value)


def read_existing_flash_key(path):
    # Parse only selected model-key lines. Do not materialize Riot settings or
    # merge the file into process environment (which is inherited by children).
    from dotenv import dotenv_values
    selected = []
    with Path(path).open(encoding='utf-8-sig') as stream:
        for line in stream:
            name = line.strip().removeprefix('export ').partition('=')[0].strip()
            if name in ('LLM_API_KEY', 'ZHIPU_API_KEY'):
                selected.append(line)
    values = dotenv_values(stream=io.StringIO(''.join(selected)), interpolate=False)
    value = values.get('LLM_API_KEY') or values.get('ZHIPU_API_KEY')
    if not value:
        raise SecretConfigurationError('existing_flash_key_missing')
    return value


def compose_archived_executor(settings, *, repository, inputs, knowledge,
                              memory_repository=None):
    from app.product import sol_chat_contract
    from app.workers.composition import compose_continuation_executor
    if settings.execution_profile != sol_chat_contract.WORKER_PROFILE:
        raise ValueError('archived_product_chat_profile_required')

    class NoLegacy:
        def execute(self, task):
            raise ValueError('archived_legacy_execution_forbidden')

    route = compose_continuation_executor(settings, repository=repository, legacy=NoLegacy(),
        summary_builder=inputs, knowledge=knowledge, memory_repository=memory_repository)
    route.candidate.publication_sources = inputs.sources
    return route

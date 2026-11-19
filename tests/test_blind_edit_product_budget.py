"""Actual product assembly with scripted replies; no live qualification."""
import hashlib

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.providers.models import ChatResponse, TokenUsage
from scripts.blind_edit_settlement import OfflineBlindEditWorkflow
from scripts.native_contract_options import body
from scripts.check_native_contract_options import PASS
from tests import test_native_editor_product_budget as product
from tests.test_native_editor_product_budget import offline  # autouse network prohibition


class BlindProductProvider(product.ScriptedProductProvider):
    def chat(self, request):
        phase = request.metadata.get('review_phase')
        if phase not in ('offline_blind_revision', 'offline_settlement_review'):
            return super().chat(request)
        self.requests.append(request)
        data = body(request)
        if phase == 'offline_blind_revision':
            assert not {'original_review', 'proposed_review', 'accepted_review', 'review_sha256'}.intersection(data)
            content = self.edit['report']
            self.editor_output = {'report': content}
        else:
            content = compact(dict(
                original_review_sha256=data['original_review_sha256'],
                original_report_sha256=data['original_report_sha256'],
                revised_report_sha256=data['revised_report_sha256'],
                decisions=[dict(issue_id=n, original_validity=v, revision_status=s,
                    source_ids=[product._computed_source(data)],
                    explanation='Actual product assembly with analyst-scripted judgments; not model evidence.')
                    for n, (v, s) in enumerate([('confirmed', 'corrected'), ('false_positive', 'not_required')], 1)],
                review=product.json.loads(PASS)))
        response = ChatResponse(content=content, provider=self.provider_name, model=self.model_name,
            finish_reason='stop', usage=TokenUsage(input_tokens=size(request) if self.charge_ceiling else 10,
                output_tokens=request.max_tokens if self.charge_ceiling else 10))
        self.last_exchange = Exchange(request, response,
            hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        return response


def run_product(tmp_path, monkeypatch, *, recover, charge_ceiling):
    monkeypatch.setattr(product, 'ScriptedProductProvider', BlindProductProvider)
    monkeypatch.setattr(product, 'OfflineEditorWorkflow', OfflineBlindEditWorkflow)
    return product._run_product(tmp_path, monkeypatch, recover=recover, charge_ceiling=charge_ceiling)


def test_real_product_generation_blind_edit_and_settlement_share_five_calls(tmp_path, monkeypatch):
    result, provider, flow, measured = run_product(tmp_path, monkeypatch, recover=False, charge_ceiling=True)
    assert result.publication_status.value == 'published', result.terminal_reason
    assert len(provider.requests) == 5 and flow.calls == 3 and flow.revisions == 1
    assert measured['actual_scripted_usage'] == measured['full_output_reservation'] <= 401920
    assert [row['phase'] for row in measured['requests']] == [
        'generation', 'generation', 'native_business_review', 'offline_blind_revision', 'offline_settlement_review']
    assert flow.last_journal['decisions'][1]['original_validity'] == 'false_positive'
    assert not flow.last_journal['initial_reviewer_qualified']


def test_product_reassessment_stops_sixth_call_without_publication(tmp_path, monkeypatch):
    result, provider, flow, measured = run_product(tmp_path, monkeypatch, recover=True, charge_ceiling=False)
    assert result.publication_status.value == 'rejected' and result.output.report is None
    assert len(provider.requests) == 5 and flow.revisions == 1 and flow.stopped
    assert measured['budget_failures'] == [dict(code='external_call_budget_exhausted', phase='offline_settlement_review')]
    assert measured['actual_scripted_usage'] == 100

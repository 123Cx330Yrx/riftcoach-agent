"""Distinct engineering control after a preserved semantic-disagreement case.

One explicitly authored count error; no qualification sample is rewritten.
Uses the same real Host gates and offline transport, not a second live model run.
"""
from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path

from scripts.full_chain_modules import private_module
from scripts.full_chain_evidence import ROOT, sha

driver = private_module(ROOT / 'scripts/full_chain_host_rehearsal.py', {})
driver.KEY = 'host-io-count:1'
driver.VERSION = 'full-chain-explicit-count-offline-real-host-v1'
driver.FIXTURE = 'data/evaluation/fixtures/full_chain_host_count_20261013.json'
fixture = json.loads((ROOT / driver.FIXTURE).read_text(encoding='utf-8'))
driver.BEFORE, driver.AFTER = fixture['before'], fixture['after']


class ExplicitRehearsal(driver.Rehearsal):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from scripts.run_full15_resumption_candidate import controls as originals
        @lru_cache(maxsize=1)
        def controls(root=ROOT):
            seed = next(v[1] for v in originals(root)[1] if v[0]['key'] == 'claim-scope:1')
            source = replace(seed, report=fixture['report'])
            inputs = self.runner.candidate.DocumentReviewWorkflow.build_inputs(source)
            request = self.runner.candidate.ContrastDocumentWorkflow.make_request(inputs)
            cell = dict(suite='host-io-count', index=1, id='offline-authored-count-error',
                expected_initial='reject', manifest_sha256=sha(ROOT / driver.FIXTURE),
                report_sha256=self.runner.digest(source.report), input_sha256=self.runner.digest(inputs.data_json),
                first_input_ceiling=self.runner.qualification.size(request), key=driver.KEY)
            row = dict(cell, candidate_request_sha256=self.runner._bytes_sha(self.runner.validate_request(
                request, transport_id=self.runner.REVIEW_MODEL_TRANSPORT_ID)))
            return [row], [(cell, source, inputs, request)]
        self.runner.controls = controls

    def prepare(self, **kwargs):
        plan = super().prepare(**kwargs)
        plan['source_sha256']['scripts/full_chain_explicit_host_rehearsal.py'] = sha(Path(__file__))
        plan.update(scope='Distinct authored engineering control, NOT original15. One count-error case; at most initial/edit/final; Provider/HTTP 0.',
            prior_disagreement_preserved=True, original15_case_included=False)
        return plan


driver.Rehearsal = ExplicitRehearsal

if __name__ == '__main__':
    driver.main()

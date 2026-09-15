"""Independent whole-context candidate; no production registration."""
from app.evaluation import golden_contextual_correction as contextual
from app.evaluation.golden_bounded_workflow import BoundedCorrectionWorkflow
from app.evaluation.golden_contextual_sources import build_inputs
from app.evaluation.golden_contextual_requests import revision_request
from app.evaluation.golden_contextual_patch_wire import apply_wire


class ContextualCorrectionWorkflow(BoundedCorrectionWorkflow):
    build_inputs = staticmethod(build_inputs)
    prepare_state = staticmethod(contextual.prepare_state)
    build_first = staticmethod(contextual.first_request)
    build_correction = staticmethod(contextual.correction_request)
    merge_correction = staticmethod(apply_wire)

    def build_revision(self, request, canonical, inputs):
        return revision_request(inputs,canonical,contextual.FULL_CONTEXT_RULE)

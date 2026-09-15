"""Independent whole-context candidate; no production registration."""
from app.evaluation import golden_contextual_correction as contextual
from app.evaluation.golden_bounded_workflow import BoundedCorrectionWorkflow


class ContextualCorrectionWorkflow(BoundedCorrectionWorkflow):
    build_first = staticmethod(contextual.first_request)
    build_correction = staticmethod(contextual.correction_request)
    merge_correction = staticmethod(contextual.apply_correction)

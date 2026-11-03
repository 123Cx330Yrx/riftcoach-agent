"""Unadmitted opt-in router; shares all dispatch/receipt/failure behavior."""
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.evaluation.document_review_identity import role_for_request
from scripts.report_document_view import VERSION


class DocumentRoleRoutedProvider(RoleRoutedProvider):
    report_presentation = VERSION

    def role_for_request(self, request):
        return role_for_request(request)

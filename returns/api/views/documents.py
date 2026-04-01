"""Thin wrapper exposing the live return-documents view through returns.api."""

from __future__ import annotations

from api.views.return_documents import ReturnDocumentsLiveView


class ReturnCaseDocumentUploadApiView(ReturnDocumentsLiveView):
    """Expose the live return-documents view under the canonical returns.api module."""

    def get(self, request, case_id: str):
        """Delegate GET to the live view using the canonical route parameter name."""

        return super().get(request, return_id=int(case_id))

    def post(self, request, case_id: str):
        """Delegate POST to the live view using the canonical route parameter name."""

        return super().post(request, return_id=int(case_id))

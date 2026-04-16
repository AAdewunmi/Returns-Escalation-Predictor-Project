"""Merchant portal views."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import MerchantSurfaceMixin
from returns.services.merchant_portal import (
    build_merchant_case_page,
    get_merchant_case_for_user,
    upload_merchant_response,
)
from ui.forms import CaseDocumentUploadForm


class MerchantCaseListView(MerchantSurfaceMixin, TemplateView):
    """Render the merchant case list with fixed-size pagination."""

    template_name = "merchant/case_list.html"

    def get_context_data(self, **kwargs):
        """Build the merchant case list context."""

        context = super().get_context_data(**kwargs)
        context.update(build_merchant_case_page(self.request.user, self.request.GET))
        return context


class MerchantCaseDetailView(MerchantSurfaceMixin, View):
    """Render merchant case detail and handle response uploads."""

    template_name = "merchant/case_detail.html"

    def get_case(self):
        """Return the merchant-visible case for the current request."""

        return get_merchant_case_for_user(self.request.user, self.kwargs["case_id"])

    def get(self, request, *args, **kwargs):
        """Render the case detail page."""

        return render(
            request,
            self.template_name,
            {
                "case": self.get_case(),
                "form": CaseDocumentUploadForm(actor_role="merchant"),
            },
        )

    def post(self, request, *args, **kwargs):
        """Handle merchant response uploads on the case detail page."""

        case = self.get_case()
        form = CaseDocumentUploadForm(
            request.POST,
            request.FILES,
            actor_role="merchant",
        )

        if form.is_valid():
            upload_merchant_response(
                return_case=case,
                uploaded_by=request.user,
                uploaded_file=form.cleaned_data["file"],
                description=form.cleaned_data["notes"],
            )
            messages.success(request, "Response uploaded successfully.")
            return redirect("merchant_portal:case_detail", case_id=case.pk)

        response = render(
            request,
            self.template_name,
            {
                "case": case,
                "form": form,
            },
        )
        response.status_code = 400
        return response

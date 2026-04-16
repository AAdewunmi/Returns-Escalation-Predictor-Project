"""Merchant portal views."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import MerchantSurfaceMixin
from returns.forms_merchant import MerchantResponseForm
from returns.services.merchant_portal import (
    build_merchant_case_detail_context,
    build_merchant_case_page,
    submit_merchant_response,
)


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

        return build_merchant_case_detail_context(
            self.request.user,
            self.kwargs["case_id"],
        )["case"]

    def get(self, request, *args, **kwargs):
        """Render the case detail page."""

        context = build_merchant_case_detail_context(
            self.request.user,
            self.kwargs["case_id"],
        )
        return render(
            request,
            self.template_name,
            {
                **context,
                "form": MerchantResponseForm(),
            },
        )

    def post(self, request, *args, **kwargs):
        """Handle merchant response uploads on the case detail page."""

        case = self.get_case()
        form = MerchantResponseForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            submit_merchant_response(
                return_case=case,
                submitted_by=request.user,
                response_note=form.cleaned_data["response_note"],
                response_file=form.cleaned_data["response_file"],
            )
            messages.success(request, "Response submitted successfully.")
            return redirect("merchant_portal:case_detail", case_id=case.pk)

        response = render(
            request,
            self.template_name,
            {
                **build_merchant_case_detail_context(
                    self.request.user,
                    self.kwargs["case_id"],
                ),
                "form": form,
            },
        )
        response.status_code = 400
        return response

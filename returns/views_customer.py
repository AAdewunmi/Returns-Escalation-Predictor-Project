"""Customer portal views."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import CustomerSurfaceMixin
from returns.services.customer_portal import (
    build_customer_case_page,
    get_customer_case_for_user,
    upload_customer_evidence,
)
from ui.forms import CaseDocumentUploadForm


class CustomerCaseListView(CustomerSurfaceMixin, TemplateView):
    """Render the customer case list with fixed-size pagination."""

    template_name = "customer/case_list.html"

    def get_context_data(self, **kwargs):
        """Build the customer case list context."""

        context = super().get_context_data(**kwargs)
        context.update(build_customer_case_page(self.request.user, self.request.GET))
        return context


class CustomerCaseDetailView(CustomerSurfaceMixin, View):
    """Render customer case detail and handle customer evidence uploads."""

    template_name = "customer/case_detail.html"

    def get_case(self):
        """Return the customer-visible case for the current request."""

        return get_customer_case_for_user(self.request.user, self.kwargs["case_id"])

    def get(self, request, *args, **kwargs):
        """Render the case detail page."""

        return render(
            request,
            self.template_name,
            {
                "case": self.get_case(),
                "form": CaseDocumentUploadForm(actor_role="customer"),
            },
        )

    def post(self, request, *args, **kwargs):
        """Handle evidence upload on the case detail page."""

        case = self.get_case()
        form = CaseDocumentUploadForm(
            request.POST,
            request.FILES,
            actor_role="customer",
        )

        if form.is_valid():
            upload_customer_evidence(
                return_case=case,
                uploaded_by=request.user,
                uploaded_file=form.cleaned_data["file"],
                description=form.cleaned_data["notes"],
            )
            messages.success(request, "Document uploaded successfully.")
            return redirect("customer_portal:case_detail", case_id=case.pk)

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

# path: returns/views_customer.py
"""Customer portal views."""

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import CustomerSurfaceMixin
from apps.returns.forms_customer import CustomerEvidenceUploadForm
from apps.returns.services.customer_portal import (
    build_customer_case_page,
    get_customer_case_for_user,
    upload_customer_evidence,
)


class CustomerCaseListView(CustomerSurfaceMixin, TemplateView):
    """Render the customer case list with fixed-size pagination."""

    template_name = "customer/case_list.html"

    def get_context_data(self, **kwargs):
        """Build the customer case list context."""
        context = super().get_context_data(**kwargs)
        context.update(build_customer_case_page(self.request.user, self.request.GET))
        return context


class CustomerCaseDetailView(CustomerSurfaceMixin, View):
    """Render customer case detail and handle evidence uploads."""

    template_name = "customer/case_detail.html"

    def get_case(self):
        """Return the customer-visible case for the current request."""
        try:
            return get_customer_case_for_user(self.request.user, self.kwargs["pk"])
        except ObjectDoesNotExist as exc:
            raise Http404("Return case not found.") from exc

    def get(self, request, *args, **kwargs):
        """Render the case detail page."""
        return render(
            request,
            self.template_name,
            {"case": self.get_case(), "form": CustomerEvidenceUploadForm()},
        )

    def post(self, request, *args, **kwargs):
        """Handle evidence upload on the case detail page."""
        case = self.get_case()
        form = CustomerEvidenceUploadForm(request.POST, request.FILES)

        if form.is_valid():
            upload_customer_evidence(
                return_case=case,
                uploaded_by=request.user,
                uploaded_file=form.cleaned_data["evidence_file"],
                description=form.cleaned_data["description"],
            )
            messages.success(request, "Evidence uploaded successfully.")
            return redirect("customer_portal:case_detail", pk=case.pk)

        response = render(request, self.template_name, {"case": case, "form": form})
        response.status_code = 400
        return response

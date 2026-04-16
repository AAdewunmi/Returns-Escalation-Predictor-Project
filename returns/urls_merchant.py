"""Merchant portal routes."""

from django.urls import path

from returns.views_merchant import MerchantCaseDetailView, MerchantCaseListView

app_name = "merchant_portal"

urlpatterns = [
    path("", MerchantCaseListView.as_view(), name="case_list"),
    path("<int:case_id>/", MerchantCaseDetailView.as_view(), name="case_detail"),
]

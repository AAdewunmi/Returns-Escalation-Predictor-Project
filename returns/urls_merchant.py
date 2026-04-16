# path: returns/urls_merchant.py
"""Merchant portal routes."""

from django.urls import path

from apps.returns.views_merchant import MerchantCaseDetailView, MerchantCaseListView

app_name = "merchant_portal"

urlpatterns = [
    path("", MerchantCaseListView.as_view(), name="case_list"),
    path("<str:pk>/", MerchantCaseDetailView.as_view(), name="case_detail"),
]
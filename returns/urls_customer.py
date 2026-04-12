# path: returns/urls_customer.py
"""Customer portal routes."""

from django.urls import path

from apps.returns.views_customer import CustomerCaseDetailView, CustomerCaseListView

app_name = "customer_portal"

urlpatterns = [
    path("", CustomerCaseListView.as_view(), name="case_list"),
    path("<str:pk>/", CustomerCaseDetailView.as_view(), name="case_detail"),
]
"""Customer portal routes."""

from django.urls import path

from returns.views_customer import CustomerCaseDetailView, CustomerCaseListView

app_name = "customer_portal"

urlpatterns = [
    path("", CustomerCaseListView.as_view(), name="case_list"),
    path("<int:case_id>/", CustomerCaseDetailView.as_view(), name="case_detail"),
]

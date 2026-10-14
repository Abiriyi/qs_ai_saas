# tribunal/api/urls.py
from django.urls import path

from tribunal.api.views import (
    TribunalCaseDecisionView,
    TribunalCaseDetailView,
    TribunalCaseListCreateView,
)

urlpatterns = [
    path(
        "",
        TribunalCaseListCreateView.as_view(),
        name="tribunal-case-list",
    ),
    path(
        "<uuid:pk>/",
        TribunalCaseDetailView.as_view(),
        name="tribunal-case-detail",
    ),
    path(
        "<uuid:pk>/decide/",
        TribunalCaseDecisionView.as_view(),
        name="tribunal-case-decide",
    ),
]

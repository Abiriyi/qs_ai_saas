from django.urls import path

from .views import (
    BoQDetailView,
    BoQListView,
    BoQReviewDecisionView,
    FinishSafeBoQView,
)

urlpatterns = [
    path(
        "",
        BoQListView.as_view(),
        name="boq-list",
    ),
    path(
        "<uuid:pk>/",
        BoQDetailView.as_view(),
        name="boq-detail",
    ),
    path(
        "finish-safe/",
        FinishSafeBoQView.as_view(),
        name="boq-finish-safe",
    ),
    path(
        "<uuid:boq_id>/review/",
        BoQReviewDecisionView.as_view(),
        name="boq-review-decision",
    ),
]

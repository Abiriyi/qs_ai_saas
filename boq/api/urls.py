from django.urls import path

from .views import BoQReviewDecisionView, FinishSafeBoQView

urlpatterns = [
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

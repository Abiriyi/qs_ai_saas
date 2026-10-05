from django.urls import path

from .views import (
    BoQDetailView,
    BoQItemDetailView,
    BoQItemListView,
    BoQListView,
    BoQReviewDecisionView,
    BoQSectionDetailView,
    BoQSectionListView,
    FinishSafeBoQView,
)

urlpatterns = [
    path(
        "",
        BoQListView.as_view(),
        name="boq-list",
    ),
    path(
        "<uuid:boq_id>/sections/",
        BoQSectionListView.as_view(),
        name="boq-section-list",
    ),
    path(
        "<uuid:boq_id>/sections/<uuid:section_id>/",
        BoQSectionDetailView.as_view(),
        name="boq-section-detail",
    ),
    path(
        "<uuid:boq_id>/sections/<uuid:section_id>/items/",
        BoQItemListView.as_view(),
        name="boq-item-list",
    ),
    path(
        "<uuid:boq_id>/sections/<uuid:section_id>/items/<uuid:item_id>/",
        BoQItemDetailView.as_view(),
        name="boq-item-detail",
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

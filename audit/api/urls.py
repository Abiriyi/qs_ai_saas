# audit/api/urls.py
from django.urls import path

from audit.api.views import AuditEventListView

urlpatterns = [
    path(
        "",
        AuditEventListView.as_view(),
        name="audit-event-list",
    ),
]

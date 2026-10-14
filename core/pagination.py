# core/pagination.py
from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Default pagination for list endpoints.

    Exposes the standard DRF envelope::

        {"count": int, "next": url|null, "previous": url|null, "results": [...]}

    Clients can override the page size with ``?page_size=`` up to
    ``max_page_size`` (which protects the API from unbounded responses).
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )

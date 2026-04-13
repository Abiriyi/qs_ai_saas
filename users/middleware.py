from django.db import connection
from contextvars import ContextVar

# Global request-scoped tenant context
_current_org = ContextVar("current_org", default=None)


def get_current_org():
    return _current_org.get()


class TenantMiddleware:
    """
    Attaches organization context to every request.
    Enforces multi-tenancy at request level.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        org = None

        if user and user.is_authenticated:
            org = user.organization

        # Store in Python context (safe for services)
        _current_org.set(org)

        # Store in PostgreSQL session (for RLS later)
        if org:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET app.current_org = %s",
                    [str(org.id)]
                )

        response = self.get_response(request)

        return response

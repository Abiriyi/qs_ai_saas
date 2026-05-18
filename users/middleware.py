from core.tenant import (
    set_current_org,
    reset_current_org,
)


class TenantMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user = getattr(request, "user", None)

        org = (
            getattr(user, "organization", None)
            if user and user.is_authenticated
            else None
        )

        token = set_current_org(org)

        try:
            response = self.get_response(request)

        finally:
            reset_current_org(token)

        return response

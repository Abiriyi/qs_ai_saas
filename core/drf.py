class TenantAPIViewMixin:

    def initial(self, request, *args, **kwargs):

        super().initial(request, *args, **kwargs)

        org = getattr(request.user, "organization", None)

        self._tenant_token = set_current_org(org)

    def finalize_response(
        self,
        request,
        response,
        *args,
        **kwargs
    ):

        if hasattr(self, "_tenant_token"):
            reset_current_org(self._tenant_token)

        return super().finalize_response(
            request,
            response,
            *args,
            **kwargs
        )
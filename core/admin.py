class TenantAdmin(admin.ModelAdmin):

    def get_queryset(self, request):

        qs = super().get_queryset(request)

        org = getattr(request.user, "organization", None)

        if org:
            return qs.filter(organization=org)

        return qs

    def save_model(
        self,
        request,
        obj,
        form,
        change
    ):

        if not obj.organization_id:
            obj.organization = request.user.organization

        super().save_model(
            request,
            obj,
            form,
            change
        )
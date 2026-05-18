class AuditEvent(models.Model):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.CharField(max_length=255)

    model_name = models.CharField(max_length=255)

    object_id = models.UUIDField()

    payload = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
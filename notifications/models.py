from django.conf import settings
from django.db import models


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        ASSET_REQUEST = "ASSET_REQUEST", "Asset Request"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        LICENSE_EXPIRY = "LICENSE_EXPIRY", "Software License Expiry"
        WARRANTY_EXPIRY = "WARRANTY_EXPIRY", "Asset Warranty Expiry"
        EMPLOYEE_EVENT = "EMPLOYEE_EVENT", "Employee Event"
        SYSTEM = "SYSTEM", "System"

    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Warning"
        SUCCESS = "SUCCESS", "Success"
        DANGER = "DANGER", "Danger"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
    )

    title = models.CharField(
        max_length=200,
    )

    message = models.TextField()

    url = models.CharField(
        max_length=500,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reference_type = models.CharField(
        max_length=100,
        blank=True,
    )

    reference_id = models.CharField(
        max_length=100,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("recipient", "is_read"),
            ),
            models.Index(
                fields=("recipient", "created_at"),
            ),
            models.Index(
                fields=(
                    "notification_type",
                    "reference_type",
                    "reference_id",
                ),
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
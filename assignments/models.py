from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from assets.models import Asset
from accounts.models import EmployeeProfile


class Assignment(models.Model):

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="asset_assignments",
    )

    assigned_date = models.DateField(
        default=timezone.now
    )

    return_date = models.DateField(
        null=True,
        blank=True
    )

    assignment_notes = models.TextField(
        blank=True
    )

    return_notes = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):
        if self.is_active:
            existing_assignment = Assignment.objects.filter(
                asset=self.asset,
                is_active=True
            ).exclude(pk=self.pk).first()

            if existing_assignment:
                raise ValidationError(
                    "This asset is already assigned to another employee."
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        # Agar assignment inactive hai aur return date nahi di gayi
        # to automatically aaj ki date set kar dein.
        if not self.is_active and not self.return_date:
            self.return_date = timezone.now().date()

        with transaction.atomic():

            super().save(*args, **kwargs)

            if self.is_active:
                Asset.objects.filter(
                    pk=self.asset_id
                ).update(
                    status=Asset.Status.ASSIGNED
                )

            else:
                Asset.objects.filter(
                    pk=self.asset_id
                ).update(
                    status=Asset.Status.AVAILABLE
                )

    def __str__(self):
        return (
            f"{self.asset.asset_id} → "
            f"{self.employee.employee_id}"
        )
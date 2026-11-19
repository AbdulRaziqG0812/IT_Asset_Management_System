from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from accounts.models import EmployeeProfile
from assets.models import Asset


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
        if not self.is_active:
            return

        existing_assignment = Assignment.objects.filter(
            asset=self.asset,
            is_active=True,
        ).exclude(
            pk=self.pk
        ).first()

        if existing_assignment:
            raise ValidationError(
                "This asset is already assigned to another employee."
            )

        # New assignments and re-activations are only allowed for
        # assets that are currently available.
        if self.pk:
            previous_assignment = (
                Assignment.objects
                .filter(pk=self.pk)
                .select_related("asset")
                .first()
            )

            if previous_assignment:
                is_being_reactivated = (
                    not previous_assignment.is_active
                    and self.is_active
                )

                is_asset_being_changed = (
                    previous_assignment.asset_id != self.asset_id
                )

                if (
                    (is_being_reactivated or is_asset_being_changed)
                    and self.asset.status != Asset.Status.AVAILABLE
                ):
                    raise ValidationError(
                        "Only an available asset can be assigned."
                    )

                return

        if self.asset.status != Asset.Status.AVAILABLE:
            raise ValidationError(
                "Only an available asset can be assigned."
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
                # Active assignment means the asset is currently assigned.
                Asset.objects.filter(
                    pk=self.asset_id
                ).update(
                    status=Asset.Status.ASSIGNED
                )

            else:
                # IMPORTANT:
                # Returning an assignment must not overwrite an existing
                # lifecycle state such as UNDER_MAINTENANCE, DAMAGED,
                # LOST, RETIRED, or DISPOSED.
                #
                # Only an asset that is currently marked ASSIGNED should
                # become AVAILABLE after its assignment is returned.
                Asset.objects.filter(
                    pk=self.asset_id,
                    status=Asset.Status.ASSIGNED,
                ).update(
                    status=Asset.Status.AVAILABLE
                )

    def __str__(self):
        return (
            f"{self.asset.asset_id} → "
            f"{self.employee.employee_id}"
        )